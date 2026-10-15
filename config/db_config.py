
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException,Request

from pydantic import BaseModel, Field
from sqlalchemy import func, DateTime, String, DECIMAL, select,delete
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# 配置类：定义所有环境变量

class Settings(BaseSettings):
    # 数据库配置
    db_host: str
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str

    # jwt配置示例
    jwt_secret: str
    jwt_expire_minutes: int = 30

    # 读取 .env 文件
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# lru_cache 缓存，全局只实例化一次，性能更好
@lru_cache()
def get_settings():
    return Settings()
settings = get_settings()

DB_URL = (
    f"mysql+aiomysql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}?charset=utf8mb4"
)
#创建连接池
async_engine = create_async_engine(DB_URL, echo=True, pool_size=10, max_overflow=20)
#会话工厂，被使用时会自动向连接池请求一条连接，session是在数据库连接之上的一层
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
