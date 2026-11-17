"""add category views index

Revision ID: f9a1b2c3d4e5
Revises: e6f7a8b9c0d1

详情页的“相关推荐”是：
    WHERE category_id = ? AND id <> ? ORDER BY views DESC LIMIT 10

只有 (category_id, publish_time) 索引时，MySQL 会把整个分类的行取出来再
filesort，分类越大越慢；LIMIT 10 并不能让排序提前结束。
补 (category_id, views) 后可以沿索引在分类内按 views 倒序读，取满 10 行就停。
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f9a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_cat_views", "news", ["category_id", "views"])


def downgrade() -> None:
    op.drop_index("idx_cat_views", table_name="news")
