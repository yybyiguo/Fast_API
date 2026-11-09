"""add rss module

Revision ID: c3f1a9d2b7e4
Revises: 1b403e13c5ac
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c3f1a9d2b7e4"
down_revision: Union[str, Sequence[str], None] = "1b403e13c5ac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rss_feeds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, comment="源名称"),
        sa.Column("url", sa.String(500), nullable=False, comment="Feed URL"),
        sa.Column("site_url", sa.String(500), nullable=True, comment="站点首页"),
        sa.Column("category_id", sa.Integer(), nullable=False, comment="映射到哪个分类"),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
            comment="是否启用",
        ),
        sa.Column(
            "fetch_interval",
            sa.Integer(),
            server_default=sa.text("900"),
            nullable=False,
            comment="抓取间隔(秒)",
        ),
        sa.Column("last_fetch_at", sa.DateTime(), nullable=True, comment="上次抓取时间"),
        sa.Column("last_status", sa.String(20), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("etag", sa.String(255), nullable=True),
        sa.Column("last_modified", sa.String(100), nullable=True),
        sa.Column("create_time", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("update_time", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["news_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", name="uk_rss_feed_url"),
        mysql_charset="utf8mb4",
    )

    op.add_column("news", sa.Column("feed_id", sa.Integer(), nullable=True, comment="来源RSS源"))
    op.add_column(
        "news",
        sa.Column("guid_hash", sa.String(64), nullable=True, comment="RSS条目去重哈希"),
    )
    op.add_column(
        "news",
        sa.Column("source_url", sa.String(1000), nullable=True, comment="原文链接"),
    )
    op.alter_column(
        "news",
        "image",
        existing_type=sa.String(255),
        type_=sa.String(1000),
        existing_comment="封面图片URL",
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_news_feed", "news", "rss_feeds", ["feed_id"], ["id"], ondelete="SET NULL"
    )
    op.create_unique_constraint("uk_news_feed_guid", "news", ["feed_id", "guid_hash"])


def downgrade() -> None:
    op.drop_constraint("uk_news_feed_guid", "news", type_="unique")
    op.drop_constraint("fk_news_feed", "news", type_="foreignkey")
    op.alter_column(
        "news",
        "image",
        existing_type=sa.String(1000),
        type_=sa.String(255),
        existing_comment="封面图片URL",
        existing_nullable=True,
    )
    op.drop_column("news", "source_url")
    op.drop_column("news", "guid_hash")
    op.drop_column("news", "feed_id")
    op.drop_table("rss_feeds")
