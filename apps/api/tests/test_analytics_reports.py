from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import (AcademicTerm, Department, Faculty, Institution, Room, Section, Semester,
                        Subject, Timetable, TimetableEntry, User, Role)
from app.security import create_access_token
from test_client_auth import authenticate_client


def test_scoped_reports_return_detail_and_csv_export_escapes_spreadsheet_formulas():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        institution = Institution(name="Example University")
        db.add(institution); db.flush()
        department = Department(institution_id=institution.id, name="Computing", code="CS")
        db.add(department); db.flush()
        term = AcademicTerm(institution_id=institution.id, name="Fall", academic_year="2026-27")
        db.add(term); db.flush()
        semester = Semester(department_id=department.id, term_id=term.id, number=1)
        db.add(semester); db.flush()
        section = Section(semester_id=semester.id, name="A", strength=25)
        db.add(section); db.flush()
        admin = User(institution_id=institution.id, email="admin@example.invalid", full_name="Campus Admin",
                     password_hash="unused", role=Role.college_admin)
        faculty_user = User(institution_id=institution.id, department_id=department.id,
                            email="faculty@example.invalid", full_name="Faculty Member",
                            password_hash="unused", role=Role.faculty)
        db.add_all([admin, faculty_user]); db.flush()
        faculty = Faculty(user_id=faculty_user.id, department_id=department.id)
        subject = Subject(department_id=department.id, code=" =1+1", name="Calculus")
        room = Room(institution_id=institution.id, name="Room 1", capacity=40)
        db.add_all([faculty, subject, room]); db.flush()
        timetable = Timetable(institution_id=institution.id, term_id=term.id, department_id=department.id,
                              created_by=admin.id, name="Fall draft", status="published", version=1,
                              days=5, periods_per_day=8)
        db.add(timetable); db.flush()
        db.add_all([
            TimetableEntry(timetable_id=timetable.id, section_id=section.id, subject_id=subject.id,
                           faculty_id=faculty.id, room_id=room.id, day=0, start_period=0, duration_periods=1),
            TimetableEntry(timetable_id=timetable.id, section_id=section.id, subject_id=subject.id,
                           faculty_id=faculty.id, room_id=room.id, day=0, start_period=0, duration_periods=1),
        ])
        db.commit()
        access_token = create_access_token(admin)
        term_id = str(term.id)

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, access_token)
            query = f"?term_id={term_id}"
            schedule = client.get(f"/api/v1/analytics/reports/schedule{query}")
            assert schedule.status_code == 200
            assert len(schedule.json()["rows"]) == 2
            assert schedule.json()["rows"][0]["period"] == 1
            assert schedule.json()["rows"][0]["start_time"] == "09:00"

            load = client.get(f"/api/v1/analytics/reports/faculty-load{query}")
            assert load.status_code == 200
            assert load.json()["rows"][0]["sessions"] == 2
            assert load.json()["rows"][0]["teaching_periods"] == 2

            utilization = client.get(f"/api/v1/analytics/reports/room-utilization{query}")
            assert utilization.status_code == 200
            assert utilization.json()["rows"][0]["utilization_percent"] == 5.0

            conflicts = client.get(f"/api/v1/analytics/reports/conflicts{query}")
            assert conflicts.status_code == 200
            assert len(conflicts.json()["rows"]) == 1

            exported = client.get(f"/api/v1/analytics/reports/schedule/export.csv{query}")
            assert exported.status_code == 200
            assert exported.headers["content-type"].startswith("text/csv")
            assert "' =1+1" in exported.text
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_conflict_report_detects_shared_room_clash_between_departments():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        institution = Institution(name="Example University")
        db.add(institution); db.flush()
        departments = [Department(institution_id=institution.id, name=name, code=code)
                       for name, code in (("Computing", "CS"), ("Physics", "PH"))]
        db.add_all(departments); db.flush()
        term = AcademicTerm(institution_id=institution.id, name="Fall", academic_year="2026-27")
        admin = User(institution_id=institution.id, email="admin@example.invalid", full_name="Campus Admin",
                     password_hash="unused", role=Role.college_admin)
        db.add_all([term, admin]); db.flush()
        room = Room(institution_id=institution.id, name="Shared Hall", capacity=100)
        db.add(room); db.flush()
        for number, department in enumerate(departments, 1):
            semester = Semester(department_id=department.id, term_id=term.id, number=1)
            faculty_user = User(institution_id=institution.id, department_id=department.id,
                                email=f"faculty{number}@example.invalid", full_name=f"Faculty {number}",
                                password_hash="unused", role=Role.faculty)
            db.add_all([semester, faculty_user]); db.flush()
            section = Section(semester_id=semester.id, name="A", strength=25)
            faculty = Faculty(user_id=faculty_user.id, department_id=department.id)
            subject = Subject(department_id=department.id, code=f"SUB{number}", name=f"Subject {number}")
            db.add_all([section, faculty, subject]); db.flush()
            timetable = Timetable(institution_id=institution.id, term_id=term.id, department_id=department.id,
                                  created_by=admin.id, name=f"{department.code} timetable", status="published",
                                  version=1, days=5, periods_per_day=8,
                                  period_minutes=45 if number == 1 else 30,
                                  period_labels=["09:00"] * 8 if number == 1 else ["08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00"])
            db.add(timetable); db.flush()
            db.add(TimetableEntry(timetable_id=timetable.id, section_id=section.id, subject_id=subject.id,
                                  faculty_id=faculty.id, room_id=room.id, day=0, start_period=0 if number == 1 else 2,
                                  duration_periods=1))
        db.commit()
        access_token = create_access_token(admin)

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, access_token)
            response = client.get("/api/v1/analytics/reports/conflicts")
            assert response.status_code == 200
            rows = response.json()["rows"]
            assert len(rows) == 1
            assert rows[0]["reason"] == "The same room is scheduled twice."
            assert "Computing / Physics" == rows[0]["department"]
            assert rows[0]["periods"] == "09:30–09:45"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
