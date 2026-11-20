"""Snapshot period length on each timetable version.

Revision ID: 0007_timetable_period_length
Revises: 0006_timetable_bell_times
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_timetable_period_length"
down_revision = "0006_timetable_bell_times"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("timetables")}
    period_minutes_added = "period_minutes" not in columns
    if period_minutes_added:
        op.add_column("timetables", sa.Column("period_minutes", sa.Integer(), nullable=False,
                                                  server_default=sa.text("60")))
    if not period_minutes_added:
        return

    institutions = sa.table("institutions", sa.column("id", sa.Uuid()),
                            sa.column("timetable_period_minutes", sa.Integer()))
    timetables = sa.table("timetables", sa.column("id", sa.Uuid()),
                          sa.column("institution_id", sa.Uuid()), sa.column("period_minutes", sa.Integer()),
                          sa.column("period_labels", sa.JSON()))
    rows = bind.execute(sa.select(timetables.c.id, institutions.c.timetable_period_minutes,
                                 timetables.c.period_labels)
                        .select_from(timetables.join(institutions, timetables.c.institution_id == institutions.c.id))).all()
    for timetable_id, institution_minutes, period_labels in rows:
        if period_labels and len(period_labels) > 1:
            first_hour, first_minute = (int(part) for part in period_labels[0].split(":"))
            next_hour, next_minute = (int(part) for part in period_labels[1].split(":"))
            period_minutes = (next_hour * 60 + next_minute) - (first_hour * 60 + first_minute)
        else:
            period_minutes = institution_minutes
        bind.execute(sa.update(timetables).where(timetables.c.id == timetable_id)
                     .values(period_minutes=int(period_minutes or 60)))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("timetables")}
    if "period_minutes" in columns:
        op.drop_column("timetables", "period_minutes")
