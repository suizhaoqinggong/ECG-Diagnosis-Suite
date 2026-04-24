"""add chat message title"""

from alembic import op
import sqlalchemy as sa


revision = "002_add_chat_message_title"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("title", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "title")
