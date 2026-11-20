import hmac
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import Role, User
from app.security import decode_access_token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("campusflow_session")
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required.")
    try:
        subject = decode_access_token(token)["sub"]
        user = db.get(User, UUID(subject))
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired.")
    if not user or not user.is_active or (settings.require_email_verification and not user.email_verified):
        raise HTTPException(status_code=401, detail="Session expired.")
    return user


def ensure_browser_origin(request: Request):
    origin = request.headers.get("origin")
    allowed_origins = {
        settings.web_origin,
        "http://127.0.0.1:3010",
        "http://localhost:3010",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    }
    is_allowed = (
        not origin or
        origin in allowed_origins or
        origin.endswith(".trycloudflare.com") or
        origin.startswith("https://")
    )
    if not is_allowed:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")
    if request.cookies.get("campusflow_session") or request.cookies.get("campusflow_refresh"):
        csrf_cookie = request.cookies.get("campusflow_csrf")
        csrf_header = request.headers.get("x-csrf-token")
        if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(status_code=403, detail="CSRF token is missing or invalid.")


def ensure_manager(user: User, department_id: UUID | None = None):
    if user.role in (Role.super_admin, Role.college_admin):
        return
    if user.role == Role.hod and department_id is not None and user.department_id == department_id:
        return
    raise HTTPException(status_code=403, detail="You do not have permission to manage this campus data.")


def ensure_institution(user: User, institution_id: UUID):
    if user.role == Role.super_admin:
        return
    if user.institution_id != institution_id:
        raise HTTPException(status_code=404, detail="Campus record not found.")
