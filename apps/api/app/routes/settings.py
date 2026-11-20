from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_user, ensure_browser_origin
from app.models import AuditEvent, Institution, Role, User
from app.schemas import InstitutionCalendarBreak
from app.calendar import maximum_period_count

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)


class InstitutionUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    timezone: str = Field(min_length=3, max_length=80)
    timetable_period_start: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timetable_period_minutes: int | None = Field(default=None, ge=20, le=180)
    timetable_breaks: list[InstitutionCalendarBreak] | None = Field(default=None, max_length=40)


class NotificationPreferencesUpdate(BaseModel):
    schedule_updates: bool
    approval_updates: bool


@router.get("")
def read_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    institution = db.get(Institution, user.institution_id) if user.institution_id else None
    return {"profile": {"full_name": user.full_name, "email": user.email, "role": user.role.value},
            "institution": ({"name": institution.name, "timezone": institution.timezone,
                             "timetable_period_start": institution.timetable_period_start,
                             "timetable_period_minutes": institution.timetable_period_minutes,
                             "timetable_breaks": institution.timetable_breaks or []} if institution else None),
            "notification_preferences": {"schedule_updates": True, "approval_updates": True,
                                         **(user.notification_preferences or {})},
            "can_manage_institution": user.role in (Role.super_admin, Role.college_admin)}


@router.patch("/notifications")
def update_notification_preferences(payload: NotificationPreferencesUpdate, request: Request,
                                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_browser_origin(request)
    user.notification_preferences = payload.model_dump()
    db.add(AuditEvent(institution_id=user.institution_id, actor_id=user.id, action="updated",
                      resource_type="notification_preferences", resource_id=str(user.id)))
    db.commit()
    return {"notification_preferences": user.notification_preferences}


@router.patch("/profile")
def update_profile(payload: ProfileUpdate, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_browser_origin(request)
    full_name = payload.full_name.strip()
    if len(full_name) < 2:
        raise HTTPException(status_code=422, detail="Enter a name with at least two characters.")
    user.full_name = full_name
    db.add(AuditEvent(institution_id=user.institution_id, actor_id=user.id, action="updated",
                      resource_type="user_profile", resource_id=str(user.id)))
    db.commit()
    return {"full_name": user.full_name}


@router.patch("/institution")
def update_institution(payload: InstitutionUpdate, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_browser_origin(request)
    if user.role not in (Role.super_admin, Role.college_admin):
        raise HTTPException(status_code=403, detail="Only a college admin can change institution settings.")
    if not user.institution_id:
        raise HTTPException(status_code=422, detail="Choose an institution before changing its settings.")
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Enter an institution name with at least two characters.")
    try:
        ZoneInfo(payload.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail="Enter a valid IANA timezone, for example Asia/Kolkata.")
    institution = db.get(Institution, user.institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")
    institution.name = name
    institution.timezone = payload.timezone
    start = payload.timetable_period_start or institution.timetable_period_start
    duration = payload.timetable_period_minutes or institution.timetable_period_minutes
    if maximum_period_count(start, duration) < 1:
        raise HTTPException(status_code=422, detail="The bell-time settings must leave room for at least one period before midnight.")
    institution.timetable_period_start = start
    institution.timetable_period_minutes = duration
    if payload.timetable_breaks is not None:
        institution.timetable_breaks = [item.model_dump() for item in payload.timetable_breaks]
    db.add(AuditEvent(institution_id=institution.id, actor_id=user.id, action="updated",
                      resource_type="institution_settings", resource_id=str(institution.id)))
    db.commit()
    return {"name": institution.name, "timezone": institution.timezone,
            "timetable_period_start": institution.timetable_period_start,
            "timetable_period_minutes": institution.timetable_period_minutes,
            "timetable_breaks": institution.timetable_breaks or []}
