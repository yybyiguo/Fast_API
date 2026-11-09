"""add server defaults for timestamp columns

Revision ID: 1b403e13c5ac
Revises: b4554e88ca80
Create Date: 2026-10-23 10:45:07.316423

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b403e13c5ac"
down_revision: Union[str, Sequence[str], None] = "b4554e88ca80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = (
    ("user", "create_time"),
    ("user", "update_time"),
    ("news", "create_time"),
    ("news", "update_time"),
    ("news_categories", "create_time"),
    ("news_categories", "update_time"),
    ("favorite", "create_time"),
    ("history", "update_time"),
)


def upgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(),
            existing_nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )


def downgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(table, column, server_default=None)
