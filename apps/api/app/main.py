import hashlib
import logging
import secrets
import uuid
import asyncio
from contextlib import asynccontextmanager
from queue import Empty
from datetime import datetime, timedelta, timezone
from time import perf_counter

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.auth_mail import queue_email_verification, queue_password_link
from app.assistant import assistant_reply, requests_timetable_generation
from app.assistant_context import build_assistant_context
from app.dependencies import current_user, ensure_browser_origin
from app.db import Base, engine, get_db
from app.models import AcademicTerm, AuditEvent, Department, EmailVerificationToken, Institution, PasswordResetToken, RefreshSession, Role, User
from app.schemas import (AssistantConfirmRequest, AssistantRequest, EmailTokenRequest, ForgotPasswordRequest,
                         ResendVerificationRequest, ResetPasswordRequest, SignInRequest,
                         SignUpRequest, StoredTimetableGenerateRequest, UserView)
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.routes.campus import generate_stored_timetable, router as campus_router
from app.routes.personal import router as personal_router
from app.routes.analytics import router as analytics_router
from app.routes.audit import router as audit_router
from app.routes.settings import router as settings_router
from app.routes.superadmin import router as superadmin_router
from app.rate_limit import limit_auth_requests, redis_limiter
from app.events import publish_campus_refresh, subscribe_campus_events, unsubscribe_campus_events

@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        if redis_limiter:
            await redis_limiter.close()


app = FastAPI(title="CampusFlow API", version="0.1.0", lifespan=lifespan)


@sqlalchemy_event.listens_for(OrmSession, "before_flush")
def mark_campus_change(session, _flush_context, _instances):
    if any(isinstance(record, AuditEvent) for record in session.new):
        session.info["campus_refresh_after_commit"] = True


@sqlalchemy_event.listens_for(OrmSession, "after_commit")
def broadcast_campus_change(session):
    if session.info.pop("campus_refresh_after_commit", False):
        publish_campus_refresh()


@sqlalchemy_event.listens_for(OrmSession, "after_rollback")
def discard_campus_change(session):
    session.info.pop("campus_refresh_after_commit", None)
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
request_logger = logging.getLogger("campusflow.request")
request_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
app.include_router(campus_router)
app.include_router(personal_router)
app.include_router(analytics_router)
app.include_router(audit_router)
app.include_router(settings_router)
app.include_router(superadmin_router)
_CORS_ALLOWED_ORIGINS = list({
    settings.web_origin,
    "http://127.0.0.1:3010",
    "http://localhost:3010",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
})
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|.*\.trycloudflare\.com|.*\.vercel\.app)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)


@app.middleware("http")
async def safe_request_logging(request: Request, call_next):
    request_id = uuid.uuid4().hex
    started = perf_counter()
    route_path = "<unmatched>"
    try:
        response = await call_next(request)
        route = request.scope.get("route")
        route_path = getattr(route, "path", route_path)
    except Exception as exc:
        request_logger.error("request failed id=%s method=%s path=%s error_type=%s",
                             request_id, request.method, route_path, type(exc).__name__)
        response = JSONResponse(status_code=500, content={"detail": "Internal server error.", "request_id": request_id})
        if request.headers.get("origin") == settings.web_origin:
            response.headers["Access-Control-Allow-Origin"] = settings.web_origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
    response.headers["X-Request-ID"] = request_id
    request_logger.info("request completed id=%s method=%s path=%s status=%s duration_ms=%d",
                        request_id, request.method, route_path, response.status_code,
                        int((perf_counter() - started) * 1000))
    return response


def user_view(user: User, email_verification_required: bool = False) -> UserView:
    return UserView(id=str(user.id), email=user.email, full_name=user.full_name, role=user.role.value,
                    email_verified=user.email_verified,
                    email_verification_required=email_verification_required)


def verify_browser_origin(request: Request):
    ensure_browser_origin(request)


def create_refresh_session(db: Session, user: User, family_id: uuid.UUID | None = None) -> str:
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    db.add(RefreshSession(user_id=user.id, family_id=family_id or uuid.uuid4(),
                          token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                          expires_at=now + timedelta(days=settings.refresh_token_days)))
    return raw_token


def set_session_cookies(response: Response, user: User, refresh_token: str, csrf_token: str | None = None):
    csrf_token = csrf_token or secrets.token_urlsafe(32)
    # Use secure=True only for HTTPS origins (production); False for local HTTP dev
    _secure = settings.api_origin.startswith("https://")
    response.set_cookie("campusflow_session", create_access_token(user), httponly=True, secure=_secure,
                        samesite="lax", max_age=settings.access_token_minutes * 60, path="/")
    response.set_cookie("campusflow_refresh", refresh_token, httponly=True, secure=_secure,
                        samesite="lax", max_age=settings.refresh_token_days * 24 * 60 * 60, path="/")
    response.set_cookie("campusflow_csrf", csrf_token, httponly=False, secure=_secure,
                        samesite="lax", max_age=settings.refresh_token_days * 24 * 60 * 60, path="/")


def revoke_refresh_family(db: Session, family_id, now: datetime):
    db.query(RefreshSession).filter(RefreshSession.family_id == family_id,
                                    RefreshSession.revoked_at.is_(None)).update(
        {RefreshSession.revoked_at: now}, synchronize_session=False)


def utc_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


@app.get("/api/v1/health")
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is unavailable.")
    if redis_limiter:
        try:
            await redis_limiter.ping()
        except Exception as exc:
            request_logger.error("shared auth limiter health check failed error_type=%s", type(exc).__name__)
            raise HTTPException(status_code=503, detail="Authentication rate limiting is unavailable.")
    return {"status": "ok", "service": "dayleaf-api"}


@app.get("/api/v1/health/live")
def health_live():
    return {"status": "ok", "service": "dayleaf-api"}


@app.get("/api/v1/events")
async def campus_events(request: Request):
    token = request.cookies.get("campusflow_session")
    try:
        claims = decode_access_token(token or "")
        uuid.UUID(claims["sub"])
        expires_at = int(claims["exp"])
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired.")
    subscriber = subscribe_campus_events()

    async def stream():
        try:
            yield "retry: 5000\n\n"
            while not await request.is_disconnected():
                remaining = expires_at - int(datetime.now(timezone.utc).timestamp())
                if remaining <= 0:
                    yield "event: session.expired\ndata: {}\n\n"
                    break
                try:
                    await asyncio.wait_for(asyncio.to_thread(subscriber.get, True, min(15, remaining)), timeout=min(16, remaining + 1))
                    yield "event: campus.refresh\ndata: {}\n\n"
                except (Empty, asyncio.TimeoutError):
                    yield ": keep-alive\n\n"
        finally:
            unsubscribe_campus_events(subscriber)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


@app.get("/api/v1/auth/csrf")
def csrf_token(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    token = request.cookies.get("campusflow_csrf") or secrets.token_urlsafe(32)
    if request.cookies.get("campusflow_csrf") != token:
        response.set_cookie("campusflow_csrf", token, httponly=False, secure=True,
                            samesite="lax", max_age=settings.refresh_token_days * 24 * 60 * 60, path="/")
    return {"csrf_token": token}


@app.post("/api/v1/auth/sign-up", response_model=UserView, status_code=201)
def sign_up(payload: SignUpRequest, background_tasks: BackgroundTasks, response: Response,
            request: Request, _rate_limit: None = Depends(limit_auth_requests("sign-up", 5, 900)),
            db: Session = Depends(get_db)):
    verify_browser_origin(request)
    institution = Institution(name=payload.institution_name.strip())
    db.add(institution)
    db.flush()
    user = User(institution_id=institution.id, email=payload.email.lower(), full_name=payload.full_name.strip(),
                password_hash=hash_password(payload.password), role=Role.college_admin)
    db.add(user)
    try:
        db.flush()
        refresh_token = None
        if settings.require_email_verification:
            queue_email_verification(db, background_tasks, user)
        else:
            user.email_verified = True
            refresh_token = create_refresh_session(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    db.refresh(user)
    if refresh_token:
        set_session_cookies(response, user, refresh_token, request.cookies.get("campusflow_csrf"))
    return user_view(user, email_verification_required=settings.require_email_verification)


@app.post("/api/v1/auth/sign-in", response_model=UserView)
def sign_in(payload: SignInRequest, response: Response, request: Request,
            _rate_limit: None = Depends(limit_auth_requests("sign-in", 10, 300)), db: Session = Depends(get_db)):
    verify_browser_origin(request)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    if settings.require_email_verification and not user.email_verified:
        raise HTTPException(status_code=403, detail="Verify your email before signing in. Use the link in your inbox or request a new one.")
    refresh_token = create_refresh_session(db, user)
    db.commit()
    set_session_cookies(response, user, refresh_token, request.cookies.get("campusflow_csrf"))
    return user_view(user)


@app.post("/api/v1/auth/verify-email", response_model=UserView)
def verify_email(payload: EmailTokenRequest, request: Request, db: Session = Depends(get_db)):
    verify_browser_origin(request)
    digest = hashlib.sha256(payload.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    verification = db.scalar(select(EmailVerificationToken).where(
        EmailVerificationToken.token_hash == digest,
        EmailVerificationToken.used_at.is_(None),
        EmailVerificationToken.expires_at > now,
    ).with_for_update())
    if not verification:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    user = db.get(User, verification.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    verification.used_at = now
    user.email_verified = True
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.id != verification.id,
        EmailVerificationToken.used_at.is_(None),
    ).update({EmailVerificationToken.used_at: now}, synchronize_session=False)
    db.commit()
    return user_view(user)


@app.post("/api/v1/auth/resend-verification", status_code=202)
def resend_verification(payload: ResendVerificationRequest, background_tasks: BackgroundTasks,
                        request: Request, _rate_limit: None = Depends(limit_auth_requests("resend-verification", 3, 900)),
                        db: Session = Depends(get_db)):
    verify_browser_origin(request)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user and user.is_active and not user.email_verified and settings.smtp_host and settings.mail_from:
        queue_email_verification(db, background_tasks, user)
        db.commit()
    return {"message": "If an unverified account matches that address, a verification link will be sent."}


@app.post("/api/v1/auth/sign-out", status_code=204)
def sign_out(response: Response, request: Request, db: Session = Depends(get_db)):
    verify_browser_origin(request)
    refresh_token = request.cookies.get("campusflow_refresh")
    if refresh_token:
        digest = hashlib.sha256(refresh_token.encode()).hexdigest()
        session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest))
        if session:
            revoke_refresh_family(db, session.family_id, datetime.now(timezone.utc))
    db.commit()
    _secure = settings.api_origin.startswith("https://")
    response.delete_cookie("campusflow_session", path="/", secure=_secure, httponly=True, samesite="lax")
    response.delete_cookie("campusflow_refresh", path="/", secure=_secure, httponly=True, samesite="lax")
    response.delete_cookie("campusflow_csrf", path="/", secure=_secure, httponly=False, samesite="lax")


@app.post("/api/v1/auth/refresh", response_model=UserView)
def refresh_session(response: Response, request: Request, db: Session = Depends(get_db)):
    verify_browser_origin(request)
    raw_token = request.cookies.get("campusflow_refresh")
    if not raw_token:
        raise HTTPException(status_code=401, detail="Refresh session expired. Sign in again.")
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest).with_for_update())
    if not session:
        raise HTTPException(status_code=401, detail="Refresh session expired. Sign in again.")
    now = datetime.now(timezone.utc)
    if session.consumed_at or session.revoked_at:
        revoke_refresh_family(db, session.family_id, now)
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh session was already used. Sign in again.")
    user = db.get(User, session.user_id)
    if utc_aware(session.expires_at) <= now or not user or not user.is_active or (settings.require_email_verification and not user.email_verified):
        revoke_refresh_family(db, session.family_id, now)
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh session expired. Sign in again.")
    session.consumed_at = now
    next_token = create_refresh_session(db, user, session.family_id)
    db.commit()
    set_session_cookies(response, user, next_token, request.cookies.get("campusflow_csrf"))
    return user_view(user)


@app.post("/api/v1/auth/forgot-password", status_code=202)
def forgot_password(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks,
                    _rate_limit: None = Depends(limit_auth_requests("forgot-password", 3, 900)),
                    db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user and settings.smtp_host and settings.mail_from:
        queue_password_link(db, background_tasks, user)
        db.commit()
    elif user:
        # The public response stays generic; the operator can see mail setup requirements in configuration.
        pass
    return {"message": "If an account matches that address, a password reset link will be sent."}


@app.post("/api/v1/auth/reset-password", status_code=204)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    digest = hashlib.sha256(payload.token.encode()).hexdigest()
    reset = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == digest,
                                                       PasswordResetToken.used_at.is_(None),
                                                       PasswordResetToken.expires_at > datetime.now(timezone.utc)).with_for_update())
    if not reset:
        raise HTTPException(status_code=400, detail="This reset link is invalid or expired.")
    user = db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or expired.")
    user.password_hash = hash_password(payload.new_password)
    user.email_verified = True
    reset.used_at = datetime.now(timezone.utc)
    db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id,
                                             EmailVerificationToken.used_at.is_(None)).update(
        {EmailVerificationToken.used_at: datetime.now(timezone.utc)}, synchronize_session=False)
    db.query(RefreshSession).filter(RefreshSession.user_id == user.id,
                                    RefreshSession.revoked_at.is_(None)).update(
        {RefreshSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()


@app.get("/api/v1/auth/me", response_model=UserView)
def me(user: User = Depends(current_user)):
    return user_view(user)


@app.post("/api/v1/assistant/chat")
async def assistant_chat(payload: AssistantRequest, request: Request, db: Session = Depends(get_db),
                         user: User = Depends(current_user)):
    verify_browser_origin(request)
    context = build_assistant_context(db, user, payload.term_id, payload.department_id)
    result = await assistant_reply(payload.message, settings, context)
    result["proposal"] = None
    if not requests_timetable_generation(payload.message):
        return result
    if user.role not in (Role.super_admin, Role.college_admin, Role.hod):
        result["reply"] = "I can help plan a timetable, but only a college admin or department head can generate a draft."
        return result
    if not payload.term_id or not payload.department_id:
        result["reply"] = "Choose an academic term and department first. I’ll prepare a draft proposal for your review."
        return result
    term = db.get(AcademicTerm, payload.term_id)
    department = db.get(Department, payload.department_id)
    if not term or not department:
        raise HTTPException(status_code=404, detail="Choose an existing academic term and department.")
    if user.role != Role.super_admin and department.institution_id != user.institution_id:
        raise HTTPException(status_code=403, detail="This department is outside your institution.")
    if term.institution_id != department.institution_id:
        raise HTTPException(status_code=422, detail="The academic term and department must belong to the same institution.")
    if user.role == Role.hod and user.department_id != department.id:
        raise HTTPException(status_code=403, detail="Department heads can only plan for their own department.")
    result["reply"] = f"I’m ready to build a draft for {department.name} · {term.name}. Review the proposal, then confirm to run the constraint optimizer."
    result["proposal"] = {"action": "generate_timetable", "term_id": str(term.id),
                          "department_id": str(department.id), "term": term.name,
                          "department": department.name, "name": f"{department.code} · {term.name} · AI draft"}
    return result


@app.post("/api/v1/assistant/confirm", status_code=201)
def confirm_assistant_action(payload: AssistantConfirmRequest, request: Request, db: Session = Depends(get_db),
                             user: User = Depends(current_user)):
    verify_browser_origin(request)
    # Confirmation triggers a real optimizer run; campus authorization, readiness,
    # persistence, conflict validation, and audit checks remain in the campus service.
    return generate_stored_timetable(
        StoredTimetableGenerateRequest(term_id=payload.term_id, department_id=payload.department_id,
                                       name=payload.name), request, db, user)
