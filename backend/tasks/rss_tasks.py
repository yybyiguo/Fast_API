"""RSS 定时抓取任务。

和 view_tasks 一样：每个任务用 asyncio.run 新建事件循环，
数据库引擎和 Redis 客户端都就地创建、用完关闭。
"""

import asyncio
import logging
import secrets
import time
from datetime import datetime, timedelta

import httpx
from redis.asyncio import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from cache.news_cache import invalidate_detail_many, invalidate_news_list
from cache.view_counter import delete_many as delete_view_counters
from config.cache_config import new_client
from config.db_config import DB_URL, settings
from models.news import News
from models.rss import RssFeed
from services.rss_fetcher import CST, USER_AGENT, fetch_and_store
from tasks.celery_app import celery_app
from utils.request_context import reset_request_id, set_request_id

logger = logging.getLogger(__name__)

LOCK_KEY = "rss:lock:{feed_id}"
LOCK_TTL = 180
CONCURRENCY = 5
# 只有 token 还是自己的才删，避免 TTL 过期后误删别人的锁
LOCK_RELEASE_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


def _next_delay(fetch_interval: int, error_count: int) -> int:
    """连续失败按 2 的幂退避，最多 6 小时。"""
    return min(fetch_interval * (2 ** min(error_count or 0, 4)), 6 * 3600)


def _is_due(row, now: datetime, force: bool = False) -> bool:
    """判断一个源这一轮是否该抓；force 用于“立即抓取”。"""
    if force or row.last_fetch_at is None:
        return True
    delay = _next_delay(row.fetch_interval, row.error_count)
    return row.last_fetch_at + timedelta(seconds=delay) <= now


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

        now = datetime.now(CST).replace(tzinfo=None)
        due = [row for row in rows if _is_due(row, now, force=bool(feed_id))]
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
                    started = time.perf_counter()
                    key = LOCK_KEY.format(feed_id=row.id)
                    token = secrets.token_hex(8)
                    locked = True
                    try:
                        locked = bool(await redis_client.set(key, token, nx=True, ex=LOCK_TTL))
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
                            # 手动“立即抓取”要强制回源，不能被 304 挡住
                            result = await fetch_and_store(db, feed, client, force=bool(feed_id))
                            await db.commit()
                            stats["inserted"] += result.inserted
                            if result.status == "error":
                                stats["failed"] += 1
                            if result.inserted:
                                await invalidate_news_list(feed.category_id, client=redis_client)
                            logger.info(
                                "RSS feed_id=%s status=%s fetched=%s inserted=%s skipped=%s cost=%.0fms",
                                row.id,
                                result.status,
                                result.fetched,
                                result.inserted,
                                result.skipped,
                                (time.perf_counter() - started) * 1000,
                            )
                    except Exception:
                        logger.exception("RSS 抓取任务异常 feed_id=%s", row.id)
                        stats["failed"] += 1
                    finally:
                        try:
                            # 只删自己加的锁
                            await redis_client.eval(LOCK_RELEASE_LUA, 1, key, token)
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
    token = set_request_id(f"cron-{secrets.token_hex(4)}")
    try:
        return asyncio.run(_run())
    except Exception:
        logger.exception("RSS 定时抓取失败")
        return {"due": 0, "inserted": 0, "failed": 1}
    finally:
        reset_request_id(token)


@celery_app.task(name="tasks.rss_tasks.fetch_feed")
def fetch_feed(feed_id: int, request_id: str | None = None) -> dict:
    # 手动刷新会带 API 的单号；定时任务没有，就自己造一个
    rid = request_id if request_id and request_id != "-" else f"task-{secrets.token_hex(4)}"
    token = set_request_id(rid)
    try:
        return asyncio.run(_run(feed_id))
    except Exception:
        logger.exception("RSS 单源抓取失败 feed_id=%s", feed_id)
        return {"due": 0, "inserted": 0, "failed": 1}
    finally:
        reset_request_id(token)


async def _clean_old(days: int) -> int:
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    client = new_client()
    cutoff = datetime.now(CST).replace(tzinfo=None) - timedelta(days=days)
    total = 0
    try:
        async with factory() as db:
            while True:
                ids = (
                    (
                        await db.execute(
                            text(
                                """
                            SELECT n.id FROM news n
                            WHERE n.feed_id IS NOT NULL
                              AND n.publish_time < :cutoff
                              AND NOT EXISTS (
                                  SELECT 1 FROM favorite f WHERE f.news_id = n.id
                              )
                              AND NOT EXISTS (
                                  SELECT 1 FROM history h WHERE h.news_id = n.id
                              )
                            LIMIT 1000
                            """
                            ),
                            {"cutoff": cutoff},
                        )
                    )
                    .scalars()
                    .all()
                )
                if not ids:
                    break

                categories = (
                    (await db.execute(select(News.category_id).where(News.id.in_(ids)).distinct()))
                    .scalars()
                    .all()
                )
                await db.execute(delete(News).where(News.id.in_(ids)))
                await db.commit()
                total += len(ids)

                # 文章已经删了：列表、详情缓存和计数器都要一起清，
                # 否则缓存还能把已删除的文章返回给用户（点进去才 404）
                for category_id in categories:
                    await invalidate_news_list(category_id, client=client)
                await invalidate_detail_many(ids, client=client)
                await delete_view_counters(ids, client=client)
        return total
    finally:
        try:
            await client.aclose()
        except Exception:
            logger.exception("关闭 Redis 客户端失败")
        await engine.dispose()


@celery_app.task(name="tasks.rss_tasks.clean_old_rss_news")
def clean_old_rss_news() -> int:
    """按天清理老的 RSS 文章；被收藏/历史引用的不删。"""
    days = settings.rss_retention_days
    if days <= 0:
        return 0
    try:
        deleted = asyncio.run(_clean_old(days))
        logger.info("清理 %s 天前的 RSS 文章，删除 %s 条", days, deleted)
        return deleted
    except Exception:
        logger.exception("清理旧 RSS 文章失败")
        return 0
