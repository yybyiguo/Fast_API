"""测试公共设施：测试库重建、HTTP 客户端、数据清理。

每次会话开始时：
1. 校验库名，拒绝在业务库上跑；
2. DROP + CREATE 测试库；
3. 用 Alembic 迁移到 head —— 顺便验证迁移脚本本身没坏。

每个测试前后 TRUNCATE 业务表，并断开 Redis（缓存/浏览量），
保证接口测试不依赖外部服务、测试之间互不污染。
"""

import logging
import os
from datetime import datetime
from pathlib import Path

# 库名必须在 import config.db_config 之前落进环境变量：
# Settings 在 import 那一刻就实例化，DB_URL 也是那时拼好的。
TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "toutiao_test")
if TEST_DB_NAME in {"", "test", "toutiao", "mysql", "information_schema"}:
    raise RuntimeError(f"拒绝在业务库上跑测试: {TEST_DB_NAME!r}")

os.environ["DB_NAME"] = TEST_DB_NAME
# 测试不写 logs/app.log：CI 和沙箱里日志目录可能不可写
os.environ["LOG_TO_FILE"] = "0"

from collections.abc import AsyncIterator, Iterator  # noqa: E402

import pymysql  # noqa: E402
import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from alembic import command  # noqa: E402
from config.db_config import DB_URL, get_db, settings  # noqa: E402
from main import app  # noqa: E402
from models.news import Category, News  # noqa: E402

# config/db_config.py 里是 create_async_engine(echo=True)，不压日志，测试输出会被 SQL 淹没。
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# 启动前就失败，比跑完第一个测试才报错好。
assert f"/{TEST_DB_NAME}?" in DB_URL, f"测试库配置错误，DB_URL 未指向 {TEST_DB_NAME}: {DB_URL}"

BACKEND_DIR = Path(__file__).resolve().parent

BUSINESS_TABLES = (
    "favorite",
    "history",
    "news",
    "rss_feeds",
    "news_categories",
    "user_token",
    "user",
)


def _connect_server() -> pymysql.connections.Connection:
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        charset="utf8mb4",
        autocommit=True,
    )
    # 测试库可能被 IDE / 数据库客户端开着事务。MySQL 的元数据锁默认几乎无限等，
    # DROP/TRUNCATE 会挂几个小时；设短超时，让它快速报错，方便定位是谁占着库。
    with conn.cursor() as cur:
        cur.execute("SET SESSION lock_wait_timeout = 10")
        cur.execute("SET SESSION innodb_lock_wait_timeout = 10")
    return conn


# 同一个测试库同一时刻只允许一个 pytest 进程使用。
# 否则两个进程会互相 DROP/TRUNCATE，表现为随机的 500、Unknown table、
# 主键冲突——看起来像业务代码坏了，实际是测试环境自己打架。
_LOCK_NAME = f"{TEST_DB_NAME}:pytest"
_LOCK_TIMEOUT = 180
_lock_conn = None


def _acquire_session_lock() -> None:
    global _lock_conn
    _lock_conn = _connect_server()
    try:
        with _lock_conn.cursor() as cur:
            cur.execute("SELECT IS_USED_LOCK(%s)", (_LOCK_NAME,))
            if cur.fetchone()[0] is not None:
                print(
                    f"另一个 pytest 正在使用 {TEST_DB_NAME}，等它结束后继续……",
                    flush=True,
                )

            cur.execute("SELECT GET_LOCK(%s, %s)", (_LOCK_NAME, _LOCK_TIMEOUT))
            if cur.fetchone()[0] != 1:
                raise RuntimeError(
                    f"等待 {TEST_DB_NAME} 的测试锁超时（{_LOCK_TIMEOUT}s）。"
                    "确认没有其它 pytest / IDE 自动测试正在跑。"
                )
    except Exception:
        _lock_conn.close()
        _lock_conn = None
        raise


def _release_session_lock() -> None:
    global _lock_conn
    if _lock_conn is None:
        return
    try:
        with _lock_conn.cursor() as cur:
            cur.execute("SELECT RELEASE_LOCK(%s)", (_LOCK_NAME,))
    finally:
        _lock_conn.close()
        _lock_conn = None


def _reset_database() -> None:
    """DROP/CREATE 测试库，再用 Alembic 建表。"""
    conn = _connect_server()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{TEST_DB_NAME}`")
            cur.execute(
                f"CREATE DATABASE `{TEST_DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
    finally:
        conn.close()

    ini_path = BACKEND_DIR / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def prepared_database() -> Iterator[None]:
    _acquire_session_lock()
    try:
        _reset_database()
        yield
    finally:
        _release_session_lock()


# 测试专用引擎。NullPool = 每次用完立刻断开，绝不缓存连接。
# 缓存连接会在“上一个测试的 event loop 已关闭”之后被下一个测试复用，
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


@pytest.fixture
def session_factory():
    """需要多个并发会话时用（例如验证 RSS 并发去重）。"""
    return TestSessionLocal


async def _truncate_all() -> None:
    """清空业务表；每次清之前都复核库名，防止误连真库。"""
    async with test_engine.begin() as conn:
        await conn.execute(text("SET SESSION lock_wait_timeout = 10"))
        await conn.execute(text("SET SESSION innodb_lock_wait_timeout = 10"))
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


@pytest.fixture(autouse=True)
def disable_external_services(monkeypatch) -> None:
    """接口测试不依赖 Redis：缓存直接 miss，浏览量计数不落库。

    注意 curd/news.py 是 from cache.news_cache import ... 的直接绑定，
    所以必须 patch curd.news.<name>，只 patch cache.news_cache 不生效。
    """

    async def _miss(*args, **kwargs):
        return None

    async def _noop(*args, **kwargs):
        return None

    async def _zero(*args, **kwargs):
        return 0

    monkeypatch.setattr("curd.news.get_cache_news_list", _miss)
    monkeypatch.setattr("curd.news.set_cache_news_list", _noop)
    monkeypatch.setattr("curd.news.get_cache_categories", _miss)
    monkeypatch.setattr("curd.news.set_cache_categories", _noop)
    monkeypatch.setattr("cache.view_counter.increase", _noop)
    monkeypatch.setattr("cache.view_counter.pending", _zero)


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


@pytest.fixture
async def category(db) -> Category:
    """一条测试分类。"""
    item = Category(name="测试分类", sort_order=1)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@pytest.fixture
def make_news(db, category):
    """造新闻的工厂：await make_news(title="x")，字段可覆盖。"""

    async def _make(**overrides) -> News:
        data = {
            "title": "测试新闻",
            "content": "测试正文",
            "category_id": category.id,
            "views": 0,
            "publish_time": datetime.now(),
        }
        data.update(overrides)

        news = News(**data)
        db.add(news)
        await db.commit()
        await db.refresh(news)
        return news

    return _make
