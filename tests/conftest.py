"""测试公共设施：测试库引擎、HTTP 客户端、数据清理。"""

import logging
import os

# 测试库名。必须在 import config.db_config 之前落到环境变量里：
# Settings 在 import 那一刻就会实例化，DB_URL 也是那时拼好的。
TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "toutiao_test")

# 用赋值而不是 setdefault：如果开发者 shell 里已经 export DB_NAME=toutiao，
# setdefault 不会覆盖，整轮测试就会跑在真库上。
os.environ["DB_NAME"] = TEST_DB_NAME

from typing import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.db_config import DB_URL, get_db
from main import app

# config/db_config.py 里是 create_async_engine(echo=True)，不压日志，测试输出会被 SQL 淹没。
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# 启动前就失败，比跑完第一个测试才报错好。
assert f"/{TEST_DB_NAME}?" in DB_URL, (
    f"测试库配置错误，DB_URL 未指向 {TEST_DB_NAME}: {DB_URL}"
)

BUSINESS_TABLES = (
    "favorite",
    "history",
    "news",
    "news_categories",
    "user_token",
    "user",
)


# 测试专用引擎。NullPool = 每次用完立刻断开，绝不缓存连接。
# 缓存连接会在"上一个测试的 event loop 已关闭"之后被下一个测试复用，
# 报 AttributeError: 'NoneType' object has no attribute 'send'（Windows 上尤其常见）。
test_engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)


TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncIterator[AsyncSession]:
    """替换 app 的 get_db：接口里所有 Depends(get_db) 都会拿到测试库的会话。

    注意这里【不 commit】——你的 router 里自己 commit。测试环境的职责只是提供会话。
    """
    async with TestSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """不启动 uvicorn、不占端口，直接把请求喂给 app 对象。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def strict_client() -> AsyncIterator[AsyncClient]:
    """不把服务端异常重新抛给测试，这样才能拿到真实的 500 响应。"""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    """直接查库用：绑定 NullPool 的测试引擎，和接口用的是同一个库。

    不要自己 import config.db_config.async_engine —— 那是 app 的连接池（QueuePool），
    而 ASGITransport 不跑 lifespan，池里的连接不会被 dispose，可能跨 event loop 复用。
    """
    async with TestSessionLocal() as session:
        yield session


async def _truncate_all() -> None:
    """清空业务表；每次清之前都复核库名，防止误连真库。"""
    async with test_engine.begin() as conn:
        dbname = (await conn.execute(text("SELECT DATABASE()"))).scalar_one()
        if dbname != TEST_DB_NAME:
            raise RuntimeError(f"拒绝清理非测试库: {dbname}")

        # MySQL 里有外键的表必须先关 FOREIGN_KEY_CHECKS 才能随便 TRUNCATE。
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in BUSINESS_TABLES:
            await conn.execute(text(f"TRUNCATE TABLE `{table}`"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


@pytest.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    """每个测试前后都清空业务表，测试之间互不影响。

    setup 也清：上一轮如果被强杀，teardown 没跑到，第一次测试就会看到脏数据。
    TRUNCATE 会重置自增 id，所以每次测试看到的 id 都从 1 开始。
    """
    await _truncate_all()

    yield

    await _truncate_all()


@pytest.fixture
async def auth(client) -> dict:
    """注册并登录一个用户，返回可直接用于请求的凭证。"""
    response = await client.post(
        "/api/user/register",
        json={"username": "alice", "password": "secret123"},
    )
    assert response.status_code == 200, response.text  # 准备阶段就失败，比后面莫名其妙强

    data = response.json()["data"]
    token = data["token"]

    return {
        "username": "alice",
        "password": "secret123",
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }
