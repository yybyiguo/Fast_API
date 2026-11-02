from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, createtimemixin
from models.news import News
from models.user import User

# class Base(DeclarativeBase):
#     pass


class Favorite(Base, createtimemixin):
    """
    收藏表ORM模型
    """

    __tablename__ = "favorite"

    # 创建索引
    # UniqueConstraint: 唯一约束，当前用户，当前新闻，只能收藏一次
    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="uq_user_favorite"),
        Index("idx_favorite_user_idx", "user_id"),
        Index("idx_favorite_news_idx", "news_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏ID")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(User.id), nullable=False, comment="用户"
    )
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey(News.id), nullable=False, comment="新")
    # created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<Favorite(id={self.id}, user_id={self.user_id}, news_id={self.news_id}, create_time={self.create_time})>"
