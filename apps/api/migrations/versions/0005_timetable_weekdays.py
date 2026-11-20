"""Persist the selected calendar weekdays on each timetable.

Revision ID: 0005_timetable_weekdays
Revises: 0004_notification_preferences
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_timetable_weekdays"
down_revision = "0004_notification_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("timetables")}
    if "weekdays" not in columns:
        op.add_column("timetables", sa.Column("weekdays", sa.JSON(), nullable=False,
                                                server_default=sa.text("'[0,1,2,3,4]'")))
    timetable = sa.table("timetables", sa.column("id", sa.Uuid()), sa.column("days", sa.Integer()),
                         sa.column("weekdays", sa.JSON()))
    rows = bind.execute(sa.select(timetable.c.id, timetable.c.days)).all()
    for timetable_id, days in rows:
        bind.execute(sa.update(timetable).where(timetable.c.id == timetable_id)
                     .values(weekdays=list(range(max(1, min(int(days or 5), 7))))))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("timetables")}
    if "weekdays" in columns:
        op.drop_column("timetables", "weekdays")
