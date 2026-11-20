from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import (AcademicTerm, Department, Faculty, Institution, Notification, Room,
                        Role, Section, Semester, Student, Subject, Timetable, TimetableEntry, User)
from app.security import create_access_token
from test_client_auth import authenticate_client


def test_hod_can_request_approval_and_admin_can_approve_and_publish():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        institution = Institution(name="Example University")
        db.add(institution); db.flush()
        department = Department(institution_id=institution.id, name="Engineering", code="ENG")
        db.add(department); db.flush()
        admin = User(institution_id=institution.id, email="admin@example.invalid", full_name="College Admin",
                     password_hash="unused", role=Role.college_admin)
        hod = User(institution_id=institution.id, department_id=department.id, email="hod@example.invalid",
                   full_name="Department Head", password_hash="unused", role=Role.hod)
        faculty_user = User(institution_id=institution.id, department_id=department.id, email="faculty@example.invalid",
                            full_name="Faculty Member", password_hash="unused", role=Role.faculty)
        student_user = User(institution_id=institution.id, department_id=department.id, email="student@example.invalid",
                            full_name="Student Member", password_hash="unused", role=Role.student)
        db.add_all([admin, hod, faculty_user, student_user]); db.flush()
        term = AcademicTerm(institution_id=institution.id, name="Fall", academic_year="2026-27")
        db.add(term); db.flush()
        semester = Semester(department_id=department.id, term_id=term.id, number=1)
        db.add(semester); db.flush()
        section = Section(semester_id=semester.id, name="A", strength=24)
        db.add(section); db.flush()
        faculty = Faculty(user_id=faculty_user.id, department_id=department.id)
        student = Student(user_id=student_user.id, section_id=section.id, student_number="S-100")
        subject = Subject(department_id=department.id, code="ENG101", name="Design", room_type="classroom")
        room = Room(institution_id=institution.id, name="Room 1", capacity=30, room_type="classroom")
        db.add_all([faculty, student, subject, room]); db.flush()
        timetable = Timetable(institution_id=institution.id, term_id=term.id, department_id=department.id,
                              name="Fall schedule", status="draft", version=1, days=5, periods_per_day=8)
        db.add(timetable); db.flush()
        db.add(TimetableEntry(timetable_id=timetable.id, section_id=section.id, subject_id=subject.id,
                              faculty_id=faculty.id, room_id=room.id, day=0, start_period=0, duration_periods=1))
        db.commit()
        timetable_id = timetable.id
        entry_id = db.scalar(select(TimetableEntry.id).where(TimetableEntry.timetable_id == timetable.id))
        admin_token, hod_token = create_access_token(admin), create_access_token(hod)
        requester_id = hod.id
        faculty_user_id, student_user_id = faculty_user.id, student_user.id

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, hod_token)
            requested = client.post(f"/api/v1/campus/timetables/{timetable_id}/request-approval")
            assert requested.status_code == 200
            assert requested.json()["approval_status"] == "pending"
            locked = client.patch(f"/api/v1/campus/timetables/{timetable_id}/entries/{entry_id}", json={"day": 0, "period": 1})
            assert locked.status_code == 409

            authenticate_client(client, admin_token)
            queue = client.get("/api/v1/campus/timetables/approvals")
            assert queue.status_code == 200
            assert len(queue.json()) == 1
            assert queue.json()[0]["requested_by_name"] == "Department Head"
            approved = client.post(f"/api/v1/campus/timetables/{timetable_id}/approval", json={"decision": "approve"})
            assert approved.status_code == 200
            assert approved.json()["status"] == "published"
            assert approved.json()["approval_status"] == "approved"

        with testing_session() as db:
            saved = db.get(Timetable, timetable_id)
            assert saved.status == "published"
            assert saved.approval_reviewed_by is not None
            notifications = set(db.scalars(select(Notification.user_id)).all())
            assert {requester_id, faculty_user_id, student_user_id}.issubset(notifications)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
