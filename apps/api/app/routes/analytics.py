import csv
from collections import Counter, defaultdict
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.calendar import build_period_labels
from app.dependencies import current_user, ensure_manager
from app.models import (AcademicTerm, Department, Faculty, Institution, Room, Role, Section,
                        Semester, Student, Subject, Timetable, TimetableEntry, User)
router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

REPORTS = {
    "schedule": {
        "title": "Published schedule detail",
        "description": "Every published class session in your access scope.",
        "columns": [("institution", "Institution"), ("term", "Term"), ("academic_year", "Academic year"), ("department", "Department"),
                    ("section", "Section"), ("subject_code", "Subject code"), ("subject", "Subject"),
                    ("faculty", "Faculty"), ("room", "Room"), ("day", "Day"), ("period", "Period"), ("start_time", "Start time"),
                    ("duration_periods", "Periods"), ("version", "Version"), ("timetable", "Timetable")],
    },
    "faculty-load": {
        "title": "Faculty teaching load",
        "description": "Published session and teaching-period totals by faculty member.",
        "columns": [("faculty", "Faculty"), ("institution", "Institution"), ("department", "Department"), ("sessions", "Sessions"),
                    ("teaching_periods", "Teaching periods"), ("sections", "Sections")],
    },
    "room-utilization": {
        "title": "Room utilization",
        "description": "Published bookings and capacity utilization for each room.",
        "columns": [("room", "Room"), ("institution", "Institution"), ("room_type", "Room type"), ("capacity", "Seats"),
                    ("sessions", "Sessions"), ("booked_periods", "Booked periods"),
                    ("available_periods", "Available periods"), ("utilization_percent", "Utilization (%)")],
    },
    "conflicts": {
        "title": "Published schedule conflicts",
        "description": "Overlapping room, faculty, or section assignments in published timetables.",
        "columns": [("timetable", "Timetable"), ("institution", "Institution"), ("term", "Term"), ("department", "Department"),
                    ("day", "Day"), ("periods", "Periods"), ("reason", "Conflict"), ("entry_ids", "Session IDs")],
    },
}
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _published_timetables(db: Session, user: User, term_id: UUID | None):
    ensure_manager(user, user.department_id)
    query = select(Timetable).where(Timetable.status == "published")
    if user.role != Role.super_admin:
        query = query.where(Timetable.institution_id == user.institution_id)
    if user.role == Role.hod and user.department_id:
        query = query.where(Timetable.department_id == user.department_id)
    if term_id:
        query = query.where(Timetable.term_id == term_id)
    return db.scalars(query.order_by(Timetable.term_id, Timetable.department_id, Timetable.version.desc())).all()


def _published_conflicts(db: Session, timetables: list[Timetable]) -> list[dict]:
    timetable_ids = [item.id for item in timetables]
    if not timetable_ids:
        return []
    rows = db.execute(select(TimetableEntry, Timetable, Institution.name, AcademicTerm.name, Department.name,
                             Institution.timetable_period_start)
                      .join(Timetable, TimetableEntry.timetable_id == Timetable.id)
                      .join(Institution, Timetable.institution_id == Institution.id)
                      .join(AcademicTerm, Timetable.term_id == AcademicTerm.id)
                      .join(Department, Timetable.department_id == Department.id)
                      .where(TimetableEntry.timetable_id.in_(timetable_ids))).all()

    def interval(entry: TimetableEntry, timetable: Timetable, institution_start: str) -> tuple[int, int]:
        period_length = max(1, timetable.period_minutes or 60)
        if timetable.period_labels and 0 <= entry.start_period < len(timetable.period_labels):
            hour, minute = (int(part) for part in timetable.period_labels[entry.start_period].split(":"))
            start = hour * 60 + minute
        else:
            hour, minute = (int(part) for part in (institution_start or "09:00").split(":"))
            start = hour * 60 + minute + entry.start_period * period_length
        return start, start + entry.duration_periods * period_length

    grouped = defaultdict(list)
    for row in rows:
        entry, timetable, institution_name, term, department, institution_start = row
        weekdays = timetable.weekdays or list(range(timetable.days))
        calendar_day = weekdays[entry.day] if 0 <= entry.day < len(weekdays) else entry.day
        start, end = interval(entry, timetable, institution_start)
        grouped[(timetable.term_id, calendar_day)].append((row, start, end))

    def clock_label(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    conflicts = []
    for day_rows in grouped.values():
        day_rows.sort(key=lambda item: item[1])
        for index, (first_row, first_start, first_end) in enumerate(day_rows):
            first, first_table, first_institution, first_term, first_department, _ = first_row
            for second_row, second_start, second_end in day_rows[index + 1:]:
                if second_start >= first_end:
                    break
                second, second_table, second_institution, second_term, second_department, _ = second_row
                overlap_start = max(first_start, second_start)
                overlap_end = min(first_end, second_end)
                if overlap_start >= overlap_end:
                    continue
                if first.section_id == second.section_id:
                    reason = "The same section is scheduled twice."
                elif first.faculty_id == second.faculty_id:
                    reason = "The same faculty member is scheduled twice."
                elif first.room_id == second.room_id:
                    reason = "The same room is scheduled twice."
                else:
                    continue
                first_label = f"{first_table.name} · v{first_table.version}"
                second_label = f"{second_table.name} · v{second_table.version}"
                weekdays = first_table.weekdays or list(range(first_table.days))
                conflicts.append({
                    "timetable": first_label if first_table.id == second_table.id else f"{first_label} / {second_label}",
                    "institution": first_institution if first_table.institution_id == second_table.institution_id
                    else f"{first_institution} / {second_institution}",
                    "term": first_term,
                    "department": first_department if first_table.department_id == second_table.department_id
                    else f"{first_department} / {second_department}",
                    "day": DAY_NAMES[weekdays[first.day]]
                    if 0 <= first.day < len(weekdays) and 0 <= weekdays[first.day] < len(DAY_NAMES)
                    else DAY_NAMES[first.day] if 0 <= first.day < len(DAY_NAMES) else str(first.day),
                    "periods": f"{clock_label(overlap_start)}–{clock_label(overlap_end)}",
                    "reason": reason,
                    "entry_ids": f"{first.id}, {second.id}",
                })
    return conflicts


def _report_rows(report_type: str, db: Session, user: User, timetables: list[Timetable]) -> list[dict]:
    ids = [timetable.id for timetable in timetables]
    if not ids:
        return []
    if report_type == "schedule":
        rows = db.execute(select(TimetableEntry, Institution.name, Institution.timetable_period_start,
                                 Institution.timetable_period_minutes, AcademicTerm.name, AcademicTerm.academic_year,
                                 Department.name, Section.name, Subject.code, Subject.name,
                                 User.full_name, Room.name, Timetable.version, Timetable.name, Timetable.weekdays,
                                 Timetable.days, Timetable.period_labels)
                          .join(Timetable, TimetableEntry.timetable_id == Timetable.id)
                          .join(Institution, Timetable.institution_id == Institution.id)
                          .join(AcademicTerm, Timetable.term_id == AcademicTerm.id)
                          .join(Department, Timetable.department_id == Department.id)
                          .join(Section, TimetableEntry.section_id == Section.id)
                          .join(Subject, TimetableEntry.subject_id == Subject.id)
                          .join(Faculty, TimetableEntry.faculty_id == Faculty.id)
                          .join(User, Faculty.user_id == User.id)
                          .join(Room, TimetableEntry.room_id == Room.id)
                          .where(TimetableEntry.timetable_id.in_(ids))
                          .order_by(AcademicTerm.name, Department.name, Section.name,
                                    TimetableEntry.day, TimetableEntry.start_period)).all()
        return [{"institution": institution, "term": term, "academic_year": year, "department": department, "section": section,
                 "subject_code": subject_code, "subject": subject, "faculty": faculty, "room": room,
                 "day": DAY_NAMES[weekdays[entry.day]]
                 if weekdays and 0 <= entry.day < len(weekdays) and 0 <= weekdays[entry.day] < len(DAY_NAMES)
                 else DAY_NAMES[entry.day] if 0 <= entry.day < len(DAY_NAMES) else str(entry.day),
                 "period": entry.start_period + 1,
                 "start_time": period_labels[entry.start_period] if period_labels and 0 <= entry.start_period < len(period_labels)
                 else build_period_labels(bell_start, bell_minutes, entry.start_period + 1)[entry.start_period],
                 "duration_periods": entry.duration_periods,
                 "version": version, "timetable": timetable_name}
                for entry, institution, bell_start, bell_minutes, term, year, department, section, subject_code, subject, faculty, room, version, timetable_name, weekdays, days, period_labels in rows]
    if report_type == "faculty-load":
        query = (select(User.full_name, Institution.name, Department.name, func.count(TimetableEntry.id),
                        func.coalesce(func.sum(TimetableEntry.duration_periods), 0),
                        func.count(func.distinct(Section.id)))
                 .join(Faculty, Faculty.user_id == User.id)
                 .join(Department, Faculty.department_id == Department.id)
                 .join(Institution, Department.institution_id == Institution.id)
                 .join(TimetableEntry, TimetableEntry.faculty_id == Faculty.id)
                 .join(Timetable, TimetableEntry.timetable_id == Timetable.id)
                 .join(Section, TimetableEntry.section_id == Section.id)
                 .where(TimetableEntry.timetable_id.in_(ids))
                 .group_by(Faculty.id, User.full_name, Institution.name, Department.name)
                 .order_by(func.sum(TimetableEntry.duration_periods).desc(), User.full_name))
        return [{"faculty": name, "institution": institution, "department": department, "sessions": sessions,
                 "teaching_periods": periods, "sections": sections}
                for name, institution, department, sessions, periods, sections in db.execute(query).all()]
    if report_type == "room-utilization":
        institution_ids = {item.institution_id for item in timetables}
        room_query = select(Room)
        if user.role != Role.super_admin:
            room_query = room_query.where(Room.institution_id == user.institution_id)
        elif institution_ids:
            room_query = room_query.where(Room.institution_id.in_(institution_ids))
        room_rows = db.execute(room_query.add_columns(Institution.name).join(Institution, Room.institution_id == Institution.id)
                                .order_by(Institution.name, Room.name)).all()
        bookings = db.execute(select(TimetableEntry.room_id, func.count(TimetableEntry.id),
                                     func.coalesce(func.sum(TimetableEntry.duration_periods), 0))
                              .where(TimetableEntry.timetable_id.in_(ids))
                              .group_by(TimetableEntry.room_id)).all()
        bookings_by_room = {room_id: (sessions, periods) for room_id, sessions, periods in bookings}
        available_by_institution = Counter()
        for timetable in timetables:
            available_by_institution[timetable.institution_id] += max(timetable.days, 1) * max(timetable.periods_per_day, 1)
        result = []
        for room, institution_name in room_rows:
            sessions, booked = bookings_by_room.get(room.id, (0, 0))
            available_periods = available_by_institution.get(room.institution_id, 0)
            result.append({"room": room.name, "institution": institution_name, "room_type": room.room_type, "capacity": room.capacity,
                           "sessions": sessions, "booked_periods": booked, "available_periods": available_periods,
                           "utilization_percent": round(100 * booked / available_periods, 1) if available_periods else 0})
        return result
    if report_type == "conflicts":
        return _published_conflicts(db, timetables)
    raise HTTPException(status_code=404, detail="Choose a supported report type.")


def _report(report_type: str, db: Session, user: User, term_id: UUID | None) -> dict:
    definition = REPORTS.get(report_type)
    if not definition:
        raise HTTPException(status_code=404, detail="Choose a supported report type.")
    timetables = _published_timetables(db, user, term_id)
    return {"report_type": report_type, "title": definition["title"],
            "description": definition["description"], "scope": "department" if user.role == Role.hod else "institution" if user.role != Role.super_admin else "all institutions",
            "columns": [{"key": key, "label": label} for key, label in definition["columns"]],
            "rows": _report_rows(report_type, db, user, timetables)}


@router.get("/reports/{report_type}")
def analytics_report(report_type: str, term_id: UUID | None = None, db: Session = Depends(get_db),
                     user: User = Depends(current_user)):
    return _report(report_type, db, user, term_id)


@router.get("/reports/{report_type}/export.csv")
def export_analytics_report(report_type: str, term_id: UUID | None = None, db: Session = Depends(get_db),
                            user: User = Depends(current_user)):
    report = _report(report_type, db, user, term_id)
    output = StringIO(newline="")
    columns = report["columns"]
    writer = csv.writer(output)
    writer.writerow([column["label"] for column in columns])
    for row in report["rows"]:
        cells = []
        for column in columns:
            value = row.get(column["key"], "")
            text = ", ".join(value) if isinstance(value, list) else str(value if value is not None else "")
            formula_value = text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@"))
            cells.append(f"'{text}" if formula_value else text)
        writer.writerow(cells)
    safe_name = report_type.replace("-", "_")
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="campusflow_{safe_name}.csv"'})


@router.get("/summary")
def analytics_summary(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Return institution/department scoped operational metrics for the dashboard."""
    ensure_manager(user, user.department_id)
    institution_id = user.institution_id
    department_id = user.department_id if user.role == Role.hod else None
    department_query = select(func.count(Department.id))
    rooms_query = select(func.count(Room.id))
    faculty_query = select(func.count(Faculty.id)).join(Department, Faculty.department_id == Department.id)
    sections_query = select(func.count(Section.id)).join(Semester, Section.semester_id == Semester.id).join(Department, Semester.department_id == Department.id)
    students_query = select(func.count(Student.id)).join(Section, Student.section_id == Section.id).join(Semester, Section.semester_id == Semester.id).join(Department, Semester.department_id == Department.id)
    if user.role != Role.super_admin:
        department_query = department_query.where(Department.institution_id == institution_id)
        rooms_query = rooms_query.where(Room.institution_id == institution_id)
        faculty_query = faculty_query.where(Department.institution_id == institution_id)
        sections_query = sections_query.where(Department.institution_id == institution_id)
        students_query = students_query.where(Department.institution_id == institution_id)
    departments = db.scalar(department_query) or 0
    if department_id:
        faculty_query = faculty_query.where(Department.id == department_id)
        sections_query = sections_query.where(Department.id == department_id)
        students_query = students_query.where(Department.id == department_id)
        departments = 1
    rooms = db.scalar(rooms_query) or 0
    faculty_count = db.scalar(faculty_query) or 0
    section_count = db.scalar(sections_query) or 0
    student_count = db.scalar(students_query) or 0

    timetable_query = select(Timetable).where(Timetable.status == "published")
    if user.role != Role.super_admin:
        timetable_query = timetable_query.where(Timetable.institution_id == institution_id)
    if department_id:
        timetable_query = timetable_query.where(Timetable.department_id == department_id)
    published = db.scalars(timetable_query.order_by(Timetable.created_at.desc())).all()
    current_terms = set(db.scalars(select(AcademicTerm.id).where(AcademicTerm.is_current.is_(True))).all())
    selected = [item for item in published if item.term_id in current_terms]
    if not selected:
        selected = published[:1]

    weekly_sessions = 0
    conflict_count = 0
    daily = Counter()
    faculty_load = Counter()
    if selected:
        selected_ids = [item.id for item in selected]
        weekly_sessions = db.scalar(select(func.count(TimetableEntry.id)).where(TimetableEntry.timetable_id.in_(selected_ids))) or 0
        conflict_count = len(_published_conflicts(db, selected))
        rows = db.execute(select(TimetableEntry.day, Faculty.id, User.full_name)
                          .join(Faculty, TimetableEntry.faculty_id == Faculty.id)
                          .join(User, Faculty.user_id == User.id)
                          .where(TimetableEntry.timetable_id.in_(selected_ids))).all()
        for day, faculty_id, full_name in rows:
            daily[int(day)] += 1
            faculty_load[str(faculty_id), full_name] += 1

    slot_total = sum(max(item.days, 1) * max(item.periods_per_day, 1) * max(rooms, 1) for item in selected)
    occupied = db.scalar(select(func.coalesce(func.sum(TimetableEntry.duration_periods), 0))
                         .where(TimetableEntry.timetable_id.in_([item.id for item in selected]))) if selected else 0
    utilization = round(100 * occupied / slot_total, 1) if slot_total else 0
    days = [{"day": day, "sessions": daily.get(day, 0)} for day in range(max((item.days for item in selected), default=5))]
    top_faculty = [{"id": key[0], "name": key[1], "sessions": count}
                   for key, count in faculty_load.most_common(8)]

    return {
        "scope": "department" if department_id else "institution" if user.role != Role.super_admin else "all institutions",
        "totals": {"departments": departments, "faculty": faculty_count, "students": student_count,
                   "sections": section_count, "rooms": rooms, "published_timetables": len(published),
                   "scheduled_sessions": weekly_sessions, "open_conflicts": conflict_count},
        "room_utilization_percent": utilization,
        "daily_sessions": days,
        "faculty_load": top_faculty,
        "selected_timetables": [{"id": str(item.id), "name": item.name, "version": item.version,
                                 "term_id": str(item.term_id), "days": item.days,
                                 "periods_per_day": item.periods_per_day} for item in selected],
    }
