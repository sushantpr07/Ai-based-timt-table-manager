"""Add per-user in-app notification preferences.

Revision ID: 0004_notification_preferences
Revises: 0003_timetable_approvals
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_notification_preferences"
down_revision = "0003_timetable_approvals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "notification_preferences" not in columns:
        op.add_column("users", sa.Column(
            "notification_preferences", sa.JSON(), nullable=False,
            server_default=sa.text("'{\"schedule_updates\": true, \"approval_updates\": true}'"),
        ))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "notification_preferences" in columns:
        op.drop_column("users", "notification_preferences")
