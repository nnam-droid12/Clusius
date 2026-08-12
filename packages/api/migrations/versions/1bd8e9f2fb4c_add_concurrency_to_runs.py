"""add concurrency to runs

Revision ID: 1bd8e9f2fb4c
Revises: 1d52040960dc
Create Date: 2026-08-12 14:50:31.599813

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1bd8e9f2fb4c"
down_revision: str | None = "1d52040960dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs", sa.Column("concurrency", sa.Integer(), nullable=False, server_default="2")
    )


def downgrade() -> None:
    op.drop_column("runs", "concurrency")
