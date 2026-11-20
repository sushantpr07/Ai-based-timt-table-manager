"""Add the HOD timetable approval lifecycle.

Revision ID: 0003_timetable_approvals
Revises: 0002_email_verification
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_timetable_approvals"
down_revision = "0002_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("timetables")}
    new_columns = [
        sa.Column("approval_status", sa.String(length=20), nullable=False, server_default=sa.text("'not_requested'")),
        sa.Column("approval_requested_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_reviewed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_note", sa.String(length=500), nullable=True),
    ]
    for column in new_columns:
        if column.name not in columns:
            op.add_column("timetables", column)


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("timetables")}
    for name in ("approval_note", "approval_reviewed_at", "approval_requested_at",
                 "approval_reviewed_by", "approval_requested_by", "approval_status"):
        if name in columns:
            op.drop_column("timetables", name)
