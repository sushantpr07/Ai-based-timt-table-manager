import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import EmailVerificationToken, Institution, Role, User
from app.security import hash_password


def test_verification_token_is_single_use_and_unlocks_sign_in(monkeypatch):
    monkeypatch.setattr(settings, "require_email_verification", True)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    raw_token = "a-single-use-email-verification-token-123456"
    with testing_session() as db:
        institution = Institution(name="Example University")
        db.add(institution); db.flush()
        user = User(institution_id=institution.id, email="admin@example.com", full_name="Campus Admin",
                    password_hash=hash_password("correct-horse-battery-staple"), role=Role.college_admin,
                    email_verified=False)
        db.add(user); db.flush()
        db.add(EmailVerificationToken(user_id=user.id, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                                      expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
        db.commit()

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            blocked = client.post("/api/v1/auth/sign-in", json={
                "email": "admin@example.com", "password": "correct-horse-battery-staple"
            })
            assert blocked.status_code == 403

            verified = client.post("/api/v1/auth/verify-email", json={"token": raw_token})
            assert verified.status_code == 200
            assert verified.json()["email_verified"] is True

            replay = client.post("/api/v1/auth/verify-email", json={"token": raw_token})
            assert replay.status_code == 400

            signed_in = client.post("/api/v1/auth/sign-in", json={
                "email": "admin@example.com", "password": "correct-horse-battery-staple"
            })
            assert signed_in.status_code == 200
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
