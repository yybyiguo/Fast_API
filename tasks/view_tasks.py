"""把 Redis 里累计的浏览量批量写回 MySQL。

核心难点：同步过程中可能又有新浏览进来。
所以顺序必须是【先从脏集合移除，再原子取走计数】，否则新增量会被误删。
"""

import asyncio
import logging

from redis.asyncio import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.db_config import DB_URL, settings
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

DIRTY_SET = "news:views:dirty"
VIEW_KEY = "news:views:{news_id}"


async def _flush_once() -> int:
    # worker 里每次任务都通过 asyncio.run 新建事件循环。
    # 所以 Redis 客户端和数据库引擎都在这里就地创建、用完就关，
    # 绝不能让连接跨事件循环复用（否则会报 "attached to a different loop"）。
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=settings.redis_decode_responses,
        socket_connect_timeout=1,
        socket_timeout=1,
        retry=Retry(NoBackoff(), 0),
    )
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    try:
        dirty = await client.smembers(DIRTY_SET)
        if not dirty:
            return 0

        deltas: dict[int, int] = {}
        for raw in dirty:
            news_id = int(raw)
            # ① 先移出脏集合：之后如果又有人浏览，会重新 SADD
            await client.srem(DIRTY_SET, news_id)
            # ② GETDEL 原子地"取出并删除"，不会和并发的 INCR 打架
            delta = await client.getdel(VIEW_KEY.format(news_id=news_id))
            if delta:
                deltas[news_id] = int(delta)

        if not deltas:
            return 0

        async with session_factory() as db:
            for news_id, delta in deltas.items():
                await db.execute(
                    text("UPDATE news SET views = views + :delta WHERE id = :news_id"),
                    {"delta": delta, "news_id": news_id},
                )
            await db.commit()

        total = sum(deltas.values())
        logger.info("浏览量落库 news_ids=%s 共 %s 次", list(deltas), total)
        return total
    finally:
        try:
            await client.aclose()
        except Exception:
            logger.exception("关闭 Redis 客户端失败")
        try:
            await engine.dispose()
        except Exception:
            logger.exception("释放 DB 引擎失败")


@celery_app.task(name="tasks.view_tasks.flush_view_counts")
def flush_view_counts() -> int:
    try:
        return asyncio.run(_flush_once())
    except Exception:
        # 定时任务失败不能让 worker 崩掉，下一轮还会再来
        logger.exception("浏览量落库失败")
        return 0
