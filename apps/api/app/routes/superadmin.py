from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_user, ensure_browser_origin
from app.calendar import maximum_period_count
from app.models import AuditEvent, Department, Institution, RefreshSession, Role, User
from app.schemas import InstitutionCalendarBreak
from app.routes.campus import create_invited_user

router = APIRouter(prefix="/api/v1/superadmin", tags=["super admin"])


class InstitutionPayload(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    timezone: str = Field(default="Asia/Kolkata", min_length=3, max_length=80)
    timetable_period_start: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timetable_period_minutes: int | None = Field(default=None, ge=20, le=180)
    timetable_breaks: list[InstitutionCalendarBreak] | None = Field(default=None, max_length=40)


class CollegeAdminInvite(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr


class AccountStatus(BaseModel):
    is_active: bool


def require_super_admin(user: User):
    if user.role != Role.super_admin:
        raise HTTPException(status_code=403, detail="Only a super admin can manage institutions.")


def validate_timezone(timezone_name: str):
    try:
        ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail="Enter a valid IANA timezone, for example Asia/Kolkata.")


def institution_payload(db: Session, institution: Institution):
    admins = db.scalars(select(User).where(User.institution_id == institution.id,
                                           User.role == Role.college_admin).order_by(User.full_name)).all()
    department_count = db.scalar(select(func.count()).select_from(Department).where(
        Department.institution_id == institution.id)) or 0
    return {"id": str(institution.id), "name": institution.name, "timezone": institution.timezone,
            "timetable_period_start": institution.timetable_period_start,
            "timetable_period_minutes": institution.timetable_period_minutes,
            "timetable_breaks": institution.timetable_breaks or [],
            "department_count": department_count,
            "admins": [{"id": str(admin.id), "full_name": admin.full_name, "email": admin.email,
                        "is_active": admin.is_active, "email_verified": admin.email_verified} for admin in admins]}


@router.get("/institutions")
def list_institutions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_super_admin(user)
    institutions = db.scalars(select(Institution).order_by(Institution.name)).all()
    return [institution_payload(db, institution) for institution in institutions]


@router.post("/institutions", status_code=201)
def create_institution(payload: InstitutionPayload, request: Request, db: Session = Depends(get_db),
                       user: User = Depends(current_user)):
    ensure_browser_origin(request)
    require_super_admin(user)
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Enter an institution name with at least two characters.")
    validate_timezone(payload.timezone)
    start = payload.timetable_period_start or "09:00"
    duration = payload.timetable_period_minutes or 60
    if maximum_period_count(start, duration) < 1:
        raise HTTPException(status_code=422, detail="The bell-time settings must leave room for at least one period before midnight.")
    institution = Institution(name=name, timezone=payload.timezone,
                              timetable_period_start=start, timetable_period_minutes=duration,
                              timetable_breaks=[item.model_dump() for item in (payload.timetable_breaks or [])])
    db.add(institution)
    db.flush()
    db.add(AuditEvent(institution_id=institution.id, actor_id=user.id, action="created",
                      resource_type="institution", resource_id=str(institution.id)))
    db.commit()
    db.refresh(institution)
    return institution_payload(db, institution)


@router.patch("/institutions/{institution_id}")
def update_institution(institution_id: UUID, payload: InstitutionPayload, request: Request,
                       db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    require_super_admin(user)
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Enter an institution name with at least two characters.")
    validate_timezone(payload.timezone)
    start = payload.timetable_period_start or institution.timetable_period_start
    duration = payload.timetable_period_minutes or institution.timetable_period_minutes
    if maximum_period_count(start, duration) < 1:
        raise HTTPException(status_code=422, detail="The bell-time settings must leave room for at least one period before midnight.")
    institution.name = name
    institution.timezone = payload.timezone
    institution.timetable_period_start = start
    institution.timetable_period_minutes = duration
    if payload.timetable_breaks is not None:
        institution.timetable_breaks = [item.model_dump() for item in payload.timetable_breaks]
    db.add(AuditEvent(institution_id=institution.id, actor_id=user.id, action="updated",
                      resource_type="institution", resource_id=str(institution.id)))
    db.commit()
    return institution_payload(db, institution)


@router.post("/institutions/{institution_id}/admins", status_code=201)
def invite_college_admin(institution_id: UUID, payload: CollegeAdminInvite, background_tasks: BackgroundTasks,
                         request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    require_super_admin(user)
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")
    account = create_invited_user(db, background_tasks, email=payload.email, full_name=payload.full_name,
                                  role=Role.college_admin, institution_id=institution.id, department_id=None)
    db.add(AuditEvent(institution_id=institution.id, actor_id=user.id, action="invited",
                      resource_type="college_admin", resource_id=str(account.id)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return {"id": str(account.id), "full_name": account.full_name, "email": account.email,
            "is_active": account.is_active, "email_verified": account.email_verified, "invite_sent": True}


@router.post("/institutions/{institution_id}/admins/{admin_id}/resend-setup")
def resend_admin_setup(institution_id: UUID, admin_id: UUID, background_tasks: BackgroundTasks, request: Request,
                       db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    require_super_admin(user)
    account = db.scalar(select(User).where(User.id == admin_id, User.institution_id == institution_id,
                                           User.role == Role.college_admin))
    if not account:
        raise HTTPException(status_code=404, detail="College admin account not found.")
    if not account.is_active:
        raise HTTPException(status_code=409, detail="Reactivate this account before sending a setup link.")
    from app.auth_mail import queue_password_link
    queue_password_link(db, background_tasks, account)
    db.add(AuditEvent(institution_id=institution_id, actor_id=user.id, action="resent_setup_link",
                      resource_type="college_admin", resource_id=str(account.id)))
    db.commit()
    return {"user_id": str(account.id), "sent": True}


@router.patch("/institutions/{institution_id}/admins/{admin_id}/status")
def update_admin_status(institution_id: UUID, admin_id: UUID, payload: AccountStatus, request: Request,
                        db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    require_super_admin(user)
    account = db.scalar(select(User).where(User.id == admin_id, User.institution_id == institution_id,
                                           User.role == Role.college_admin))
    if not account:
        raise HTTPException(status_code=404, detail="College admin account not found.")
    if account.id == user.id:
        raise HTTPException(status_code=409, detail="You cannot change your own account status here.")
    account.is_active = payload.is_active
    action = "activated" if payload.is_active else "deactivated"
    if not payload.is_active:
        db.query(RefreshSession).filter(RefreshSession.user_id == account.id,
                                        RefreshSession.revoked_at.is_(None)).update(
            {RefreshSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False)
    db.add(AuditEvent(institution_id=institution_id, actor_id=user.id, action=action,
                      resource_type="college_admin", resource_id=str(account.id)))
    db.commit()
    return {"id": str(account.id), "is_active": account.is_active}
