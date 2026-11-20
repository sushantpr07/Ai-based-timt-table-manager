from uuid import UUID
from datetime import datetime, timezone

import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth_mail import queue_password_link
from app.calendar import build_period_labels, calendar_break_slots, maximum_period_count
from app.dependencies import current_user, ensure_browser_origin, ensure_institution, ensure_manager
from app.models import (AcademicTerm, AuditEvent, Department, Faculty, FacultyAvailability, GenerationRun,
                        Institution, Notification, Room, Section, Semester, Student, Subject, TeachingAssignment,
                        Timetable, TimetableEntry, User, Role, RefreshSession)
from app.security import hash_password
from app.scheduler import ScheduleInfeasible, generate_schedule
from app.schemas import (FacultyAvailabilityUpdate, StoredTimetableGenerateRequest,
                         TeachingAssignmentCreate, TimetableApprovalDecision, TimetableEntryMove)

router = APIRouter(prefix="/api/v1/campus", tags=["campus setup"])


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    code: str = Field(min_length=2, max_length=24)
    institution_id: UUID | None = None


class TermCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    academic_year: str = Field(min_length=4, max_length=20)
    is_current: bool = False
    institution_id: UUID | None = None


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    capacity: int = Field(ge=1, le=5000)
    room_type: str = Field(default="classroom", min_length=1, max_length=24)
    institution_id: UUID | None = None


class SubjectCreate(BaseModel):
    code: str = Field(min_length=2, max_length=24)
    name: str = Field(min_length=2, max_length=160)
    department_id: UUID
    weekly_sessions: int = Field(default=3, ge=1, le=20)
    room_type: str = Field(default="classroom", min_length=1, max_length=24)


class SemesterCreate(BaseModel):
    term_id: UUID
    department_id: UUID
    number: int = Field(ge=1, le=20)


class SectionCreate(BaseModel):
    semester_id: UUID
    name: str = Field(min_length=1, max_length=40)
    strength: int = Field(ge=1, le=1000)


class FacultyInvite(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    department_id: UUID
    max_weekly_periods: int = Field(default=18, ge=1, le=50)


class StudentInvite(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    section_id: UUID
    student_number: str = Field(min_length=1, max_length=40)


class HodInvite(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    department_id: UUID


class AccountStatusUpdate(BaseModel):
    is_active: bool


class FacultyUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    full_name: str = Field(min_length=2, max_length=160)
    department_id: UUID
    max_weekly_periods: int = Field(ge=1, le=50)


class StudentUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    full_name: str = Field(min_length=2, max_length=160)
    section_id: UUID
    student_number: str = Field(min_length=1, max_length=40)


class HodUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    full_name: str = Field(min_length=2, max_length=160)
    department_id: UUID


class CampusImport(BaseModel):
    rows: list[dict] = Field(min_length=1, max_length=500)


def audit(db: Session, user: User, action: str, resource_type: str, resource_id: UUID):
    db.add(AuditEvent(institution_id=user.institution_id, actor_id=user.id, action=action,
                      resource_type=resource_type, resource_id=str(resource_id)))


def notify_user(db: Session, user_id: UUID, category: str, title: str, body: str):
    recipient = db.get(User, user_id)
    preferences = recipient.notification_preferences if recipient and recipient.notification_preferences else {}
    if recipient and preferences.get(category, True):
        db.add(Notification(user_id=user_id, title=title, body=body))


def department_or_404(db: Session, department_id: UUID) -> Department:
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found.")
    return department


def term_or_404(db: Session, term_id: UUID) -> AcademicTerm:
    term = db.get(AcademicTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Academic term not found.")
    return term


def import_department(db: Session, user: User, row: dict) -> Department | None:
    code = str(row.get("department_code", "")).strip().upper()
    query = select(Department).where(Department.code == code)
    if user.role == Role.super_admin:
        if row.get("institution_id"):
            try:
                query = query.where(Department.institution_id == UUID(str(row["institution_id"])))
            except ValueError:
                raise ValueError("institution_id must be a valid UUID.")
    else:
        query = query.where(Department.institution_id == user.institution_id)
    matches = db.scalars(query.limit(2)).all()
    if len(matches) > 1:
        raise ValueError("department_code is ambiguous; include institution_id for this import.")
    return matches[0] if matches else None


def import_record(db: Session, user: User, resource: str, row: dict):
    """Resolve human-readable CSV references, validate one row, and stage its record."""
    columns = {
        "departments": {"name", "code", "institution_id"},
        "terms": {"name", "academic_year", "is_current", "institution_id"},
        "rooms": {"name", "capacity", "room_type", "institution_id"},
        "subjects": {"code", "name", "department_code", "weekly_sessions", "room_type", "institution_id"},
        "semesters": {"department_code", "term_name", "academic_year", "number", "institution_id"},
        "sections": {"department_code", "term_name", "academic_year", "semester_number", "name", "strength", "institution_id"},
        "teaching-assignments": {"department_code", "term_name", "academic_year", "semester_number", "section_name", "subject_code", "faculty_email", "sessions_per_week", "duration_periods", "institution_id"},
    }
    unknown_columns = set(row) - columns.get(resource, set())
    if unknown_columns:
        raise ValueError(f"Unknown column(s): {', '.join(sorted(unknown_columns))}.")
    row = {key: value.strip() if isinstance(value, str) else value for key, value in row.items()}
    if resource == "departments":
        values = DepartmentCreate.model_validate(row)
        ensure_manager(user)
        institution_id = values.institution_id if user.role == Role.super_admin else user.institution_id
        if not institution_id or not db.get(Institution, institution_id):
            raise ValueError("institution_id must identify an existing institution for this account.")
        record = Department(institution_id=institution_id, name=values.name.strip(), code=values.code.strip().upper())
        label = "department"
    elif resource == "terms":
        values = TermCreate.model_validate(row)
        ensure_manager(user)
        institution_id = values.institution_id if user.role == Role.super_admin else user.institution_id
        if not institution_id or not db.get(Institution, institution_id):
            raise ValueError("institution_id must identify an existing institution for this account.")
        if values.is_current:
            db.query(AcademicTerm).filter(AcademicTerm.institution_id == institution_id).update({AcademicTerm.is_current: False})
        record = AcademicTerm(institution_id=institution_id, name=values.name.strip(),
                              academic_year=values.academic_year.strip(), is_current=values.is_current)
        label = "academic_term"
    elif resource == "rooms":
        values = RoomCreate.model_validate(row)
        ensure_manager(user)
        institution_id = values.institution_id if user.role == Role.super_admin else user.institution_id
        if not institution_id or not db.get(Institution, institution_id):
            raise ValueError("institution_id must identify an existing institution for this account.")
        record = Room(institution_id=institution_id, name=values.name.strip(), capacity=values.capacity,
                      room_type=values.room_type.strip().lower())
        label = "room"
    elif resource == "subjects":
        department = import_department(db, user, row)
        if not department:
            raise ValueError("department_code does not match an existing department.")
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        values = SubjectCreate.model_validate({**row, "department_id": department.id})
        record = Subject(department_id=department.id, code=values.code.strip().upper(), name=values.name.strip(),
                         weekly_sessions=values.weekly_sessions, room_type=values.room_type.strip().lower())
        label = "subject"
    elif resource == "semesters":
        department = import_department(db, user, row)
        term = db.scalar(select(AcademicTerm).where(AcademicTerm.name == str(row.get("term_name", "")).strip(),
                                                    AcademicTerm.academic_year == str(row.get("academic_year", "")).strip(),
                                                    AcademicTerm.institution_id == department.institution_id if department else False))
        if not department or not term:
            raise ValueError("department_code, term_name, and academic_year must match existing records.")
        if department.institution_id != term.institution_id:
            raise ValueError("Department and term must belong to the same institution.")
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        values = SemesterCreate.model_validate({**row, "department_id": department.id, "term_id": term.id})
        record = Semester(department_id=department.id, term_id=term.id, number=values.number)
        label = "semester"
    elif resource == "sections":
        department = import_department(db, user, row)
        term_name, academic_year = str(row.get("term_name", "")).strip(), str(row.get("academic_year", "")).strip()
        try:
            semester_number = int(row.get("semester_number", 0))
        except (TypeError, ValueError):
            raise ValueError("semester_number must be a number.")
        semester = db.scalar(select(Semester).join(Department, Semester.department_id == Department.id)
                              .join(AcademicTerm, Semester.term_id == AcademicTerm.id)
                              .where(Semester.department_id == department.id if department else False, AcademicTerm.name == term_name,
                                     AcademicTerm.academic_year == academic_year, Semester.number == semester_number))
        if not department or not semester:
            raise ValueError("Department, term, and semester number must match existing records.")
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        values = SectionCreate.model_validate({**row, "semester_id": semester.id})
        record = Section(semester_id=semester.id, name=values.name.strip(), strength=values.strength)
        label = "section"
    elif resource == "teaching-assignments":
        department = import_department(db, user, row)
        term_name, academic_year = str(row.get("term_name", "")).strip(), str(row.get("academic_year", "")).strip()
        try:
            semester_number = int(row.get("semester_number", 0))
        except (TypeError, ValueError):
            raise ValueError("semester_number must be a number.")
        section = db.scalar(select(Section).join(Semester, Section.semester_id == Semester.id)
                             .join(Department, Semester.department_id == Department.id)
                             .join(AcademicTerm, Semester.term_id == AcademicTerm.id)
                             .where(Semester.department_id == department.id if department else False, AcademicTerm.name == term_name,
                                    AcademicTerm.academic_year == academic_year, Semester.number == semester_number,
                                    Section.name == str(row.get("section_name", "")).strip()))
        subject = db.scalar(select(Subject).where(Subject.department_id == department.id if department else False,
                                                  Subject.code == str(row.get("subject_code", "")).strip().upper()))
        faculty = db.scalar(select(Faculty).join(User, Faculty.user_id == User.id)
                            .where(Faculty.department_id == department.id if department else False,
                                   User.email == str(row.get("faculty_email", "")).strip().lower()))
        if not department or not section or not subject or not faculty:
            raise ValueError("Department, term, semester, section, subject, and faculty email must match existing records.")
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        values = TeachingAssignmentCreate.model_validate({**row, "subject_id": subject.id,
                                                         "section_id": section.id, "faculty_id": faculty.id})
        record = TeachingAssignment(subject_id=subject.id, section_id=section.id, faculty_id=faculty.id,
                                    sessions_per_week=values.sessions_per_week, duration_periods=values.duration_periods)
        label = "teaching_assignment"
    else:
        raise ValueError("Bulk import is not enabled for this record type.")
    db.add(record)
    db.flush()
    return record, label


@router.post("/import/{resource}")
def import_campus_records(resource: str, payload: CampusImport, request: Request,
                          db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    if resource not in {"departments", "terms", "rooms", "subjects", "semesters", "sections", "teaching-assignments"}:
        raise HTTPException(status_code=404, detail="Bulk import is not enabled for this record type.")
    if resource in {"departments", "terms", "rooms"}:
        ensure_manager(user)
    created, errors = 0, []
    for index, row in enumerate(payload.rows, start=2):
        try:
            if not isinstance(row, dict):
                raise ValueError("Each CSV row must contain named columns.")
            with db.begin_nested():
                record, label = import_record(db, user, resource, row)
                audit(db, user, "imported", label, record.id)
            created += 1
        except HTTPException as exc:
            errors.append({"row": index, "message": exc.detail if isinstance(exc.detail, str) else exc.detail.get("message", "This row is outside your access scope.")})
        except ValidationError as exc:
            errors.append({"row": index, "message": "; ".join(f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in exc.errors())})
        except (ValueError, IntegrityError) as exc:
            errors.append({"row": index, "message": str(exc) if isinstance(exc, ValueError) else "A matching record already exists or a reference is invalid."})
    db.commit()
    return {"created_count": created, "error_count": len(errors), "errors": errors}


@router.get("/departments")
def list_departments(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = select(Department)
    if user.role == "super_admin":
        pass
    elif user.role == "hod":
        query = query.where(Department.id == user.department_id)
    else:
        query = query.where(Department.institution_id == user.institution_id)
    return [{"id": str(x.id), "name": x.name, "code": x.code, "institution_id": str(x.institution_id)} for x in db.scalars(query).all()]


@router.post("/departments", status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    ensure_manager(user)
    institution_id = payload.institution_id if user.role == "super_admin" else user.institution_id
    if not institution_id:
        raise HTTPException(status_code=422, detail="An institution is required.")
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")
    record = Department(institution_id=institution_id, name=payload.name.strip(), code=payload.code.strip().upper())
    db.add(record)
    db.flush()
    audit(db, user, "created", "department", record.id)
    db.commit()
    return {"id": str(record.id), "name": record.name, "code": record.code, "institution_id": str(record.institution_id)}


@router.get("/terms")
def list_terms(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = select(AcademicTerm)
    if user.role != "super_admin":
        query = query.where(AcademicTerm.institution_id == user.institution_id)
    return [{"id": str(x.id), "name": x.name, "academic_year": x.academic_year, "is_current": x.is_current,
             "institution_id": str(x.institution_id)} for x in db.scalars(query).all()]


@router.post("/terms", status_code=status.HTTP_201_CREATED)
def create_term(payload: TermCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    ensure_manager(user)
    institution_id = payload.institution_id if user.role == "super_admin" else user.institution_id
    if not institution_id:
        raise HTTPException(status_code=422, detail="Choose an institution before creating a term.")
    if not db.get(Institution, institution_id):
        raise HTTPException(status_code=404, detail="Institution not found.")
    if payload.is_current:
        db.query(AcademicTerm).filter(AcademicTerm.institution_id == institution_id).update({AcademicTerm.is_current: False})
    record = AcademicTerm(institution_id=institution_id, name=payload.name.strip(), academic_year=payload.academic_year.strip(), is_current=payload.is_current)
    db.add(record)
    db.flush()
    audit(db, user, "created", "academic_term", record.id)
    db.commit()
    return {"id": str(record.id), "name": record.name, "academic_year": record.academic_year, "is_current": record.is_current,
            "institution_id": str(record.institution_id)}


@router.get("/rooms")
def list_rooms(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = select(Room)
    if user.role != "super_admin":
        query = query.where(Room.institution_id == user.institution_id)
    return [{"id": str(x.id), "name": x.name, "capacity": x.capacity, "room_type": x.room_type,
             "institution_id": str(x.institution_id)} for x in db.scalars(query).all()]


@router.post("/rooms", status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    ensure_manager(user)
    institution_id = payload.institution_id if user.role == "super_admin" else user.institution_id
    if not institution_id:
        raise HTTPException(status_code=422, detail="Choose an institution before creating a room.")
    if not db.get(Institution, institution_id):
        raise HTTPException(status_code=404, detail="Institution not found.")
    record = Room(institution_id=institution_id, name=payload.name.strip(), capacity=payload.capacity, room_type=payload.room_type)
    db.add(record)
    db.flush()
    audit(db, user, "created", "room", record.id)
    db.commit()
    return {"id": str(record.id), "name": record.name, "capacity": record.capacity, "room_type": record.room_type,
            "institution_id": str(record.institution_id)}


@router.get("/subjects")
def list_subjects(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = select(Subject).join(Department)
    if user.role == "hod":
        query = query.where(Subject.department_id == user.department_id)
    elif user.role != "super_admin":
        query = query.where(Department.institution_id == user.institution_id)
    return [{"id": str(x.id), "code": x.code, "name": x.name, "department_id": str(x.department_id), "weekly_sessions": x.weekly_sessions, "room_type": x.room_type} for x in db.scalars(query).all()]


@router.post("/subjects", status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    department = department_or_404(db, payload.department_id)
    ensure_institution(user, department.institution_id)
    ensure_manager(user, department.id)
    record = Subject(department_id=department.id, code=payload.code.strip().upper(), name=payload.name.strip(),
                     weekly_sessions=payload.weekly_sessions, room_type=payload.room_type)
    db.add(record)
    db.flush()
    audit(db, user, "created", "subject", record.id)
    db.commit()
    return {"id": str(record.id), "code": record.code, "name": record.name, "department_id": str(record.department_id), "weekly_sessions": record.weekly_sessions, "room_type": record.room_type}


@router.get("/semesters")
def list_semesters(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = select(Semester).join(Department)
    if user.role == "hod":
        query = query.where(Semester.department_id == user.department_id)
    elif user.role != "super_admin":
        query = query.where(Department.institution_id == user.institution_id)
    return [{"id": str(x.id), "number": x.number, "department_id": str(x.department_id), "term_id": str(x.term_id)} for x in db.scalars(query).all()]


@router.post("/semesters", status_code=status.HTTP_201_CREATED)
def create_semester(payload: SemesterCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    department = department_or_404(db, payload.department_id)
    term = term_or_404(db, payload.term_id)
    ensure_institution(user, department.institution_id)
    if term.institution_id != department.institution_id:
        raise HTTPException(status_code=422, detail="Department and term must belong to the same institution.")
    ensure_manager(user, department.id)
    record = Semester(department_id=department.id, term_id=term.id, number=payload.number)
    db.add(record)
    db.flush()
    audit(db, user, "created", "semester", record.id)
    db.commit()
    return {"id": str(record.id), "number": record.number, "department_id": str(record.department_id), "term_id": str(record.term_id)}


@router.get("/sections")
def list_sections(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = select(Section, Semester, Department).join(Semester, Section.semester_id == Semester.id).join(Department, Semester.department_id == Department.id)
    if user.role == "hod":
        query = query.where(Semester.department_id == user.department_id)
    elif user.role != "super_admin":
        query = query.where(Department.institution_id == user.institution_id)
    return [{"id": str(section.id), "name": section.name, "strength": section.strength,
             "semester_id": str(section.semester_id), "semester_number": semester.number,
             "term_id": str(semester.term_id), "department_id": str(department.id)}
            for section, semester, department in db.execute(query).all()]


@router.post("/sections", status_code=status.HTTP_201_CREATED)
def create_section(payload: SectionCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    semester = db.get(Semester, payload.semester_id)
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found.")
    ensure_manager(user, semester.department_id)
    department = department_or_404(db, semester.department_id)
    ensure_institution(user, department.institution_id)
    record = Section(semester_id=semester.id, name=payload.name.strip(), strength=payload.strength)
    db.add(record)
    db.flush()
    audit(db, user, "created", "section", record.id)
    db.commit()
    return {"id": str(record.id), "name": record.name, "strength": record.strength, "semester_id": str(record.semester_id)}


@router.patch("/records/{resource}/{record_id}")
def update_campus_record(resource: str, record_id: UUID, payload: dict, request: Request,
                         db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    configurations = {
        "departments": (Department, DepartmentCreate, {"name", "code"}),
        "terms": (AcademicTerm, TermCreate, {"name", "academic_year", "is_current"}),
        "rooms": (Room, RoomCreate, {"name", "capacity", "room_type"}),
        "subjects": (Subject, SubjectCreate, {"code", "name", "weekly_sessions", "room_type"}),
        "semesters": (Semester, SemesterCreate, {"number"}),
        "sections": (Section, SectionCreate, {"name", "strength"}),
        "teaching-assignments": (TeachingAssignment, TeachingAssignmentCreate, {"sessions_per_week", "duration_periods"}),
    }
    if resource not in configurations:
        raise HTTPException(status_code=404, detail="This campus record type cannot be edited here.")
    model, schema, editable = configurations[resource]
    record = db.get(model, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Campus record not found.")
    if not isinstance(payload, dict) or not payload or set(payload) - editable:
        raise HTTPException(status_code=422, detail={"message": "Choose valid fields to update.", "allowed_fields": sorted(editable)})

    context = dict(payload)
    if resource == "departments":
        ensure_institution(user, record.institution_id); ensure_manager(user, record.id)
        context.update(institution_id=record.institution_id)
    elif resource == "terms":
        ensure_institution(user, record.institution_id); ensure_manager(user)
        context.update(institution_id=record.institution_id)
    elif resource == "rooms":
        ensure_institution(user, record.institution_id); ensure_manager(user)
        context.update(institution_id=record.institution_id)
    elif resource == "subjects":
        department = department_or_404(db, record.department_id)
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        context.update(department_id=record.department_id)
    elif resource == "semesters":
        department = department_or_404(db, record.department_id)
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        context.update(department_id=record.department_id, term_id=record.term_id)
    elif resource == "sections":
        semester = db.get(Semester, record.semester_id)
        department = department_or_404(db, semester.department_id)
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        context.update(semester_id=record.semester_id)
    else:
        subject = db.get(Subject, record.subject_id)
        section = db.get(Section, record.section_id)
        faculty = db.get(Faculty, record.faculty_id)
        semester = db.get(Semester, section.semester_id) if section else None
        if not subject or not section or not faculty or not semester or semester.department_id != subject.department_id or faculty.department_id != subject.department_id:
            raise HTTPException(status_code=409, detail="This teaching assignment no longer has a valid department relationship.")
        department = department_or_404(db, subject.department_id)
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        context.update(subject_id=record.subject_id, section_id=record.section_id, faculty_id=record.faculty_id)

    try:
        valid = schema.model_validate(context)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    for key in editable:
        if key in payload:
            setattr(record, key, getattr(valid, key))
    if resource == "terms" and record.is_current:
        db.query(AcademicTerm).filter(AcademicTerm.institution_id == record.institution_id,
                                      AcademicTerm.id != record.id).update({AcademicTerm.is_current: False})
    try:
        db.flush()
        audit(db, user, "updated", resource.replace("-", "_"), record.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This change conflicts with an existing campus record.")
    return {"id": str(record.id), "updated": sorted(payload)}


@router.delete("/records/{resource}/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campus_record(resource: str, record_id: UUID, request: Request,
                         db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    models = {"departments": Department, "terms": AcademicTerm, "rooms": Room,
              "subjects": Subject, "semesters": Semester, "sections": Section,
              "teaching-assignments": TeachingAssignment}
    if resource not in models:
        raise HTTPException(status_code=404, detail="This campus record type cannot be deleted here.")
    record = db.get(models[resource], record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Campus record not found.")
    references = 0
    if resource == "departments":
        ensure_institution(user, record.institution_id); ensure_manager(user, record.id)
        references = sum(db.scalar(select(func.count()).select_from(table).where(column == record.id)) or 0
                         for table, column in ((Faculty, Faculty.department_id), (Subject, Subject.department_id),
                                               (Semester, Semester.department_id), (User, User.department_id),
                                               (Timetable, Timetable.department_id)))
    elif resource == "terms":
        ensure_institution(user, record.institution_id); ensure_manager(user)
        references = (db.scalar(select(func.count()).select_from(Semester).where(Semester.term_id == record.id)) or 0) + (db.scalar(select(func.count()).select_from(Timetable).where(Timetable.term_id == record.id)) or 0)
    elif resource == "rooms":
        ensure_institution(user, record.institution_id); ensure_manager(user)
        references = db.scalar(select(func.count()).select_from(TimetableEntry).where(TimetableEntry.room_id == record.id)) or 0
    elif resource == "subjects":
        department = department_or_404(db, record.department_id)
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        references = (db.scalar(select(func.count()).select_from(TeachingAssignment).where(TeachingAssignment.subject_id == record.id)) or 0) + (db.scalar(select(func.count()).select_from(TimetableEntry).where(TimetableEntry.subject_id == record.id)) or 0)
    elif resource == "semesters":
        department = department_or_404(db, record.department_id)
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        references = db.scalar(select(func.count()).select_from(Section).where(Section.semester_id == record.id)) or 0
    elif resource == "sections":
        semester = db.get(Semester, record.semester_id)
        department = department_or_404(db, semester.department_id)
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        references = (db.scalar(select(func.count()).select_from(Student).where(Student.section_id == record.id)) or 0) + (db.scalar(select(func.count()).select_from(TeachingAssignment).where(TeachingAssignment.section_id == record.id)) or 0) + (db.scalar(select(func.count()).select_from(TimetableEntry).where(TimetableEntry.section_id == record.id)) or 0)
    else:
        subject = db.get(Subject, record.subject_id)
        department = department_or_404(db, subject.department_id)
        ensure_institution(user, department.institution_id); ensure_manager(user, department.id)
        references = db.scalar(select(func.count()).select_from(TimetableEntry).where(TimetableEntry.subject_id == record.subject_id, TimetableEntry.section_id == record.section_id, TimetableEntry.faculty_id == record.faculty_id)) or 0
    if references:
        raise HTTPException(status_code=409, detail="This record is in use. Remove or reassign its dependent campus records before deleting it.")
    audit(db, user, "deleted", resource.replace("-", "_"), record.id)
    db.delete(record)
    db.commit()


def create_invited_user(db: Session, background_tasks: BackgroundTasks, *, email: str, full_name: str,
                        role: Role, institution_id: UUID, department_id: UUID | None):
    email = email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(institution_id=institution_id, department_id=department_id, email=email,
                full_name=full_name.strip(), password_hash=hash_password(secrets.token_urlsafe(48)), role=role)
    db.add(user)
    db.flush()
    queue_password_link(db, background_tasks, user)
    return user


def manageable_invited_account(db: Session, user_id: UUID, actor: User) -> User:
    account = db.get(User, user_id)
    if not account or account.role not in (Role.faculty, Role.student, Role.hod):
        raise HTTPException(status_code=404, detail="Campus account not found.")
    if account.id == actor.id:
        raise HTTPException(status_code=409, detail="You cannot manage your own account from this screen.")
    if account.role == Role.faculty:
        faculty = db.scalar(select(Faculty).where(Faculty.user_id == account.id))
        if not faculty:
            raise HTTPException(status_code=404, detail="Campus account not found.")
        department = department_or_404(db, faculty.department_id)
    elif account.role == Role.student:
        student = db.scalar(select(Student).where(Student.user_id == account.id))
        section = db.get(Section, student.section_id) if student else None
        semester = db.get(Semester, section.semester_id) if section else None
        if not semester:
            raise HTTPException(status_code=404, detail="Campus account not found.")
        department = department_or_404(db, semester.department_id)
    else:
        if actor.role == Role.hod:
            raise HTTPException(status_code=403, detail="Only a college admin can manage department head accounts.")
        department = department_or_404(db, account.department_id) if account.department_id else None
        if not department:
            raise HTTPException(status_code=404, detail="Campus account not found.")
    ensure_institution(actor, department.institution_id)
    ensure_manager(actor, department.id)
    return account


@router.post("/people/accounts/{user_id}/resend-setup")
def resend_account_setup(user_id: UUID, background_tasks: BackgroundTasks, request: Request,
                         db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    account = manageable_invited_account(db, user_id, user)
    if not account.is_active:
        raise HTTPException(status_code=409, detail="Reactivate this account before sending a setup link.")
    queue_password_link(db, background_tasks, account)
    db.add(AuditEvent(institution_id=account.institution_id, actor_id=user.id, action="resent_setup_link",
                      resource_type="user_account", resource_id=str(account.id)))
    db.commit()
    return {"user_id": str(account.id), "sent": True}


@router.patch("/people/accounts/{user_id}/status")
def update_account_status(user_id: UUID, payload: AccountStatusUpdate, request: Request,
                          db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    account = manageable_invited_account(db, user_id, user)
    account.is_active = payload.is_active
    action = "activated" if payload.is_active else "deactivated"
    if not payload.is_active:
        db.query(RefreshSession).filter(RefreshSession.user_id == account.id,
                                        RefreshSession.revoked_at.is_(None)).update(
            {RefreshSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False)
    db.add(AuditEvent(institution_id=account.institution_id, actor_id=user.id, action=action,
                      resource_type="user_account", resource_id=str(account.id)))
    db.commit()
    return {"user_id": str(account.id), "is_active": account.is_active}


@router.get("/people/faculty")
def list_faculty(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = select(Faculty, User, Department).join(User, Faculty.user_id == User.id).join(Department, Faculty.department_id == Department.id)
    if user.role == "hod":
        query = query.where(Faculty.department_id == user.department_id)
    elif user.role != "super_admin":
        query = query.where(Department.institution_id == user.institution_id)
    return [{"id": str(f.id), "user_id": str(account.id), "full_name": account.full_name, "email": account.email,
             "is_active": account.is_active, "department_id": str(d.id), "department": d.name, "max_weekly_periods": f.max_weekly_periods}
            for f, account, d in db.execute(query).all()]


@router.patch("/people/faculty/{faculty_id}")
def update_faculty(faculty_id: UUID, payload: FacultyUpdate, request: Request,
                   db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    faculty = db.get(Faculty, faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty record not found.")
    current_department = department_or_404(db, faculty.department_id)
    ensure_institution(user, current_department.institution_id)
    ensure_manager(user, current_department.id)
    target_department = department_or_404(db, payload.department_id)
    ensure_institution(user, target_department.institution_id)
    ensure_manager(user, target_department.id)
    if target_department.institution_id != current_department.institution_id:
        raise HTTPException(status_code=422, detail="Faculty must remain in the same institution.")
    if target_department.id != current_department.id:
        references = (db.scalar(select(func.count()).select_from(TeachingAssignment).where(TeachingAssignment.faculty_id == faculty.id)) or 0) + (db.scalar(select(func.count()).select_from(TimetableEntry).where(TimetableEntry.faculty_id == faculty.id)) or 0)
        if references:
            raise HTTPException(status_code=409, detail="Reassign this faculty member's teaching assignments and timetable sessions before changing departments.")
    account = db.get(User, faculty.user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Faculty account not found.")
    full_name = payload.full_name.strip()
    if len(full_name) < 2:
        raise HTTPException(status_code=422, detail="Enter a name with at least two characters.")
    account.full_name = full_name
    account.department_id = target_department.id
    faculty.department_id = target_department.id
    faculty.max_weekly_periods = payload.max_weekly_periods
    audit(db, user, "updated", "faculty", faculty.id)
    db.commit()
    return {"id": str(faculty.id), "full_name": account.full_name, "email": account.email,
            "department_id": str(target_department.id), "department": target_department.name,
            "max_weekly_periods": faculty.max_weekly_periods, "is_active": account.is_active}


@router.post("/people/faculty", status_code=status.HTTP_201_CREATED)
def invite_faculty(payload: FacultyInvite, background_tasks: BackgroundTasks, request: Request,
                   db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    department = department_or_404(db, payload.department_id)
    ensure_institution(user, department.institution_id)
    ensure_manager(user, department.id)
    account = create_invited_user(db, background_tasks, email=payload.email, full_name=payload.full_name,
                                  role=Role.faculty, institution_id=department.institution_id, department_id=department.id)
    record = Faculty(user_id=account.id, department_id=department.id, max_weekly_periods=payload.max_weekly_periods)
    db.add(record)
    try:
        db.flush()
        audit(db, user, "invited", "faculty", record.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return {"id": str(record.id), "full_name": account.full_name, "email": account.email,
            "department_id": str(department.id), "department": department.name,
            "max_weekly_periods": record.max_weekly_periods, "invite_sent": True}


def visible_faculty(db: Session, faculty_id: UUID, user: User) -> Faculty:
    faculty = db.get(Faculty, faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty record not found.")
    department = department_or_404(db, faculty.department_id)
    ensure_institution(user, department.institution_id)
    if user.role == Role.faculty:
        if faculty.user_id != user.id:
            raise HTTPException(status_code=404, detail="Faculty record not found.")
    else:
        ensure_manager(user, department.id)
    return faculty


@router.get("/people/faculty/{faculty_id}/availability")
def get_faculty_availability(faculty_id: UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    faculty = visible_faculty(db, faculty_id, user)
    department = db.get(Department, faculty.department_id)
    institution = db.get(Institution, department.institution_id) if department else None
    period_labels = build_period_labels(institution.timetable_period_start, institution.timetable_period_minutes,
                                        maximum_period_count(institution.timetable_period_start,
                                                            institution.timetable_period_minutes)) if institution else build_period_labels("09:00", 60, 14)
    records = db.scalars(select(FacultyAvailability).where(FacultyAvailability.faculty_id == faculty.id,
                                                           FacultyAvailability.is_available.is_(False))).all()
    return {"faculty_id": str(faculty.id), "period_labels": period_labels,
            "unavailable": [{"day": item.day, "period": item.period} for item in records]}


@router.put("/people/faculty/{faculty_id}/availability")
def set_faculty_availability(faculty_id: UUID, payload: FacultyAvailabilityUpdate, request: Request,
                             db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    faculty = visible_faculty(db, faculty_id, user)
    slots = {(item.day, item.period) for item in payload.unavailable}
    if len(slots) != len(payload.unavailable):
        raise HTTPException(status_code=422, detail="Availability contains a duplicate day and period.")
    db.execute(delete(FacultyAvailability).where(FacultyAvailability.faculty_id == faculty.id))
    db.add_all([FacultyAvailability(faculty_id=faculty.id, day=day, period=period, is_available=False)
                for day, period in sorted(slots)])
    audit(db, user, "updated", "faculty_availability", faculty.id)
    db.commit()
    return {"faculty_id": str(faculty.id), "unavailable": [{"day": day, "period": period} for day, period in sorted(slots)]}


@router.get("/people/students")
def list_students(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = (select(Student, User, Section, Semester).join(User, Student.user_id == User.id)
             .join(Section, Student.section_id == Section.id)
             .join(Semester, Section.semester_id == Semester.id)
             .join(Department, Semester.department_id == Department.id))
    if user.role == "hod":
        query = query.where(Semester.department_id == user.department_id)
    elif user.role != "super_admin":
        query = query.where(User.institution_id == user.institution_id)
    return [{"id": str(student.id), "user_id": str(account.id), "is_active": account.is_active, "full_name": account.full_name, "email": account.email,
             "student_number": student.student_number, "section_id": str(section.id),
             "section": section.name, "semester": semester.number}
            for student, account, section, semester in db.execute(query).all()]


@router.patch("/people/students/{student_id}")
def update_student(student_id: UUID, payload: StudentUpdate, request: Request,
                   db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found.")
    account = db.get(User, student.user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Student account not found.")
    old_section = db.get(Section, student.section_id)
    old_semester = db.get(Semester, old_section.semester_id) if old_section else None
    current_department = department_or_404(db, old_semester.department_id) if old_semester else None
    if not current_department:
        raise HTTPException(status_code=404, detail="Student record not found.")
    ensure_institution(user, current_department.institution_id)
    ensure_manager(user, current_department.id)
    target_section = db.get(Section, payload.section_id)
    target_semester = db.get(Semester, target_section.semester_id) if target_section else None
    target_department = department_or_404(db, target_semester.department_id) if target_semester else None
    if not target_department:
        raise HTTPException(status_code=404, detail="Section not found.")
    ensure_institution(user, target_department.institution_id)
    ensure_manager(user, target_department.id)
    if target_department.institution_id != current_department.institution_id:
        raise HTTPException(status_code=422, detail="Student must remain in the same institution.")
    full_name = payload.full_name.strip()
    if len(full_name) < 2:
        raise HTTPException(status_code=422, detail="Enter a name with at least two characters.")
    student.student_number = payload.student_number.strip()
    student.section_id = target_section.id
    account.full_name = full_name
    account.department_id = target_department.id
    audit(db, user, "updated", "student", student.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That student number is already in use.")
    return {"id": str(student.id), "full_name": account.full_name, "email": account.email,
            "student_number": student.student_number, "section_id": str(target_section.id),
            "section": target_section.name, "is_active": account.is_active}


@router.post("/people/students", status_code=status.HTTP_201_CREATED)
def invite_student(payload: StudentInvite, background_tasks: BackgroundTasks, request: Request,
                   db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    section = db.get(Section, payload.section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")
    semester = db.get(Semester, section.semester_id)
    department = department_or_404(db, semester.department_id)
    ensure_institution(user, department.institution_id)
    ensure_manager(user, department.id)
    account = create_invited_user(db, background_tasks, email=payload.email, full_name=payload.full_name,
                                  role=Role.student, institution_id=department.institution_id, department_id=department.id)
    record = Student(user_id=account.id, section_id=section.id, student_number=payload.student_number.strip())
    db.add(record)
    try:
        db.flush()
        audit(db, user, "invited", "student", record.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This student number or email is already in use.")
    return {"id": str(record.id), "full_name": account.full_name, "email": account.email,
            "student_number": record.student_number, "section_id": str(section.id), "section": section.name,
            "invite_sent": True}


@router.get("/people/hods")
def list_hods(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user)
    query = select(User, Department).join(Department, User.department_id == Department.id).where(User.role == Role.hod)
    if user.role != Role.super_admin:
        query = query.where(User.institution_id == user.institution_id)
    return [{"id": str(account.id), "user_id": str(account.id), "is_active": account.is_active, "full_name": account.full_name, "email": account.email,
             "department_id": str(department.id), "department": department.name}
            for account, department in db.execute(query).all()]


@router.patch("/people/hods/{user_id}")
def update_hod(user_id: UUID, payload: HodUpdate, request: Request,
               db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    if user.role == Role.hod:
        raise HTTPException(status_code=403, detail="Only a college admin can update department head accounts.")
    account = db.get(User, user_id)
    if not account or account.role != Role.hod:
        raise HTTPException(status_code=404, detail="Department head account not found.")
    current_department = department_or_404(db, account.department_id) if account.department_id else None
    if not current_department:
        raise HTTPException(status_code=404, detail="Department head account not found.")
    ensure_institution(user, current_department.institution_id)
    ensure_manager(user)
    target_department = department_or_404(db, payload.department_id)
    ensure_institution(user, target_department.institution_id)
    if target_department.institution_id != current_department.institution_id:
        raise HTTPException(status_code=422, detail="Department head must remain in the same institution.")
    full_name = payload.full_name.strip()
    if len(full_name) < 2:
        raise HTTPException(status_code=422, detail="Enter a name with at least two characters.")
    account.full_name = full_name
    account.department_id = target_department.id
    audit(db, user, "updated", "hod", account.id)
    db.commit()
    return {"id": str(account.id), "full_name": account.full_name, "email": account.email,
            "department_id": str(target_department.id), "department": target_department.name,
            "is_active": account.is_active}


@router.post("/people/hods", status_code=status.HTTP_201_CREATED)
def invite_hod(payload: HodInvite, background_tasks: BackgroundTasks, request: Request,
               db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    ensure_manager(user)
    department = department_or_404(db, payload.department_id)
    ensure_institution(user, department.institution_id)
    account = create_invited_user(db, background_tasks, email=payload.email, full_name=payload.full_name,
                                  role=Role.hod, institution_id=department.institution_id, department_id=department.id)
    audit(db, user, "invited", "hod", account.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return {"id": str(account.id), "full_name": account.full_name, "email": account.email,
            "department_id": str(department.id), "department": department.name, "invite_sent": True}


@router.get("/teaching-assignments")
def list_teaching_assignments(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = (select(TeachingAssignment, Subject, Section, Semester, Faculty, User)
             .join(Subject, TeachingAssignment.subject_id == Subject.id)
             .join(Section, TeachingAssignment.section_id == Section.id)
             .join(Semester, Section.semester_id == Semester.id)
             .join(Faculty, TeachingAssignment.faculty_id == Faculty.id)
             .join(User, Faculty.user_id == User.id)
             .join(Department, Subject.department_id == Department.id))
    if user.role == Role.hod:
        query = query.where(Department.id == user.department_id)
    elif user.role != Role.super_admin:
        query = query.where(Department.institution_id == user.institution_id)
    return [{"id": str(assignment.id), "subject_id": str(subject.id), "subject": subject.name,
             "section_id": str(section.id), "section": section.name, "faculty_id": str(faculty.id),
             "faculty": account.full_name, "sessions_per_week": assignment.sessions_per_week,
             "duration_periods": assignment.duration_periods}
            for assignment, subject, section, semester, faculty, account in db.execute(query).all()]


@router.post("/teaching-assignments", status_code=status.HTTP_201_CREATED)
def create_teaching_assignment(payload: TeachingAssignmentCreate, request: Request, db: Session = Depends(get_db),
                               user: User = Depends(current_user)):
    ensure_browser_origin(request)
    subject = db.get(Subject, payload.subject_id)
    section = db.get(Section, payload.section_id)
    faculty = db.get(Faculty, payload.faculty_id)
    if not subject or not section or not faculty:
        raise HTTPException(status_code=404, detail="Choose an existing subject, section, and faculty member.")
    semester = db.get(Semester, section.semester_id)
    department = department_or_404(db, subject.department_id)
    if semester.department_id != department.id or faculty.department_id != department.id:
        raise HTTPException(status_code=422, detail="Subject, section, and faculty must belong to the same department.")
    ensure_institution(user, department.institution_id)
    ensure_manager(user, department.id)
    record = TeachingAssignment(subject_id=subject.id, section_id=section.id, faculty_id=faculty.id,
                                sessions_per_week=payload.sessions_per_week, duration_periods=payload.duration_periods)
    db.add(record)
    db.flush()
    audit(db, user, "created", "teaching_assignment", record.id)
    db.commit()
    faculty_user = db.get(User, faculty.user_id)
    return {"id": str(record.id), "subject_id": str(subject.id), "subject": subject.name,
            "section_id": str(section.id), "section": section.name, "faculty_id": str(faculty.id),
            "faculty": faculty_user.full_name if faculty_user else "Faculty",
            "sessions_per_week": record.sessions_per_week, "duration_periods": record.duration_periods}


@router.post("/timetables/generate", status_code=status.HTTP_201_CREATED)
def generate_stored_timetable(payload: StoredTimetableGenerateRequest, request: Request, db: Session = Depends(get_db),
                              user: User = Depends(current_user)):
    ensure_browser_origin(request)
    ensure_manager(user, payload.department_id)
    department = department_or_404(db, payload.department_id)
    term = term_or_404(db, payload.term_id)
    ensure_institution(user, department.institution_id)
    if term.institution_id != department.institution_id:
        raise HTTPException(status_code=422, detail="The academic term and department must belong to the same institution.")
    institution = db.get(Institution, department.institution_id)
    try:
        period_labels = build_period_labels(institution.timetable_period_start,
                                            institution.timetable_period_minutes, payload.periods_per_day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    weekdays = payload.weekdays or list(range(payload.days))
    schedule_day_for_weekday = {weekday: index for index, weekday in enumerate(weekdays)}

    query = (select(TeachingAssignment, Subject, Section, Semester, Faculty, User)
             .join(Subject, TeachingAssignment.subject_id == Subject.id)
             .join(Section, TeachingAssignment.section_id == Section.id)
             .join(Semester, Section.semester_id == Semester.id)
             .join(Faculty, TeachingAssignment.faculty_id == Faculty.id)
             .join(User, Faculty.user_id == User.id)
             .where(Semester.term_id == term.id, Semester.department_id == department.id))
    if payload.section_id:
        query = query.where(Section.id == payload.section_id)
    assignments = db.execute(query).all()
    if not assignments:
        raise HTTPException(status_code=422, detail="Add teaching assignments for this term before generating a timetable.")

    rooms = db.scalars(select(Room).where(Room.institution_id == department.institution_id)).all()
    if not rooms:
        raise HTTPException(status_code=422, detail="Add at least one classroom or lab before generating a timetable.")
    faculty_ids = {faculty.id for _, _, _, _, faculty, _ in assignments}
    unavailable_by_faculty: dict[UUID, list[tuple[int, int]]] = {faculty_id: [] for faculty_id in faculty_ids}
    availability = db.scalars(select(FacultyAvailability).where(
        FacultyAvailability.faculty_id.in_(faculty_ids), FacultyAvailability.is_available.is_(False))).all()
    for slot in availability:
        schedule_day = schedule_day_for_weekday.get(slot.day)
        if schedule_day is not None:
            unavailable_by_faculty.setdefault(slot.faculty_id, []).append((schedule_day, slot.period))

    break_slots = calendar_break_slots(weekdays, period_labels, institution.timetable_period_minutes,
                                        institution.timetable_breaks or [])
    sessions = []
    assignment_by_session: dict[str, tuple] = {}
    for assignment, subject, section, semester, faculty, account in assignments:
        for occurrence in range(assignment.sessions_per_week):
            key = f"{assignment.id}:{occurrence}"
            sessions.append({"session_key": key, "subject": subject.name, "faculty": str(faculty.id),
                             "section": str(section.id), "course_key": f"{subject.id}:{section.id}", "students": section.strength,
                             "room_type": subject.room_type, "duration_periods": assignment.duration_periods,
                             "faculty_max_weekly_periods": faculty.max_weekly_periods,
                             "unavailable": unavailable_by_faculty.get(faculty.id, [])})
            assignment_by_session[key] = (subject, section, faculty, account)
    solver_input = {"sessions": sessions,
                    "rooms": [{"id": str(room.id), "name": room.name, "capacity": room.capacity, "room_type": room.room_type} for room in rooms],
                    "days": len(weekdays), "periods_per_day": payload.periods_per_day,
                    "global_blocked_slots": sorted(break_slots)}
    try:
        solved = generate_schedule(solver_input, with_metadata=True)
    except ScheduleInfeasible as exc:
        db.add(GenerationRun(requested_by=user.id, status="infeasible",
                             diagnostics={"message": str(exc), "details": exc.diagnostics,
                                          "department_id": str(department.id), "term_id": str(term.id)}))
        db.commit()
        raise HTTPException(status_code=422, detail={"message": str(exc), "conflicts": [],
                                                    "diagnostics": exc.diagnostics})

    previous = db.scalar(select(Timetable).where(Timetable.institution_id == department.institution_id,
                                                 Timetable.term_id == term.id, Timetable.department_id == department.id)
                         .order_by(Timetable.version.desc()).limit(1))
    timetable = Timetable(institution_id=department.institution_id, department_id=department.id, term_id=term.id,
                          previous_version_id=previous.id if previous else None, created_by=user.id,
                          name=payload.name.strip(), status="draft", version=(previous.version + 1 if previous else 1),
                          days=len(weekdays), weekdays=weekdays, periods_per_day=payload.periods_per_day,
                          period_minutes=institution.timetable_period_minutes, period_labels=period_labels)
    db.add(timetable)
    db.flush()
    output_entries = []
    for solved_entry in solved["entries"]:
        subject, section, faculty, account = assignment_by_session[solved_entry["session_key"]]
        entry = TimetableEntry(timetable_id=timetable.id, section_id=section.id, subject_id=subject.id,
                               faculty_id=faculty.id, room_id=UUID(solved_entry["room_id"]),
                               day=solved_entry["day"], start_period=solved_entry["period"],
                               duration_periods=solved_entry["duration_periods"])
        db.add(entry)
        db.flush()
        output_entries.append({"id": str(entry.id), "subject": subject.name, "subject_id": str(subject.id),
                               "faculty": account.full_name, "faculty_id": str(faculty.id),
                               "section": section.name, "section_id": str(section.id),
                               "room": solved_entry["room"], "room_id": solved_entry["room_id"],
                               "day": solved_entry["day"], "period": solved_entry["period"],
                               "duration_periods": solved_entry["duration_periods"]})
    run = GenerationRun(timetable_id=timetable.id, requested_by=user.id, status=solved["status"],
                        score=solved["score"], diagnostics={"entry_count": len(output_entries)})
    db.add(run)
    audit(db, user, "generated", "timetable", timetable.id)
    db.commit()
    return {"id": str(timetable.id), "name": timetable.name, "status": timetable.status,
            "version": timetable.version, "previous_version_id": str(timetable.previous_version_id) if timetable.previous_version_id else None,
            "score": solved["score"], "days": timetable.days, "weekdays": timetable.weekdays,
            "period_labels": timetable.period_labels,
            "periods_per_day": timetable.periods_per_day, "entries": output_entries}


@router.get("/timetables")
def list_timetables(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_manager(user, user.department_id)
    query = select(Timetable).order_by(Timetable.created_at.desc())
    if user.role == Role.hod:
        query = query.where(Timetable.department_id == user.department_id)
    elif user.role != Role.super_admin:
        query = query.where(Timetable.institution_id == user.institution_id)
    return [{"id": str(item.id), "name": item.name, "status": item.status,
             "approval_status": item.approval_status, "approval_note": item.approval_note,
             "version": item.version,
             "term_id": str(item.term_id), "department_id": str(item.department_id),
             "days": item.days, "weekdays": item.weekdays or list(range(item.days)),
             "periods_per_day": item.periods_per_day,
             "period_labels": item.period_labels or build_period_labels("09:00", 60, item.periods_per_day),
             "created_at": item.created_at}
            for item in db.scalars(query).all()]


@router.get("/timetables/approvals")
def pending_timetable_approvals(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role not in (Role.super_admin, Role.college_admin):
        raise HTTPException(status_code=403, detail="Only a college admin can review timetable approvals.")
    query = (select(Timetable, Department.name, AcademicTerm.name, User.full_name)
             .join(Department, Timetable.department_id == Department.id)
             .join(AcademicTerm, Timetable.term_id == AcademicTerm.id)
             .outerjoin(User, Timetable.approval_requested_by == User.id)
             .where(Timetable.status == "draft", Timetable.approval_status == "pending")
             .order_by(Timetable.approval_requested_at.asc()))
    if user.role != Role.super_admin:
        query = query.where(Timetable.institution_id == user.institution_id)
    return [{"id": str(item.id), "name": item.name, "version": item.version,
             "term_id": str(item.term_id), "term": term_name,
             "department_id": str(item.department_id), "department": department_name,
             "requested_by": str(item.approval_requested_by) if item.approval_requested_by else None,
             "requested_by_name": requester or "Former account",
             "requested_at": item.approval_requested_at, "approval_note": item.approval_note}
            for item, department_name, term_name, requester in db.execute(query).all()]


@router.get("/timetables/{timetable_id}/entries")
def get_timetable_entries(timetable_id: UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    timetable = db.get(Timetable, timetable_id)
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    ensure_institution(user, timetable.institution_id)
    ensure_manager(user, timetable.department_id)
    query = (select(TimetableEntry, Subject, Section, Faculty, User, Room)
             .join(Subject, TimetableEntry.subject_id == Subject.id)
             .join(Section, TimetableEntry.section_id == Section.id)
             .join(Faculty, TimetableEntry.faculty_id == Faculty.id)
             .join(User, Faculty.user_id == User.id)
             .join(Room, TimetableEntry.room_id == Room.id)
             .where(TimetableEntry.timetable_id == timetable.id)
             .order_by(TimetableEntry.day, TimetableEntry.start_period))
    return [{"id": str(entry.id), "subject": subject.name, "section": section.name, "section_id": str(section.id),
             "faculty": account.full_name, "room": room.name, "room_id": str(room.id), "day": entry.day,
             "period": entry.start_period, "duration_periods": entry.duration_periods, "is_locked": entry.is_locked}
            for entry, subject, section, faculty, account, room in db.execute(query).all()]


def timetable_or_404(db: Session, timetable_id: UUID, user: User, lock: bool = False) -> Timetable:
    query = select(Timetable).where(Timetable.id == timetable_id)
    if lock:
        query = query.with_for_update()
    timetable = db.scalar(query)
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    ensure_institution(user, timetable.institution_id)
    ensure_manager(user, timetable.department_id)
    return timetable


def timetable_conflicts(db: Session, timetable_id: UUID):
    timetable = db.get(Timetable, timetable_id)
    if not timetable:
        return []
    entries = db.scalars(select(TimetableEntry).where(TimetableEntry.timetable_id == timetable_id)).all()
    conflicts = []
    weekdays = timetable.weekdays or list(range(timetable.days))

    def calendar_weekday(day_index):
        return weekdays[day_index] if 0 <= day_index < len(weekdays) else day_index
    section_ids = {entry.section_id for entry in entries}
    subject_ids = {entry.subject_id for entry in entries}
    room_ids = {entry.room_id for entry in entries}
    faculty_ids = {entry.faculty_id for entry in entries}
    sections = {item.id: item for item in db.scalars(select(Section).where(Section.id.in_(section_ids))).all()} if section_ids else {}
    subjects = {item.id: item for item in db.scalars(select(Subject).where(Subject.id.in_(subject_ids))).all()} if subject_ids else {}
    rooms = {item.id: item for item in db.scalars(select(Room).where(Room.id.in_(room_ids))).all()} if room_ids else {}
    institution = db.get(Institution, timetable.institution_id)
    institution_break_slots = calendar_break_slots(
        weekdays, timetable.period_labels or build_period_labels(institution.timetable_period_start,
            institution.timetable_period_minutes, timetable.periods_per_day),
        timetable.period_minutes, institution.timetable_breaks or []) if institution else set()
    unavailable = {(item.faculty_id, item.day, item.period) for item in db.scalars(select(FacultyAvailability).where(
        FacultyAvailability.faculty_id.in_(faculty_ids), FacultyAvailability.is_available.is_(False))).all()} if faculty_ids else set()

    def report(entry, category, reason, periods=None):
        item = {"entry_ids": [str(entry.id)], "category": category, "day": entry.day,
                "weekday": calendar_weekday(entry.day),
                "periods": periods or [entry.start_period + 1, entry.start_period + entry.duration_periods],
                "reason": reason}
        conflicts.append(item)

    for entry in entries:
        if entry.day < 0 or entry.day >= timetable.days or entry.start_period < 0 or entry.duration_periods < 1 or entry.start_period + entry.duration_periods > timetable.periods_per_day:
            report(entry, "schedule_bounds", "This session falls outside the timetable's configured days or periods.")
        section = sections.get(entry.section_id)
        subject = subjects.get(entry.subject_id)
        room = rooms.get(entry.room_id)
        if section and subject and room and (room.capacity < section.strength or room.room_type != subject.room_type):
            report(entry, "room_eligibility", f"{room.name} does not meet the section capacity or {subject.room_type} room requirement.")
        blocked = sorted(period for faculty_id, day, period in unavailable
                         if faculty_id == entry.faculty_id and day == calendar_weekday(entry.day)
                         and entry.start_period <= period < entry.start_period + entry.duration_periods)
        if blocked:
            report(entry, "faculty_availability", "The faculty member is unavailable during this session.",
                   [blocked[0] + 1, blocked[-1] + 1])
        blocked_by_break = sorted(period for day, period in institution_break_slots
                                  if day == entry.day and entry.start_period <= period < entry.start_period + entry.duration_periods)
        if blocked_by_break:
            report(entry, "institution_break", "This session overlaps a campus-wide scheduled break.",
                   [blocked_by_break[0] + 1, blocked_by_break[-1] + 1])

    for index, first in enumerate(entries):
        for second in entries[index + 1:]:
            if first.day != second.day:
                continue
            overlaps = (first.start_period < second.start_period + second.duration_periods and
                        second.start_period < first.start_period + first.duration_periods)
            if overlaps:
                overlap_start = max(first.start_period, second.start_period)
                overlap_end = min(first.start_period + first.duration_periods, second.start_period + second.duration_periods)
                periods = [overlap_start + 1, overlap_end]
                shared_resources = ((first.section_id == second.section_id, "section_overlap", "The same section is scheduled twice."),
                                    (first.faculty_id == second.faculty_id, "faculty_overlap", "The same faculty member is scheduled twice."),
                                    (first.room_id == second.room_id, "room_overlap", "The same room is scheduled twice."))
                for shared, category, reason in shared_resources:
                    if shared:
                        conflicts.append({"entry_ids": [str(first.id), str(second.id)], "category": category,
                                          "day": first.day, "weekday": calendar_weekday(first.day),
                                          "periods": periods, "reason": reason})
    return conflicts


def publish_timetable_record(db: Session, timetable: Timetable, user: User):
    db.query(Timetable).filter(Timetable.institution_id == timetable.institution_id,
                               Timetable.term_id == timetable.term_id,
                               Timetable.department_id == timetable.department_id,
                               Timetable.status == "published",
                               Timetable.id != timetable.id).update({Timetable.status: "archived"})
    timetable.status = "published"
    entries = db.scalars(select(TimetableEntry).where(TimetableEntry.timetable_id == timetable.id)).all()
    faculty_ids = {entry.faculty_id for entry in entries}
    section_ids = {entry.section_id for entry in entries}
    recipients = set(db.scalars(select(Faculty.user_id).where(Faculty.id.in_(faculty_ids))).all()) if faculty_ids else set()
    if section_ids:
        recipients.update(db.scalars(select(Student.user_id).where(Student.section_id.in_(section_ids))).all())
    for recipient_id in recipients:
        notify_user(db, recipient_id, "schedule_updates", "New timetable published",
                    f"{timetable.name} · version {timetable.version} is now available in your schedule.")
    audit(db, user, "published", "timetable", timetable.id)


@router.post("/timetables/{timetable_id}/request-approval")
def request_timetable_approval(timetable_id: UUID, request: Request,
                               db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    if user.role != Role.hod:
        raise HTTPException(status_code=403, detail="Only a department head can submit a timetable for approval.")
    timetable = timetable_or_404(db, timetable_id, user, lock=True)
    if timetable.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft timetable can be submitted for approval.")
    if timetable.approval_status == "pending":
        raise HTTPException(status_code=409, detail="This timetable is already waiting for approval.")
    if not db.scalar(select(func.count()).select_from(TimetableEntry).where(TimetableEntry.timetable_id == timetable.id)):
        raise HTTPException(status_code=422, detail="Add scheduled sessions before requesting approval.")
    conflicts = timetable_conflicts(db, timetable.id)
    if conflicts:
        raise HTTPException(status_code=409, detail={"message": "Resolve all timetable conflicts before requesting approval.", "conflicts": conflicts})
    now = datetime.now(timezone.utc)
    timetable.approval_status = "pending"
    timetable.approval_requested_by = user.id
    timetable.approval_requested_at = now
    timetable.approval_reviewed_by = None
    timetable.approval_reviewed_at = None
    timetable.approval_note = None
    admin_ids = db.scalars(select(User.id).where(
        User.is_active.is_(True),
        or_((User.role == Role.college_admin) & (User.institution_id == timetable.institution_id),
            User.role == Role.super_admin),
    )).all()
    for admin_id in admin_ids:
        notify_user(db, admin_id, "approval_updates", "Timetable approval requested",
                    f"{timetable.name} · version {timetable.version} is ready for review.")
    audit(db, user, "approval_requested", "timetable", timetable.id)
    db.commit()
    return {"id": str(timetable.id), "approval_status": timetable.approval_status,
            "approval_requested_at": timetable.approval_requested_at}


@router.get("/timetables/{timetable_id}/conflicts")
def get_timetable_conflicts(timetable_id: UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    timetable = timetable_or_404(db, timetable_id, user)
    conflicts = timetable_conflicts(db, timetable.id)
    return {"timetable_id": str(timetable.id), "conflict_count": len(conflicts), "conflicts": conflicts}


@router.post("/timetables/{timetable_id}/repair")
def repair_timetable(timetable_id: UUID, request: Request, db: Session = Depends(get_db),
                     user: User = Depends(current_user)):
    ensure_browser_origin(request)
    timetable = timetable_or_404(db, timetable_id, user, lock=True)
    if timetable.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft timetables can be repaired.")
    if timetable.approval_status == "pending":
        raise HTTPException(status_code=409, detail="This timetable is locked while it is waiting for approval.")

    current_conflicts = timetable_conflicts(db, timetable.id)
    if not current_conflicts:
        return {"moved_count": 0, "conflicts": [], "entries": get_timetable_entries(timetable.id, db, user)}

    rows = db.execute(select(TimetableEntry, Subject, Section, Faculty, User)
                      .join(Subject, TimetableEntry.subject_id == Subject.id)
                      .join(Section, TimetableEntry.section_id == Section.id)
                      .join(Faculty, TimetableEntry.faculty_id == Faculty.id)
                      .join(User, Faculty.user_id == User.id)
                      .where(TimetableEntry.timetable_id == timetable.id)).all()
    if not rows:
        raise HTTPException(status_code=422, detail="Add scheduled sessions before requesting a repair.")

    entries = {str(entry.id): entry for entry, _, _, _, _ in rows}
    faculty_ids = {faculty.id for _, _, _, faculty, _ in rows}
    availability = db.scalars(select(FacultyAvailability).where(
        FacultyAvailability.faculty_id.in_(faculty_ids), FacultyAvailability.is_available.is_(False))).all()
    weekdays = timetable.weekdays or list(range(timetable.days))
    schedule_day_for_weekday = {weekday: index for index, weekday in enumerate(weekdays)}
    unavailable_by_faculty: dict[UUID, list[tuple[int, int]]] = {faculty_id: [] for faculty_id in faculty_ids}
    for slot in availability:
        schedule_day = schedule_day_for_weekday.get(slot.day)
        if schedule_day is not None:
            unavailable_by_faculty.setdefault(slot.faculty_id, []).append((schedule_day, slot.period))
    institution = db.get(Institution, timetable.institution_id)
    institution_break_slots = calendar_break_slots(
        weekdays, timetable.period_labels or build_period_labels(institution.timetable_period_start,
            institution.timetable_period_minutes, timetable.periods_per_day),
        timetable.period_minutes, institution.timetable_breaks or []) if institution else set()

    rooms = db.scalars(select(Room).where(Room.institution_id == timetable.institution_id)).all()
    sessions = []
    for entry, subject, section, faculty, _ in rows:
        sessions.append({
            "session_key": str(entry.id), "subject": subject.name, "faculty": str(faculty.id),
            "section": str(section.id), "course_key": f"{subject.id}:{section.id}",
            "students": section.strength, "room_type": subject.room_type,
            "duration_periods": entry.duration_periods,
            "faculty_max_weekly_periods": faculty.max_weekly_periods,
            "unavailable": unavailable_by_faculty.get(faculty.id, []),
            "preferred_location": {"day": entry.day, "period": entry.start_period, "room_id": str(entry.room_id)},
            "fixed": entry.is_locked,
        })
    solver_input = {
        "sessions": sessions,
        "rooms": [{"id": str(room.id), "name": room.name, "capacity": room.capacity, "room_type": room.room_type}
                  for room in rooms],
        "days": timetable.days, "periods_per_day": timetable.periods_per_day,
        "global_blocked_slots": sorted(institution_break_slots),
    }
    try:
        solved = generate_schedule(solver_input, with_metadata=True)
    except ScheduleInfeasible as exc:
        db.add(GenerationRun(timetable_id=timetable.id, requested_by=user.id, status="infeasible",
                             diagnostics={"repair": True, "message": str(exc), "details": exc.diagnostics}))
        db.commit()
        raise HTTPException(status_code=422, detail={"message": str(exc), "conflicts": current_conflicts,
                                                    "diagnostics": exc.diagnostics})

    moved_count = 0
    for solved_entry in solved["entries"]:
        entry = entries[solved_entry["session_key"]]
        room_id = UUID(solved_entry["room_id"])
        if (entry.day, entry.start_period, entry.room_id) != (solved_entry["day"], solved_entry["period"], room_id):
            moved_count += 1
            entry.day = solved_entry["day"]
            entry.start_period = solved_entry["period"]
            entry.room_id = room_id
    db.flush()
    remaining_conflicts = timetable_conflicts(db, timetable.id)
    if remaining_conflicts:
        db.rollback()
        raise HTTPException(status_code=409, detail={"message": "The proposed repair did not clear every timetable issue.",
                                                    "conflicts": remaining_conflicts})
    db.add(GenerationRun(timetable_id=timetable.id, requested_by=user.id, status=solved["status"],
                         score=solved["score"], diagnostics={"repair": True, "moved_count": moved_count}))
    audit(db, user, "repaired", "timetable", timetable.id)
    db.commit()
    return {"moved_count": moved_count, "conflicts": [], "entries": get_timetable_entries(timetable.id, db, user)}


@router.get("/timetables/{timetable_id}/entries/{entry_id}/suggestions")
def suggest_timetable_entry_slots(timetable_id: UUID, entry_id: UUID, db: Session = Depends(get_db),
                                  user: User = Depends(current_user)):
    timetable = timetable_or_404(db, timetable_id, user)
    if timetable.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft sessions can be rescheduled.")
    if timetable.approval_status == "pending":
        raise HTTPException(status_code=409, detail="This timetable is locked while it is waiting for approval.")
    entry = db.get(TimetableEntry, entry_id)
    if not entry or entry.timetable_id != timetable.id:
        raise HTTPException(status_code=404, detail="Timetable entry not found.")
    if entry.is_locked:
        raise HTTPException(status_code=409, detail="This session is locked and cannot be rescheduled.")

    subject = db.get(Subject, entry.subject_id)
    section = db.get(Section, entry.section_id)
    if not subject or not section:
        raise HTTPException(status_code=409, detail="This session no longer has valid course or section details.")
    rooms = db.scalars(select(Room).where(Room.institution_id == timetable.institution_id,
                                         Room.capacity >= section.strength,
                                         Room.room_type == subject.room_type)).all()
    existing = db.scalars(select(TimetableEntry).where(TimetableEntry.timetable_id == timetable.id,
                                                        TimetableEntry.id != entry.id)).all()
    unavailable = {(slot.day, slot.period) for slot in db.scalars(select(FacultyAvailability).where(
        FacultyAvailability.faculty_id == entry.faculty_id, FacultyAvailability.is_available.is_(False))).all()}
    weekdays = timetable.weekdays or list(range(timetable.days))
    institution = db.get(Institution, timetable.institution_id)
    institution_break_slots = calendar_break_slots(
        weekdays, timetable.period_labels or build_period_labels(institution.timetable_period_start,
            institution.timetable_period_minutes, timetable.periods_per_day),
        timetable.period_minutes, institution.timetable_breaks or []) if institution else set()
    section_load = {}
    for item in existing:
        if item.section_id == entry.section_id:
            section_load[item.day] = section_load.get(item.day, 0) + item.duration_periods

    suggestions = []
    for day in range(timetable.days):
        calendar_day = weekdays[day]
        for period in range(timetable.periods_per_day - entry.duration_periods + 1):
            if any((calendar_day, period + offset) in unavailable for offset in range(entry.duration_periods)):
                continue
            if any((day, period + offset) in institution_break_slots for offset in range(entry.duration_periods)):
                continue
            resource_overlaps = [item for item in existing if item.day == day and
                                 period < item.start_period + item.duration_periods and
                                 item.start_period < period + entry.duration_periods and
                                 (item.section_id == entry.section_id or item.faculty_id == entry.faculty_id)]
            if resource_overlaps:
                continue
            for room in rooms:
                if day == entry.day and period == entry.start_period and room.id == entry.room_id:
                    continue
                room_overlap = any(item.day == day and item.room_id == room.id and
                                   period < item.start_period + item.duration_periods and
                                   item.start_period < period + entry.duration_periods for item in existing)
                if room_overlap:
                    continue
                room_change = room.id != entry.room_id
                suggestions.append({"day": day, "period": period, "room_id": str(room.id), "room": room.name,
                                    "score": section_load.get(day, 0) * 10 + period + (5 if room_change else 0),
                                    "reason": "Clear of faculty, section, room, availability, and campus-break conflicts."})
    suggestions.sort(key=lambda item: (item["score"], item["day"], item["period"]))
    return {"entry_id": str(entry.id), "duration_periods": entry.duration_periods,
            "suggestions": suggestions[:8], "total_available_slots": len(suggestions)}


@router.patch("/timetables/{timetable_id}/entries/{entry_id}")
def move_timetable_entry(timetable_id: UUID, entry_id: UUID, payload: TimetableEntryMove, request: Request,
                         db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    timetable = timetable_or_404(db, timetable_id, user, lock=True)
    if timetable.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft timetables can be edited.")
    if timetable.approval_status == "pending":
        raise HTTPException(status_code=409, detail="This timetable is locked while it is waiting for approval.")
    entry = db.get(TimetableEntry, entry_id)
    if not entry or entry.timetable_id != timetable.id:
        raise HTTPException(status_code=404, detail="Timetable entry not found.")
    if entry.is_locked:
        raise HTTPException(status_code=409, detail="This session is locked and cannot be moved.")
    if payload.day >= timetable.days:
        raise HTTPException(status_code=422, detail="Choose a day within this timetable's schedule.")
    if payload.period + entry.duration_periods > timetable.periods_per_day:
        raise HTTPException(status_code=422, detail="This session would extend beyond the last period.")
    weekdays = timetable.weekdays or list(range(timetable.days))
    calendar_day = weekdays[payload.day]
    blocked_slots = set(db.execute(select(FacultyAvailability.day, FacultyAvailability.period).where(
        FacultyAvailability.faculty_id == entry.faculty_id,
        FacultyAvailability.is_available.is_(False),
        FacultyAvailability.day == calendar_day,
        FacultyAvailability.period >= payload.period,
        FacultyAvailability.period < payload.period + entry.duration_periods,
    )).all())
    if blocked_slots:
        raise HTTPException(status_code=409, detail="This faculty member is unavailable during that session.")
    institution = db.get(Institution, timetable.institution_id)
    campus_break_slots = calendar_break_slots(
        weekdays, timetable.period_labels or build_period_labels(institution.timetable_period_start,
            institution.timetable_period_minutes, timetable.periods_per_day),
        timetable.period_minutes, institution.timetable_breaks or []) if institution else set()
    if any((payload.day, payload.period + offset) in campus_break_slots
           for offset in range(entry.duration_periods)):
        raise HTTPException(status_code=409, detail="This session overlaps a campus-wide scheduled break.")
    previous_conflicts = timetable_conflicts(db, timetable.id)
    previous_signatures = {(tuple(item.get("entry_ids", [])), item.get("category"), item.get("day"),
                            tuple(item.get("periods", [])), item.get("reason")) for item in previous_conflicts}
    previous_day, previous_period, previous_room = entry.day, entry.start_period, entry.room_id
    if payload.room_id:
        room = db.get(Room, payload.room_id)
        subject = db.get(Subject, entry.subject_id)
        section = db.get(Section, entry.section_id)
        if not room or room.institution_id != timetable.institution_id:
            raise HTTPException(status_code=404, detail="Room not found in this institution.")
        if not subject or not section or room.capacity < section.strength or room.room_type != subject.room_type:
            raise HTTPException(status_code=422, detail="Choose a room with the right capacity and type for this session.")
        entry.room_id = room.id
    entry.day, entry.start_period = payload.day, payload.period
    db.flush()
    conflicts = timetable_conflicts(db, timetable.id)
    introduced_conflicts = [item for item in conflicts if
                            (tuple(item.get("entry_ids", [])), item.get("category"), item.get("day"),
                             tuple(item.get("periods", [])), item.get("reason")) not in previous_signatures]
    if introduced_conflicts:
        entry.day, entry.start_period = previous_day, previous_period
        entry.room_id = previous_room
        db.rollback()
        raise HTTPException(status_code=409, detail={"message": "That move creates a schedule conflict.", "conflicts": introduced_conflicts})
    audit(db, user, "moved", "timetable_entry", entry.id)
    db.commit()
    room = db.get(Room, entry.room_id)
    return {"id": str(entry.id), "day": entry.day, "period": entry.start_period,
            "duration_periods": entry.duration_periods, "room_id": str(entry.room_id),
            "room": room.name if room else ""}


@router.post("/timetables/{timetable_id}/approval")
def decide_timetable_approval(timetable_id: UUID, payload: TimetableApprovalDecision, request: Request,
                              db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    if user.role not in (Role.super_admin, Role.college_admin):
        raise HTTPException(status_code=403, detail="Only a college admin can review timetable approvals.")
    timetable = timetable_or_404(db, timetable_id, user, lock=True)
    if timetable.status != "draft" or timetable.approval_status != "pending":
        raise HTTPException(status_code=409, detail="This timetable is not waiting for approval.")
    note = payload.note.strip() if payload.note else ""
    if payload.decision == "reject" and len(note) < 2:
        raise HTTPException(status_code=422, detail="Add a short reason when returning a timetable for changes.")
    now = datetime.now(timezone.utc)
    timetable.approval_reviewed_by = user.id
    timetable.approval_reviewed_at = now
    timetable.approval_note = note or None
    requester_id = timetable.approval_requested_by
    if payload.decision == "reject":
        timetable.approval_status = "rejected"
        if requester_id:
            notify_user(db, requester_id, "approval_updates", "Timetable returned for changes",
                        f"{timetable.name} · version {timetable.version}: {note}")
        audit(db, user, "approval_rejected", "timetable", timetable.id)
        db.commit()
        return {"id": str(timetable.id), "status": timetable.status,
                "approval_status": timetable.approval_status, "version": timetable.version}
    conflicts = timetable_conflicts(db, timetable.id)
    if conflicts:
        db.rollback()
        raise HTTPException(status_code=409, detail={"message": "Resolve all timetable conflicts before approving.", "conflicts": conflicts})
    timetable.approval_status = "approved"
    publish_timetable_record(db, timetable, user)
    if requester_id:
        notify_user(db, requester_id, "approval_updates", "Timetable approved and published",
                    f"{timetable.name} · version {timetable.version} is now published.")
    audit(db, user, "approval_approved", "timetable", timetable.id)
    db.commit()
    return {"id": str(timetable.id), "status": timetable.status,
            "approval_status": timetable.approval_status, "version": timetable.version}


@router.post("/timetables/{timetable_id}/publish")
def publish_timetable(timetable_id: UUID, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ensure_browser_origin(request)
    timetable = timetable_or_404(db, timetable_id, user, lock=True)
    if user.role not in (Role.super_admin, Role.college_admin):
        raise HTTPException(status_code=403, detail="A college admin must publish the timetable.")
    if timetable.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft timetables can be published.")
    if timetable.approval_status == "pending":
        raise HTTPException(status_code=409, detail="Review this timetable in the approvals queue before publishing.")
    conflicts = timetable_conflicts(db, timetable.id)
    if conflicts:
        raise HTTPException(status_code=409, detail={"message": "Resolve all timetable conflicts before publishing.", "conflicts": conflicts})
    timetable.approval_status = "approved"
    timetable.approval_reviewed_by = user.id
    timetable.approval_reviewed_at = datetime.now(timezone.utc)
    timetable.approval_note = None
    publish_timetable_record(db, timetable, user)
    db.commit()
    return {"id": str(timetable.id), "status": timetable.status,
            "approval_status": timetable.approval_status, "version": timetable.version}
