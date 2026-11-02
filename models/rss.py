from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, createtimemixin, updatetimemixin


class RssFeed(Base, createtimemixin, updatetimemixin):
    __tablename__ = "rss_feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="源名称")
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, comment="Feed URL")
    site_url: Mapped[str | None] = mapped_column(String(500), comment="站点首页")
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("news_categories.id"),
        nullable=False,
        comment="映射到哪个分类",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        comment="是否启用",
    )
    fetch_interval: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=900,
        server_default=text("900"),
        comment="抓取间隔(秒)",
    )
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime, comment="上次抓取时间")
    last_status: Mapped[str | None] = mapped_column(String(20), comment="ok/not_modified/error")
    last_error: Mapped[str | None] = mapped_column(String(500), comment="最近一次错误")
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="连续失败次数",
    )
    etag: Mapped[str | None] = mapped_column(String(255), comment="条件请求 ETag")
    last_modified: Mapped[str | None] = mapped_column(String(100), comment="条件请求 Last-Modified")

    def __repr__(self) -> str:
        return f"<RssFeed(id={self.id}, name='{self.name}')>"
