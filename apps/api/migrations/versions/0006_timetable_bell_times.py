"""Add institution bell-time defaults and immutable timetable period labels.

Revision ID: 0006_timetable_bell_times
Revises: 0005_timetable_weekdays
Create Date: 2026-11-18
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_timetable_bell_times"
down_revision = "0005_timetable_weekdays"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    institution_columns = {column["name"] for column in inspector.get_columns("institutions")}
    timetable_columns = {column["name"] for column in inspector.get_columns("timetables")}
    if "timetable_period_start" not in institution_columns:
        op.add_column("institutions", sa.Column("timetable_period_start", sa.String(length=5), nullable=False,
                                                  server_default=sa.text("'09:00'")))
    if "timetable_period_minutes" not in institution_columns:
        op.add_column("institutions", sa.Column("timetable_period_minutes", sa.Integer(), nullable=False,
                                                  server_default=sa.text("60")))
    labels_added = "period_labels" not in timetable_columns
    if labels_added:
        op.add_column("timetables", sa.Column("period_labels", sa.JSON(), nullable=False,
                                                server_default=sa.text("'[]'")))

    if not labels_added:
        return

    institutions = sa.table("institutions", sa.column("id", sa.Uuid()),
                            sa.column("timetable_period_start", sa.String()),
                            sa.column("timetable_period_minutes", sa.Integer()))
    timetables = sa.table("timetables", sa.column("id", sa.Uuid()),
                          sa.column("institution_id", sa.Uuid()), sa.column("periods_per_day", sa.Integer()),
                          sa.column("period_labels", sa.JSON()))
    rows = bind.execute(sa.select(timetables.c.id, timetables.c.periods_per_day,
                                 institutions.c.timetable_period_start, institutions.c.timetable_period_minutes)
                        .select_from(timetables.join(institutions, timetables.c.institution_id == institutions.c.id))).all()
    for timetable_id, count, start, duration in rows:
        parsed_start = datetime.strptime(start or "09:00", "%H:%M")
        start_minutes = parsed_start.hour * 60 + parsed_start.minute
        duration = int(duration or 60)
        labels = [f"{(start_minutes + index * duration) // 60:02d}:{(start_minutes + index * duration) % 60:02d}"
                  for index in range(max(1, min(int(count or 8), 14)))]
        bind.execute(sa.update(timetables).where(timetables.c.id == timetable_id).values(period_labels=labels))


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    timetable_columns = {column["name"] for column in inspector.get_columns("timetables")}
    institution_columns = {column["name"] for column in inspector.get_columns("institutions")}
    if "period_labels" in timetable_columns:
        op.drop_column("timetables", "period_labels")
    if "timetable_period_minutes" in institution_columns:
        op.drop_column("institutions", "timetable_period_minutes")
    if "timetable_period_start" in institution_columns:
        op.drop_column("institutions", "timetable_period_start")
