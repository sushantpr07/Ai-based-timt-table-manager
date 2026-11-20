from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import (AcademicTerm, Department, Faculty, FacultyAvailability, Institution, Role,
                        Room, Section, Semester, Subject, Timetable, TimetableEntry, User)
from app.security import create_access_token
from test_client_auth import authenticate_client


def test_conflicting_room_move_suggests_an_alternative_and_respects_availability():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with testing_session() as db:
        institution = Institution(name="Test University")
        db.add(institution); db.flush()
        department = Department(institution_id=institution.id, name="Computing", code="CS")
        db.add(department); db.flush()
        admin = User(institution_id=institution.id, email="admin@test.invalid", full_name="Campus Admin",
                     password_hash="unused", role=Role.college_admin)
        faculty_user_1 = User(institution_id=institution.id, department_id=department.id, email="one@test.invalid",
                              full_name="Faculty One", password_hash="unused", role=Role.faculty)
        faculty_user_2 = User(institution_id=institution.id, department_id=department.id, email="two@test.invalid",
                              full_name="Faculty Two", password_hash="unused", role=Role.faculty)
        db.add_all([admin, faculty_user_1, faculty_user_2]); db.flush()
        term = AcademicTerm(institution_id=institution.id, name="Fall", academic_year="2026-27", is_current=True)
        db.add(term); db.flush()
        semester = Semester(department_id=department.id, term_id=term.id, number=1)
        db.add(semester); db.flush()
        section_1 = Section(semester_id=semester.id, name="A", strength=25)
        section_2 = Section(semester_id=semester.id, name="B", strength=22)
        db.add_all([section_1, section_2]); db.flush()
        faculty_1 = Faculty(user_id=faculty_user_1.id, department_id=department.id, max_weekly_periods=18)
        faculty_2 = Faculty(user_id=faculty_user_2.id, department_id=department.id, max_weekly_periods=18)
        db.add_all([faculty_1, faculty_2]); db.flush()
        subject_1 = Subject(department_id=department.id, code="CS101", name="Algorithms", room_type="classroom")
        subject_2 = Subject(department_id=department.id, code="CS102", name="Databases", room_type="classroom")
        db.add_all([subject_1, subject_2]); db.flush()
        shared_room = Room(institution_id=institution.id, name="Room 1", capacity=20, room_type="classroom")
        alternate_room = Room(institution_id=institution.id, name="Room 2", capacity=30, room_type="classroom")
        db.add_all([shared_room, alternate_room]); db.flush()
        timetable = Timetable(institution_id=institution.id, term_id=term.id, department_id=department.id,
                              name="Draft", status="draft", version=1, days=2, weekdays=[0, 2], periods_per_day=3)
        db.add(timetable); db.flush()
        target = TimetableEntry(timetable_id=timetable.id, section_id=section_1.id, subject_id=subject_1.id,
                                faculty_id=faculty_1.id, room_id=shared_room.id, day=0, start_period=0,
                                duration_periods=1)
        blocker = TimetableEntry(timetable_id=timetable.id, section_id=section_2.id, subject_id=subject_2.id,
                                 faculty_id=faculty_2.id, room_id=shared_room.id, day=0, start_period=0,
                                 duration_periods=1)
        db.add_all([target, blocker,
                     FacultyAvailability(faculty_id=faculty_1.id, day=2, period=0, is_available=False),
                     FacultyAvailability(faculty_id=faculty_2.id, day=0, period=0, is_available=False)])
        db.commit()
        token = create_access_token(admin)
        timetable_id, entry_id = timetable.id, target.id

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, token)
            saved_versions = client.get("/api/v1/campus/timetables")
            assert saved_versions.status_code == 200
            assert saved_versions.json()[0]["days"] == 2
            assert saved_versions.json()[0]["weekdays"] == [0, 2]
            assert saved_versions.json()[0]["periods_per_day"] == 3
            diagnostics = client.get(f"/api/v1/campus/timetables/{timetable_id}/conflicts")
            assert diagnostics.status_code == 200
            issue_categories = {item["category"] for item in diagnostics.json()["conflicts"]}
            assert "room_overlap" in issue_categories
            assert "faculty_availability" in issue_categories
            assert "room_eligibility" in issue_categories
            response = client.get(f"/api/v1/campus/timetables/{timetable_id}/entries/{entry_id}/suggestions")
            assert response.status_code == 200
            suggestions = response.json()["suggestions"]
            room_swap = next(item for item in suggestions if item["day"] == 0 and item["period"] == 0 and item["room"] == "Room 2")
            assert not any(item["day"] == 1 and item["period"] == 0 for item in suggestions)
            unavailable_move = client.patch(f"/api/v1/campus/timetables/{timetable_id}/entries/{entry_id}", json={
                "day": 1, "period": 0
            })
            assert unavailable_move.status_code == 409
            moved = client.patch(f"/api/v1/campus/timetables/{timetable_id}/entries/{entry_id}", json={
                "day": room_swap["day"], "period": room_swap["period"], "room_id": room_swap["room_id"]
            })
            assert moved.status_code == 200
            assert moved.json()["room"] == "Room 2"
            repaired = client.post(f"/api/v1/campus/timetables/{timetable_id}/repair")
            assert repaired.status_code == 200
            assert repaired.json()["moved_count"] == 1
            assert repaired.json()["conflicts"] == []
            target_after_repair = next(item for item in repaired.json()["entries"] if item["id"] == str(entry_id))
            break_weekday = [0, 2][target_after_repair["day"]]
            break_start_minutes = 9 * 60 + target_after_repair["period"] * 60
            break_end_minutes = break_start_minutes + 60
            break_window = {
                "weekday": break_weekday,
                "start_time": f"{break_start_minutes // 60:02d}:{break_start_minutes % 60:02d}",
                "end_time": f"{break_end_minutes // 60:02d}:{break_end_minutes % 60:02d}",
            }
            saved_break = client.patch("/api/v1/settings/institution", json={
                "name": "Test University", "timezone": "Asia/Kolkata",
                "timetable_breaks": [break_window],
            })
            assert saved_break.status_code == 200
            break_conflicts = client.get(f"/api/v1/campus/timetables/{timetable_id}/conflicts")
            assert "institution_break" in {item["category"] for item in break_conflicts.json()["conflicts"]}
            break_suggestions = client.get(f"/api/v1/campus/timetables/{timetable_id}/entries/{entry_id}/suggestions")
            assert not any(item["day"] == target_after_repair["day"] and item["period"] == target_after_repair["period"]
                           for item in break_suggestions.json()["suggestions"])
            rejected_move = client.patch(f"/api/v1/campus/timetables/{timetable_id}/entries/{entry_id}", json={
                "day": target_after_repair["day"], "period": target_after_repair["period"]
            })
            assert rejected_move.status_code == 409
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
