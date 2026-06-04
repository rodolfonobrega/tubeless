"""Add content_hash to embeddings table for caching.

Revision ID: 005
Revises: 004
Create Date: 2025-06-03 23:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "embeddings",
        sa.Column("content_hash", sa.String(length=64), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("embeddings", "content_hash")
