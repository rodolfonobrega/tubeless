"""Add chapter_title and source_type to transcript_chunks; restructure consolidated_summaries.

Revision ID: 001
Revises:
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # transcript_chunks: new fields
    op.add_column("transcript_chunks", sa.Column("chapter_title", sa.String(500), nullable=True))
    op.add_column("transcript_chunks", sa.Column("source_type", sa.String(20), nullable=False, server_default="transcript"))

    # consolidated_summaries: drop old schema, add new fields
    # (safe because data is regenerated on each project processing)
    with op.batch_alter_table("consolidated_summaries") as batch_op:
        # Remove old columns that don't match the service layer
        for col in ["title", "key_topics", "synthesis_notes", "token_count", "source_video_count"]:
            try:
                batch_op.drop_column(col)
            except Exception:
                pass  # column may not exist

        # Rename content -> summary_text if needed
        try:
            batch_op.alter_column("content", new_column_name="summary_text")
        except Exception:
            pass

        # Add new JSON columns
        batch_op.add_column(sa.Column("key_themes", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("consensus_points", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("differing_viewpoints", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("contradictions", sa.JSON(), nullable=True))

        # Add project_id FK if missing
        try:
            batch_op.add_column(sa.Column("project_id", UUID(as_uuid=True), nullable=True))
        except Exception:
            pass


def downgrade() -> None:
    op.drop_column("transcript_chunks", "chapter_title")
    op.drop_column("transcript_chunks", "source_type")
    # consolidated_summaries downgrade intentionally omitted — schema change is destructive
