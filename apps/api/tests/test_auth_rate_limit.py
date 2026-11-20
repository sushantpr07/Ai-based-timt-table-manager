from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


def test_sign_in_rate_limit_is_scoped_to_hashed_account_identity():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    suffix = uuid4().hex
    first_email = f"first-{suffix}@example.com"
    second_email = f"second-{suffix}@example.com"

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            for _ in range(10):
                response = client.post("/api/v1/auth/sign-in", json={"email": first_email, "password": "incorrect"})
                assert response.status_code == 401
            limited = client.post("/api/v1/auth/sign-in", json={"email": first_email, "password": "incorrect"})
            assert limited.status_code == 429
            assert int(limited.headers["retry-after"]) > 0
            other_account = client.post("/api/v1/auth/sign-in", json={"email": second_email, "password": "incorrect"})
            assert other_account.status_code == 401
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
