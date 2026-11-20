"""Add durable email verification state.

Revision ID: 0002_email_verification
Revises: 0001_initial
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_email_verification"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "email_verified" not in {column["name"] for column in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    if not inspector.has_table("email_verification_tokens"):
        op.create_table(
            "email_verification_tokens",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("email_verification_tokens"):
        indexes = {index["name"] for index in inspector.get_indexes("email_verification_tokens")}
        if "ix_email_verification_tokens_user_id" in indexes:
            op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
        op.drop_table("email_verification_tokens")
    if "email_verified" in {column["name"] for column in inspector.get_columns("users")}:
        op.drop_column("users", "email_verified")
