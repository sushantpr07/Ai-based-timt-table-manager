from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import AuditEvent, Institution, Role, User
from app.security import create_access_token
from test_client_auth import authenticate_client


def test_college_admin_can_save_and_read_recurring_campus_breaks():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        institution = Institution(name="Example University")
        db.add(institution); db.flush()
        user = User(institution_id=institution.id, email="admin@example.invalid", full_name="Campus Admin",
                    password_hash="unused", role=Role.college_admin)
        db.add(user); db.commit()
        access_token = create_access_token(user)

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, access_token)
            response = client.patch("/api/v1/settings/institution", json={
                "name": "Example University", "timezone": "Asia/Kolkata",
                "timetable_period_start": "09:00", "timetable_period_minutes": 60,
                "timetable_breaks": [
                    {"weekday": 0, "start_time": "12:00", "end_time": "13:00"},
                    {"weekday": 2, "start_time": "12:30", "end_time": "13:15"},
                ],
            })
            assert response.status_code == 200
            assert response.json()["timetable_breaks"][0]["weekday"] == 0
            assert client.get("/api/v1/settings").json()["institution"]["timetable_breaks"][1]["weekday"] == 2
            invalid = client.patch("/api/v1/settings/institution", json={
                "name": "Example University", "timezone": "Asia/Kolkata",
                "timetable_breaks": [{"weekday": 0, "start_time": "13:00", "end_time": "12:00"}],
            })
            assert invalid.status_code == 422
        with testing_session() as db:
            events = db.scalars(select(AuditEvent).where(AuditEvent.resource_type == "institution_settings")).all()
            assert len(events) == 1
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
