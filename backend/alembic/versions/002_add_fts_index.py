"""Add GIN full-text search index on transcript_chunks.content.

Revision ID: 002
Revises: 001
Create Date: 2026-05-08
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_transcript_chunks_fts
        ON transcript_chunks
        USING GIN (to_tsvector('simple', content))
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_transcript_chunks_fts")
