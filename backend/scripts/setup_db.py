"""Database setup script: creates all tables and applies migrations."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.environ["DATABASE_URL"]


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Import models so metadata is populated
    from app.models.orm import (  # noqa: F401
        Project, Video, Transcript, TranscriptChunk,
        Embedding, VideoSummary, ConsolidatedSummary,
        ChatSession, ChatMessage,
    )
    from app.models.orm.base import BaseModel

    async with engine.begin() as conn:
        # pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Create all tables from ORM metadata
        await conn.run_sync(BaseModel.metadata.create_all)

        # Migration patch: add source_type and contextual_content to transcript_chunks if missing
        await conn.execute(text("""
            ALTER TABLE transcript_chunks 
            ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'transcript'
        """))
        await conn.execute(text("""
            ALTER TABLE transcript_chunks 
            ADD COLUMN IF NOT EXISTS contextual_content TEXT NULL
        """))

        # Migration patch: add source_type to embeddings if missing
        await conn.execute(text("""
            ALTER TABLE embeddings 
            ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) NOT NULL DEFAULT 'transcript_chunk'
        """))
        await conn.execute(text("""
            ALTER TABLE embeddings 
            ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64) NULL
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_embeddings_content_hash ON embeddings (content_hash)
        """))

        # FTS index from migration 002 (idempotent)
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_transcript_chunks_fts
            ON transcript_chunks
            USING GIN (to_tsvector('simple', content))
        """))

    print("Database setup complete.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
