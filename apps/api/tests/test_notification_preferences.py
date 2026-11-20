from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import AuditEvent, Institution, Notification, Role, User
from app.routes.campus import notify_user
from app.security import create_access_token
from test_client_auth import authenticate_client


def test_user_can_save_notification_preferences_and_they_filter_future_notices():
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
        user_id = user.id

    def override_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            authenticate_client(client, access_token)
            initial = client.get("/api/v1/settings")
            assert initial.status_code == 200
            assert initial.json()["notification_preferences"] == {"schedule_updates": True, "approval_updates": True}
            saved = client.patch("/api/v1/settings/notifications", json={
                "schedule_updates": False, "approval_updates": True,
            })
            assert saved.status_code == 200
            assert saved.json()["notification_preferences"] == {"schedule_updates": False, "approval_updates": True}

        with testing_session() as db:
            user = db.get(User, user_id)
            notify_user(db, user.id, "schedule_updates", "Published", "New schedule")
            notify_user(db, user.id, "approval_updates", "Approval", "Needs review")
            db.commit()
            notices = db.scalars(select(Notification).where(Notification.user_id == user_id)).all()
            assert [item.title for item in notices] == ["Approval"]
            audit = db.scalars(select(AuditEvent).where(AuditEvent.resource_type == "notification_preferences")).all()
            assert len(audit) == 1
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
