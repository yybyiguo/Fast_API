"""把 Redis 里的浏览量绝对值批量写回 MySQL。

和旧的"增量 + GETDEL"相比，这里只做一件事：读当前总数、覆盖写回。
覆盖是幂等的——任务重跑、worker 崩了重投，结果都一样；
读到的值如果在这期间又涨了，比较后不会从脏集合里移除，下一轮自然追上。
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.cache_config import new_client
from config.db_config import DB_URL
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

DIRTY_SET = "news:views:dirty"
VIEW_KEY = "news:views:total:{news_id}"

# 落库成功后再清脏标记，但只清"值没变"的那条：
# 如果读完之后又有人浏览，计数已经变大，留着下一轮再写一次。
_COMPARE_AND_CLEAR = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('SREM', KEYS[2], ARGV[2])
end
return 0
"""


async def _flush_once() -> int:
    # worker 里每次任务都通过 asyncio.run 新建事件循环。
    # 所以 Redis 客户端和数据库引擎都在这里就地创建、用完就关，
    # 绝不能让连接跨事件循环复用（否则会报 "attached to a different loop"）。
    client = new_client()
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    try:
        dirty = await client.smembers(DIRTY_SET)
        ids = sorted({int(raw) for raw in dirty})
        if not ids:
            return 0

        raw_values = await client.mget([VIEW_KEY.format(news_id=i) for i in ids])
        values = {
            news_id: int(raw)
            for news_id, raw in zip(ids, raw_values, strict=False)
            if raw is not None
        }
        missing = [news_id for news_id in ids if news_id not in values]
        if missing:
            # 文章被删、或计数被淘汰：脏标记留着也没法落库，直接清掉
            await client.srem(DIRTY_SET, *missing)
        if not values:
            return 0

        async with session_factory() as db:
            for news_id, total in values.items():
                await db.execute(
                    # GREATEST：浏览量是单调递增的，两个 flush 重叠时
                    # 旧快照后写不能把数据库的数字盖回去（否则会永久少记）。
                    text("UPDATE news SET views = GREATEST(views, :total) WHERE id = :news_id"),
                    {"total": total, "news_id": news_id},
                )
            await db.commit()

        for news_id, total in values.items():
            await client.eval(
                _COMPARE_AND_CLEAR,
                2,
                VIEW_KEY.format(news_id=news_id),
                DIRTY_SET,
                str(total),
                str(news_id),
            )

        logger.info("浏览量落库 articles=%s", len(values))
        return len(values)
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
