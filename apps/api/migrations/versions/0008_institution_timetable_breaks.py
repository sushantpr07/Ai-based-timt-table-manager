"""Add recurring institution-wide timetable breaks.

Revision ID: 0008_institution_timetable_breaks
Revises: 0007_timetable_period_length
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008_institution_timetable_breaks"
down_revision = "0007_timetable_period_length"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("institutions")}
    if "timetable_breaks" not in columns:
        op.add_column("institutions", sa.Column("timetable_breaks", sa.JSON(), nullable=False,
                                                   server_default=sa.text("'[]'")))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("institutions")}
    if "timetable_breaks" in columns:
        op.drop_column("institutions", "timetable_breaks")
