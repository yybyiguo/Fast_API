"""name categories after feeds

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9

把“分类1..5”这种占位名字换成源名字，并清掉没有新闻也没有源的空分类。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 先删空分类，避免重名冲突（当前就是 2..5 这四个）
    conn.execute(
        sa.text(
            """
            DELETE c FROM news_categories c
            LEFT JOIN news n ON n.category_id = c.id
            LEFT JOIN rss_feeds f ON f.category_id = c.id
            WHERE n.id IS NULL AND f.id IS NULL
            """
        )
    )

    # 每个源对应的分类改成源名字，首页 tab 直接显示它
    conn.execute(
        sa.text(
            """
            UPDATE news_categories c
            JOIN rss_feeds f ON f.category_id = c.id
            SET c.name = LEFT(f.name, 50)
            """
        )
    )


def downgrade() -> None:
    # 数据迁移不可逆：旧的“分类1..5”名字没有留存
    pass
