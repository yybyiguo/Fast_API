"""add category publish index

Revision ID: d4e5f6a7b8c9
Revises: c3f1a9d2b7e4
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3f1a9d2b7e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 列表接口改成 ORDER BY publish_time DESC 后，避免 10 万行走 filesort
    op.create_index("idx_cat_publish", "news", ["category_id", "publish_time"])


def downgrade() -> None:
    op.drop_index("idx_cat_publish", table_name="news")
