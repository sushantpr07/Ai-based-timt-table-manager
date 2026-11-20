from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.assistant import requests_timetable_generation
from app.main import app
from app.models import (AcademicTerm, Department, Faculty, Institution, Room, Section, Semester,
                        Subject, TeachingAssignment, Timetable, Role, User)
from app.security import create_access_token
from test_client_auth import authenticate_client


def test_assistant_only_proposes_generation_for_explicit_positive_requests():
    assert requests_timetable_generation("Please generate a timetable for this term")
    assert requests_timetable_generation("इस term के लिए टाइमटेबल बना दो")
    assert not requests_timetable_generation("Do not generate a timetable yet")
    assert not requests_timetable_generation("I don't want to create a schedule")


def test_assistant_proposal_requires_confirmation_before_optimizer_creates_draft(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        institution = Institution(name="Example University")
        db.add(institution); db.flush()
        department = Department(institution_id=institution.id, name="Computing", code="CS")
        db.add(department); db.flush()
        term = AcademicTerm(institution_id=institution.id, name="Fall", academic_year="2026-27", is_current=True)
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
        faculty = Faculty(user_id=faculty_user.id, department_id=department.id, max_weekly_periods=18)
        subject = Subject(department_id=department.id, code="CS101", name="Algorithms", room_type="classroom")
        room = Room(institution_id=institution.id, name="Room 1", capacity=40, room_type="classroom")
        db.add_all([faculty, subject, room]); db.flush()
        db.add(TeachingAssignment(subject_id=subject.id, section_id=section.id, faculty_id=faculty.id,
                                  sessions_per_week=2, duration_periods=1))
        db.commit()
        access_token = create_access_token(admin)
        term_id, department_id = str(term.id), str(department.id)

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    async def guided_response(message, config, campus_context=""):
        return {"reply": "Ready to help.", "mode": "guided"}

    monkeypatch.setattr("app.main.assistant_reply", guided_response)
    try:
        with TestClient(app) as client:
            authenticate_client(client, access_token)
            proposal_response = client.post("/api/v1/assistant/chat", json={
                "message": "Generate a timetable for this term", "term_id": term_id,
                "department_id": department_id,
            })
            assert proposal_response.status_code == 200
            proposal = proposal_response.json()["proposal"]
            assert proposal["action"] == "generate_timetable"
            with testing_session() as db:
                assert db.scalar(select(Timetable)) is None

            confirmed = client.post("/api/v1/assistant/confirm", json={
                "action": proposal["action"], "term_id": proposal["term_id"],
                "department_id": proposal["department_id"], "name": proposal["name"],
            })
            assert confirmed.status_code == 201
            assert len(confirmed.json()["entries"]) == 2
            with testing_session() as db:
                assert db.scalar(select(Timetable)) is not None
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
