from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.calendar import build_period_labels
from app.dependencies import current_user, ensure_browser_origin
from app.models import (AcademicTerm, Faculty, Notification, Role, Room, Section, Student, Subject,
                        Timetable, TimetableEntry, User)

router = APIRouter(prefix="/api/v1/me", tags=["personal workspace"])


@router.get("/schedule")
def my_published_schedule(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role == Role.student:
        student = db.scalar(select(Student).where(Student.user_id == user.id))
        if not student:
            return {"role": user.role.value, "entries": []}
        resource_filter = TimetableEntry.section_id == student.section_id
    elif user.role == Role.faculty:
        faculty = db.scalar(select(Faculty).where(Faculty.user_id == user.id))
        if not faculty:
            return {"role": user.role.value, "entries": []}
        resource_filter = TimetableEntry.faculty_id == faculty.id
    else:
        raise HTTPException(status_code=403, detail="This schedule view is for faculty and students.")

    query = (select(TimetableEntry, Timetable, Subject, Section, Room, AcademicTerm)
             .join(Timetable, TimetableEntry.timetable_id == Timetable.id)
             .join(AcademicTerm, Timetable.term_id == AcademicTerm.id)
                      .join(Subject, TimetableEntry.subject_id == Subject.id)
                      .join(Section, TimetableEntry.section_id == Section.id)
                      .join(Room, TimetableEntry.room_id == Room.id)
             .where(Timetable.status == "published", resource_filter)
             .order_by(Timetable.created_at.desc(), TimetableEntry.day, TimetableEntry.start_period))
    rows = db.execute(query).all()
    return {"role": user.role.value, "entries": [
        {"id": str(entry.id), "timetable": timetable.name, "version": timetable.version,
         "term_id": str(timetable.term_id), "term": term.name, "academic_year": term.academic_year,
         "is_current_term": term.is_current, "days": timetable.days, "periods_per_day": timetable.periods_per_day,
         "period_labels": timetable.period_labels or build_period_labels("09:00", 60, timetable.periods_per_day),
         "weekdays": timetable.weekdays or list(range(timetable.days)),
         "section": section.name,
         "section_id": str(section.id), "subject": subject.name, "subject_code": subject.code,
         "room": room.name, "day": entry.day,
         "weekday": (timetable.weekdays or list(range(timetable.days)))[entry.day]
         if 0 <= entry.day < len(timetable.weekdays or list(range(timetable.days))) else entry.day,
         "period": entry.start_period,
         "duration_periods": entry.duration_periods}
        for entry, timetable, subject, section, room, term in rows]}


@router.get("/notifications")
def my_notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.scalars(select(Notification).where(Notification.user_id == user.id)
                       .order_by(Notification.created_at.desc()).limit(100)).all()
    return [{"id": str(item.id), "title": item.title, "body": item.body,
             "read": item.read_at is not None, "created_at": item.created_at} for item in items]


@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_read(notification_id: UUID, request: Request,
                           db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    item = db.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    item.read_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    db.query(Notification).filter(Notification.user_id == user.id, Notification.read_at.is_(None)).update(
        {Notification.read_at: datetime.now(timezone.utc)})
    db.commit()
