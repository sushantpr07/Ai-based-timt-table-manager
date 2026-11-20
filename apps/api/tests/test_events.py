from queue import Empty

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.events import publish_campus_refresh, subscribe_campus_events, unsubscribe_campus_events
from app.main import app as _app  # noqa: F401 - registers the post-commit audit publisher
from app.models import AuditEvent


def test_campus_refresh_events_coalesce_and_unsubscribe():
    subscriber = subscribe_campus_events()
    try:
        publish_campus_refresh()
        publish_campus_refresh()
        assert subscriber.qsize() == 1
        subscriber.get_nowait()
    finally:
        unsubscribe_campus_events(subscriber)

    publish_campus_refresh()
    try:
        subscriber.get_nowait()
        raise AssertionError("Unsubscribed listener received a refresh event.")
    except Empty:
        pass


def test_committed_audit_events_publish_and_rolled_back_changes_do_not():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    subscriber = subscribe_campus_events()
    try:
        with session_factory() as db:
            db.add(AuditEvent(action="created", resource_type="department"))
            db.commit()
        assert subscriber.get_nowait() is None

        with session_factory() as db:
            db.add(AuditEvent(action="created", resource_type="department"))
            db.flush()
            db.rollback()
        try:
            subscriber.get_nowait()
            raise AssertionError("A rolled-back campus change emitted a refresh event.")
        except Empty:
            pass
    finally:
        unsubscribe_campus_events(subscriber)
        Base.metadata.drop_all(engine)
        engine.dispose()
