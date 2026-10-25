from datetime import datetime

from pydantic import Field
from sqlalchemy import DateTime, Index, Integer, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from models.base import Base,updatetimemixin

# class Base(DeclarativeBase):
#     __abstract__ = True

#     update_time: Mapped[datetime] = mapped_column(
#         DateTime, default=func.now(), onupdate=func.now()
#     )


class History(Base,updatetimemixin):
    __tablename__ = "history"
    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="uq_history_user_news"),
        Index("idx_history_user_id", "user_id"),
        Index("idx_history_news_id", "news_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="新闻id")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户id")
