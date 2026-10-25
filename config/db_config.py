
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

from pathlib import Path

# .env 的位置相对于本文件是固定的：backend/.env
# 不能写相对路径 ".env" —— 那是相对【当前工作目录】找的，
# 换一个目录启动（VS Code 发现测试、计划任务、别的服务）就读不到，报 Field required。
BASE_DIR = Path(__file__).resolve().parent.parent

# 配置类：定义所有环境变量

class Settings(BaseSettings):
    # 数据库配置
    db_host: str
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str

    redis_host:str
    redis_port:int=6379
    redis_db:int=0
    redis_decode_responses:bool=True

    # 运行环境开关：dev 打开 SQL echo / 详细异常，prod 全部关掉
    debug: bool = True


    # 读取 .env 文件
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
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
async_engine = create_async_engine(DB_URL, echo=settings.debug, pool_size=10, max_overflow=20)
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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
