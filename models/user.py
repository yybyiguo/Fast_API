from typing import Optional
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Text, func, DateTime, String, DECIMAL, select, delete, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, createtimemixin, updatetimemixin
from schemas.users import Gender


class User(Base, createtimemixin,updatetimemixin):
    __tablename__ = 'user'

    __table_args__ = (
        Index('username_UNIQUE', 'username'),
        Index('phone_UNIQUE', 'phone'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码（加密存储）")
    nickname: Mapped[Optional[str]] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), comment="头像URL", default=r'file\p1.jpg')
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), comment="性别", default=Gender.unknown)
    bio: Mapped[Optional[str]] = mapped_column(String(500), comment="个人简介", default='这个人很懒，什么都没说')
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, comment="手机号")
    # created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), comment="创建时间")
    # updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), onupdate=func.now(), comment="更新时间")


class UserToken(Base):
    __tablename__='user_token'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False,autoincrement=True, comment="用户ID")
    token: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="token")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
