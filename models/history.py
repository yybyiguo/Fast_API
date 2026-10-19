from datetime import datetime

from pydantic import Field
from sqlalchemy import DateTime, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    __abstract__ = True

    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class History(Base):
    __tablename__ = "history"
    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="user_news_unique"),
        Index("fk_favorite_user_idx", "user_id"),
        Index("fk_favorite_news_idx", "news_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="新闻id")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户id")
