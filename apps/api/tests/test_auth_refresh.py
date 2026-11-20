from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Institution, RefreshSession, Role, User
from app.security import hash_password


def test_refresh_rotation_rejects_reuse_and_revokes_the_token_family():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with testing_session() as db:
        institution = Institution(name="Test University")
        db.add(institution); db.flush()
        user = User(institution_id=institution.id, email="admin@example.com", full_name="Campus Admin",
                    password_hash=hash_password("correct-horse-battery-staple"), role=Role.college_admin)
        db.add(user); db.commit()

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            csrf_bootstrap = client.get("/api/v1/auth/csrf")
            assert csrf_bootstrap.status_code == 200
            csrf_token = csrf_bootstrap.json()["csrf_token"]
            assert csrf_bootstrap.cookies.get("campusflow_csrf") == csrf_token
            client.headers.update({"Origin": "http://localhost:3000", "X-CSRF-Token": csrf_token})
            signed_in = client.post("/api/v1/auth/sign-in", json={
                "email": "admin@example.com", "password": "correct-horse-battery-staple"
            })
            assert signed_in.status_code == 200
            old_token = signed_in.cookies.get("campusflow_refresh")
            assert old_token
            rotated_csrf_token = signed_in.cookies.get("campusflow_csrf")
            assert rotated_csrf_token and rotated_csrf_token != csrf_token
            csrf_token = rotated_csrf_token
            client.headers.update({"X-CSRF-Token": csrf_token})
            client.cookies.set("campusflow_session", signed_in.cookies.get("campusflow_session"))
            client.cookies.set("campusflow_refresh", old_token)
            client.cookies.set("campusflow_csrf", csrf_token)

            rejected = client.post("/api/v1/me/notifications/read-all", headers={
                "Origin": "http://localhost:3000", "X-CSRF-Token": "wrong-token",
            })
            assert rejected.status_code == 403
            csrf_headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": csrf_token}

            rotated = client.post("/api/v1/auth/refresh", headers={
                **csrf_headers, "Cookie": f"campusflow_refresh={old_token}; campusflow_csrf={csrf_token}"
            })
            assert rotated.status_code == 200
            new_token = rotated.cookies.get("campusflow_refresh")
            assert new_token and new_token != old_token

            replay = client.post("/api/v1/auth/refresh", headers={
                **csrf_headers, "Cookie": f"campusflow_refresh={old_token}; campusflow_csrf={csrf_token}"
            })
            assert replay.status_code == 401
            current_token_after_replay = client.post("/api/v1/auth/refresh", headers={
                **csrf_headers, "Cookie": f"campusflow_refresh={new_token}; campusflow_csrf={csrf_token}"
            })
            assert current_token_after_replay.status_code == 401

        with testing_session() as db:
            sessions = db.scalars(select(RefreshSession)).all()
            assert len(sessions) == 2
            assert all(session.revoked_at is not None for session in sessions)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
