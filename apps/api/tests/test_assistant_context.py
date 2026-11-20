import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.assistant_context import build_assistant_context
from app.db import Base
from app.models import (AcademicTerm, Department, Faculty, Institution, Role, Room, Section,
                        Semester, Subject, Timetable, TimetableEntry, User)


def test_assistant_context_includes_selected_published_schedule_and_room_data():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as db:
            institution = Institution(name="Example University")
            db.add(institution); db.flush()
            department = Department(institution_id=institution.id, name="Computing", code="CS")
            db.add(department); db.flush()
            term = AcademicTerm(institution_id=institution.id, name="Fall", academic_year="2026-27")
            db.add(term); db.flush()
            semester = Semester(department_id=department.id, term_id=term.id, number=1)
            admin = User(institution_id=institution.id, email="admin@example.invalid", full_name="Campus Admin",
                         password_hash="unused", role=Role.college_admin)
            faculty_user = User(institution_id=institution.id, department_id=department.id,
                                email="faculty@example.invalid", full_name="Faculty Member",
                                password_hash="unused", role=Role.faculty)
            db.add_all([semester, admin, faculty_user]); db.flush()
            section = Section(semester_id=semester.id, name="A", strength=30)
            faculty = Faculty(user_id=faculty_user.id, department_id=department.id)
            subject = Subject(department_id=department.id, code="CS101", name="Algorithms")
            room = Room(institution_id=institution.id, name="Lab 1", capacity=36, room_type="lab")
            db.add_all([section, faculty, subject, room]); db.flush()
            timetable = Timetable(institution_id=institution.id, term_id=term.id,
                                  department_id=department.id, created_by=admin.id,
                                  name="Fall published", status="published", version=1,
                                  days=5, weekdays=[0, 1, 2, 3, 4], periods_per_day=8,
                                  period_labels=["09:00", "10:00", "11:00", "12:00",
                                                 "13:00", "14:00", "15:00", "16:00"])
            db.add(timetable); db.flush()
            db.add(TimetableEntry(timetable_id=timetable.id, section_id=section.id,
                                  subject_id=subject.id, faculty_id=faculty.id, room_id=room.id,
                                  day=2, start_period=1, duration_periods=2))
            db.commit()

            context = build_assistant_context(db, admin, term.id, department.id)

        data = json.loads(context)
        assert data["department"] == "Computing"
        assert data["room_directory"] == [{"name": "Lab 1", "type": "lab", "capacity": 36}]
        assert data["published_sessions"] == [{
            "weekday": "Wednesday", "start": "10:00", "subject": "Algorithms", "section": "A",
            "faculty": "Faculty Member", "room": "Lab 1", "duration_periods": 2,
        }]
        assert "cannot establish campus-wide room availability" in data["limitations"]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_assistant_context_refuses_cross_department_hod_requests():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as db:
            institution = Institution(name="Example University")
            db.add(institution); db.flush()
            own_department = Department(institution_id=institution.id, name="Computing", code="CS")
            other_department = Department(institution_id=institution.id, name="Physics", code="PH")
            db.add_all([own_department, other_department]); db.flush()
            term = AcademicTerm(institution_id=institution.id, name="Fall", academic_year="2026-27")
            hod = User(institution_id=institution.id, department_id=own_department.id,
                       email="hod@example.invalid", full_name="Department Head",
                       password_hash="unused", role=Role.hod)
            faculty = User(institution_id=institution.id, department_id=own_department.id,
                           email="faculty@example.invalid", full_name="Faculty Member",
                           password_hash="unused", role=Role.faculty)
            db.add_all([term, hod, faculty]); db.commit()

            context = build_assistant_context(db, hod, term.id, other_department.id)
            faculty_context = build_assistant_context(db, faculty, term.id, own_department.id)

        assert context == ""
        assert faculty_context == ""
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_assistant_context_refuses_cross_institution_admin_requests():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as db:
            first = Institution(name="First University")
            second = Institution(name="Second University")
            db.add_all([first, second]); db.flush()
            first_department = Department(institution_id=first.id, name="Computing", code="CS")
            second_department = Department(institution_id=second.id, name="Physics", code="PH")
            db.add_all([first_department, second_department]); db.flush()
            first_term = AcademicTerm(institution_id=first.id, name="Fall", academic_year="2026-27")
            second_term = AcademicTerm(institution_id=second.id, name="Fall", academic_year="2026-27")
            admin = User(institution_id=first.id, email="admin@example.invalid", full_name="Campus Admin",
                         password_hash="unused", role=Role.college_admin)
            db.add_all([first_term, second_term, admin]); db.commit()

            context = build_assistant_context(db, admin, second_term.id, second_department.id)

        assert context == ""
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_guided_assistant_answers_use_truthful_constraint_language():
    from app.assistant import guided_reply

    assert "hard constraints" in guided_reply("What is the faculty teaching load?")
    assert "capacity" in guided_reply("How are rooms chosen?")
    assert "does not calculate live availability" in guided_reply("Find a free room", "schedule context")
