"""RSS 定时抓取任务。

和 view_tasks 一样：每个任务用 asyncio.run 新建事件循环，
数据库引擎和 Redis 客户端都就地创建、用完关闭。
"""

import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from redis.asyncio import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from cache.news_cache import invalidate_news_list
from config.db_config import DB_URL, settings
from models.rss import RssFeed
from services.rss_fetcher import USER_AGENT, fetch_and_store
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

LOCK_KEY = "rss:lock:{feed_id}"
LOCK_TTL = 180
CONCURRENCY = 5


async def _run(feed_id: int | None = None) -> dict:
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    redis_client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
        retry=Retry(NoBackoff(), 0),
    )
    stats = {"due": 0, "inserted": 0, "failed": 0}

    try:
        async with factory() as db:
            stmt = select(
                RssFeed.id,
                RssFeed.last_fetch_at,
                RssFeed.fetch_interval,
                RssFeed.error_count,
            )
            stmt = (
                stmt.where(RssFeed.id == feed_id)
                if feed_id
                else stmt.where(RssFeed.enabled.is_(True))
            )
            rows = (await db.execute(stmt)).all()

        now = datetime.now()

        def _due(row) -> bool:
            if feed_id or row.last_fetch_at is None:
                return True
            # 连续失败按 2 的幂退避，最多 6 小时，避免坏源每 5 分钟撞一次
            delay = min(
                row.fetch_interval * (2 ** min(row.error_count or 0, 4)),
                6 * 3600,
            )
            return row.last_fetch_at + timedelta(seconds=delay) <= now

        due = [row for row in rows if _due(row)]
        stats["due"] = len(due)
        if not due:
            return stats

        semaphore = asyncio.Semaphore(CONCURRENCY)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:

            async def fetch_one(row) -> None:
                async with semaphore:
                    key = LOCK_KEY.format(feed_id=row.id)
                    locked = True
                    try:
                        locked = bool(await redis_client.set(key, "1", nx=True, ex=LOCK_TTL))
                    except Exception:
                        logger.warning("Redis 不可用，跳过抓取锁 feed_id=%s", row.id)
                        locked = True
                    if not locked:
                        return
                    try:
                        async with factory() as db:
                            feed = await db.get(RssFeed, row.id)
                            if feed is None or (feed_id is None and not feed.enabled):
                                return
                            result = await fetch_and_store(db, feed, client)
                            await db.commit()
                            stats["inserted"] += result.inserted
                            if result.status == "error":
                                stats["failed"] += 1
                            if result.inserted:
                                await invalidate_news_list(feed.category_id, client=redis_client)
                    except Exception:
                        logger.exception("RSS 抓取任务异常 feed_id=%s", row.id)
                        stats["failed"] += 1
                    finally:
                        try:
                            await redis_client.delete(key)
                        except Exception:
                            pass

            await asyncio.gather(*(fetch_one(row) for row in due))

        logger.info("RSS 本轮完成 %s", stats)
        return stats
    finally:
        await redis_client.aclose()
        await engine.dispose()


@celery_app.task(name="tasks.rss_tasks.fetch_due_feeds")
def fetch_due_feeds() -> dict:
    try:
        return asyncio.run(_run())
    except Exception:
        logger.exception("RSS 定时抓取失败")
        return {"due": 0, "inserted": 0, "failed": 1}


@celery_app.task(name="tasks.rss_tasks.fetch_feed")
def fetch_feed(feed_id: int) -> dict:
    try:
        return asyncio.run(_run(feed_id))
    except Exception:
        logger.exception("RSS 单源抓取失败 feed_id=%s", feed_id)
        return {"due": 0, "inserted": 0, "failed": 1}
