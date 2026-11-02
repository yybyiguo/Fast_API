from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, createtimemixin, updatetimemixin


class news_Base(Base, updatetimemixin, createtimemixin):
    __abstract__ = True


class Category(news_Base):
    __tablename__ = "news_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="排序")

    def __repr__(self):
        return f"<Category(id={self.id},name={self.name},sort_order={self.sort_order})>"


class News(news_Base):
    __tablename__ = "news"

    # 创建索引：提升查询速度
    __table_args__ = (
        Index("fk_news_category_idx", "category_id"),
        Index("idx_publish_time", "publish_time"),
        Index("idx_cat_publish", "category_id", "publish_time"),
        UniqueConstraint("feed_id", "guid_hash", name="uk_news_feed_guid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="新闻ID")
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="新闻标题")
    description: Mapped[str | None] = mapped_column(String(500), comment="新闻简介")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[str | None] = mapped_column(String(1000), comment="封面图片URL")
    author: Mapped[str | None] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("news_categories.id"),
        nullable=False,
    )
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览量")
    is_top: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0"), comment="是否置顶"
    )
    publish_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="发布时间"
    )
    feed_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("rss_feeds.id", ondelete="SET NULL"), comment="来源RSS源"
    )
    guid_hash: Mapped[str | None] = mapped_column(String(64), comment="RSS条目去重哈希")
    source_url: Mapped[str | None] = mapped_column(String(1000), comment="原文链接")

    def __repr__(self):
        return f"<News(id={self.id}, title='{self.title}', views={self.views})>"
