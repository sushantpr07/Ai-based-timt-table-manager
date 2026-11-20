from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.db import get_db
from app.main import app


def test_health_endpoints_distinguish_database_readiness_from_liveness():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            ready = client.get("/api/v1/health")
            live = client.get("/api/v1/health/live")
            assert ready.status_code == 200
            assert ready.json()["status"] == "ok"
            assert live.status_code == 200
            assert live.json()["status"] == "ok"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_readiness_returns_service_unavailable_when_database_query_fails():
    class OfflineDatabase:
        def execute(self, statement):
            raise SQLAlchemyError("database offline")

    app.dependency_overrides[get_db] = lambda: OfflineDatabase()
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/health").status_code == 503
            assert client.get("/api/v1/health/live").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_request_logs_omit_query_strings_and_return_a_correlation_id(caplog):
    with caplog.at_level(logging.INFO, logger="campusflow.request"):
        with TestClient(app) as client:
            response = client.get("/api/v1/health/live?token=highly-sensitive-value")
            missing_route = client.get("/api/v1/highly-sensitive-path-segment?token=another-secret")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")
    assert missing_route.status_code == 404
    assert "highly-sensitive-value" not in caplog.text
    assert "another-secret" not in caplog.text
    assert "highly-sensitive-path-segment" not in caplog.text
    assert "/api/v1/health/live" in caplog.text
