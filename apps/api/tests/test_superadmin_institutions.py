from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Institution, Role, User
from app.security import create_access_token
from test_client_auth import authenticate_client


def test_super_admin_can_create_and_update_institutions():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        existing = Institution(name="Existing University")
        db.add(existing)
        super_admin = User(institution_id=None, email="root@test.invalid", full_name="Platform Admin",
                           password_hash="unused", role=Role.super_admin, email_verified=True)
        db.add(super_admin)
        db.commit()
        token = create_access_token(super_admin)

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, token)
            directory = client.get("/api/v1/superadmin/institutions")
            assert directory.status_code == 200
            assert [row["name"] for row in directory.json()] == ["Existing University"]

            created = client.post("/api/v1/superadmin/institutions", json={
                "name": "North Campus University", "timezone": "Asia/Kolkata"
            })
            assert created.status_code == 201
            institution_id = created.json()["id"]
            assert created.json()["admins"] == []

            updated = client.patch(f"/api/v1/superadmin/institutions/{institution_id}", json={
                "name": "North Campus", "timezone": "Europe/London"
            })
            assert updated.status_code == 200
            assert updated.json()["name"] == "North Campus"
            assert updated.json()["timezone"] == "Europe/London"

            department = client.post("/api/v1/campus/departments", json={
                "name": "Computing", "code": "CS", "institution_id": institution_id
            })
            term = client.post("/api/v1/campus/terms", json={
                "name": "Autumn", "academic_year": "2026-27", "institution_id": institution_id
            })
            room = client.post("/api/v1/campus/rooms", json={
                "name": "Lab 1", "capacity": 30, "room_type": "lab", "institution_id": institution_id
            })
            assert department.status_code == 201
            assert term.status_code == 201
            assert room.status_code == 201
            assert department.json()["institution_id"] == institution_id
            assert term.json()["institution_id"] == institution_id
            assert room.json()["institution_id"] == institution_id
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_college_admin_cannot_access_super_admin_directory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        institution = Institution(name="Test University")
        db.add(institution)
        db.flush()
        admin = User(institution_id=institution.id, email="admin@test.invalid", full_name="Campus Admin",
                     password_hash="unused", role=Role.college_admin)
        db.add(admin)
        db.commit()
        token = create_access_token(admin)

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, token)
            assert client.get("/api/v1/superadmin/institutions").status_code == 403
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
