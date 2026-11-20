import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (AcademicTerm, Department, Faculty, Role, Room, Section, Subject,
                        Timetable, TimetableEntry, User)


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _label(value: object, limit: int = 120) -> str:
    return " ".join(str(value).split())[:limit]


def build_assistant_context(db: Session, user: User, term_id, department_id) -> str:
    """Build a small, read-only context from records the caller may access."""
    if user.role not in (Role.super_admin, Role.college_admin, Role.hod) or not term_id or not department_id:
        return ""

    term = db.get(AcademicTerm, term_id)
    department = db.get(Department, department_id)
    if not term or not department or term.institution_id != department.institution_id:
        return ""
    if user.role != Role.super_admin and department.institution_id != user.institution_id:
        return ""
    if user.role == Role.hod and department.id != user.department_id:
        return ""

    rooms = db.scalars(select(Room).where(Room.institution_id == department.institution_id)
                       .order_by(Room.name).limit(100)).all()
    room_records = [{"name": _label(room.name), "type": _label(room.room_type), "capacity": room.capacity}
                    for room in rooms]

    timetable = db.scalar(select(Timetable).where(
        Timetable.institution_id == department.institution_id,
        Timetable.term_id == term.id,
        Timetable.department_id == department.id,
        Timetable.status == "published",
    ).order_by(Timetable.created_at.desc(), Timetable.version.desc()).limit(1))

    session_records: list[dict] = []
    if timetable:
        rows = db.execute(
            select(TimetableEntry, Subject, Section, Faculty, User, Room)
            .join(Subject, Subject.id == TimetableEntry.subject_id)
            .join(Section, Section.id == TimetableEntry.section_id)
            .join(Faculty, Faculty.id == TimetableEntry.faculty_id)
            .join(User, User.id == Faculty.user_id)
            .join(Room, Room.id == TimetableEntry.room_id)
            .where(TimetableEntry.timetable_id == timetable.id)
            .order_by(TimetableEntry.day, TimetableEntry.start_period, Subject.name)
            .limit(60)
        ).all()
        weekdays = timetable.weekdays or list(range(timetable.days))
        labels = timetable.period_labels or []
        for entry, subject, section, _faculty, faculty_user, room in rows:
            weekday = weekdays[entry.day] if 0 <= entry.day < len(weekdays) else entry.day
            day_name = WEEKDAYS[weekday] if isinstance(weekday, int) and 0 <= weekday < len(WEEKDAYS) else str(weekday)
            period = labels[entry.start_period] if 0 <= entry.start_period < len(labels) else f"period {entry.start_period + 1}"
            session_records.append({
                "weekday": day_name,
                "start": _label(period),
                "subject": _label(subject.name),
                "section": _label(section.name),
                "faculty": _label(faculty_user.full_name),
                "room": _label(room.name),
                "duration_periods": entry.duration_periods,
            })

    context = {
        "scope": "selected_department_only",
        "institution_id": str(department.institution_id),
        "department": _label(department.name),
        "term": _label(term.name),
        "academic_year": _label(term.academic_year),
        "room_directory": room_records,
        "latest_published_timetable": ({"name": _label(timetable.name), "version": timetable.version}
                                        if timetable else None),
        "published_sessions": session_records,
        "limitations": "Does not include other departments' bookings; cannot establish campus-wide room availability.",
    }
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))
