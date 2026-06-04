"""Add contextual_content, source_type, and feedback columns.

Revision ID: 004
Revises: 003
Create Date: 2025-06-03 23:31:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. contextual_content for Contextual Retrieval
    op.add_column(
        "transcript_chunks",
        sa.Column("contextual_content", sa.Text(), nullable=True),
    )

    # 2. source_type for HyPE embeddings
    op.add_column(
        "embeddings",
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="transcript_chunk"),
    )

    # 3. feedback for RAG quality
    op.add_column(
        "chat_messages",
        sa.Column("feedback", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "feedback")
    op.drop_column("embeddings", "source_type")
    op.drop_column("transcript_chunks", "contextual_content")
