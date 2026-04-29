"""Add health jobs, assets, and findings tables

Revision ID: 003_add_health_jobs
Revises: 002_add_chat_message_title
Create Date: 2026-04-29 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_health_jobs"
down_revision = "002_add_chat_message_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_jobs_user_created", "health_jobs", ["user_id", "created_at"])
    op.create_table(
        "health_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("health_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
    )
    op.create_table(
        "health_findings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("health_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("action_hint", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("health_findings")
    op.drop_table("health_assets")
    op.drop_index("ix_health_jobs_user_created", table_name="health_jobs")
    op.drop_table("health_jobs")
