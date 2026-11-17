"""详情缓存：正文长 TTL + 负缓存 + 单飞，views 不进来。

为什么 views 不进缓存：它是一个持续变化的计数器，缓存它只会得到
"冻结的数字"或"回填后倒退"。views 统一走 cache.view_counter。
"""

import asyncio
import logging
import random

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from cache import lock, news_cache
from curd import news as news_crud
from utils.metrics import CACHE_REQUESTS

logger = logging.getLogger(__name__)

_LOCK_KEY = "lock:news:detail:{}"
_LOCK_TTL = 5

# 没抢到锁时等赢家写缓存的退避序列：0.05+0.1+0.2+0.4+0.8+1.0 ≈ 2.55 秒。
# 旧实现是固定 10×50ms=0.5s：数据库一慢于 0.5s，所有等待者就同时回源，
# 锁只是把雪崩推迟了半秒。每档再加 ±20% 抖动，避免等待者同一刻醒来。
_WAIT_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8, 1.0)

# 区分"退避窗口用完"和"缓存里真的存了 None"的内部哨兵
_MISS = object()


def _payload(row) -> dict:
    """ORM 行 → 响应/缓存共用的正文字段，不含 views。"""
    return jsonable_encoder(
        {
            "id": row.id,
            "title": row.title,
            "author": row.author,
            "image": row.image,
            "publishTime": row.publish_time,
            "categoryId": row.category_id,
            "content": row.content,
            "sourceUrl": row.source_url,
        }
    )


async def _wait_for_cache(news_id: int):
    """等赢家把缓存写好；返回 (payload, known_db_views, status)，等不到才返回 _MISS。

    先立刻读一次（赢家可能刚好写完），再按退避序列读。
    退避比固定间隔多花几倍时间，但换来的是"数据库慢的时候等待者不集体回源"。
    """
    for delay in (0.0, *_WAIT_DELAYS):
        if delay:
            await asyncio.sleep(delay * random.uniform(0.8, 1.2))
        cached = await news_cache.get_cache_detail(news_id)
        if cached == news_cache.NULL_MARK:
            return None, None, "NEGATIVE"
        if cached is not None:
            return cached, None, "HIT"
    return _MISS


async def _load(db: AsyncSession, news_id: int) -> tuple[dict | None, int | None, str]:
    """读详情，返回 (payload, known_db_views, status)。

    - payload 为 None 表示文章不存在（已经写了负缓存）；
    - known_db_views 只在这次真的查了库时才有值，给浏览量回填用；
    - status 是本次请求的缓存状态：HIT / NEGATIVE / MISS，只用于指标和响应头。
    """
    cached = await news_cache.get_cache_detail(news_id)
    if cached == news_cache.NULL_MARK:
        return None, None, "NEGATIVE"
    if cached is not None:
        return cached, None, "HIT"

    lock_key = _LOCK_KEY.format(news_id)
    token = await lock.acquire(lock_key, ttl=_LOCK_TTL)
    if token is not None:
        try:
            # 双重检查：等锁期间别人可能已经把缓存写好了
            cached = await news_cache.get_cache_detail(news_id)
            if cached == news_cache.NULL_MARK:
                return None, None, "NEGATIVE"
            if cached is not None:
                return cached, None, "HIT"

            row = await news_crud.get_news_detail(db, news_id)
            if row is None:
                await news_cache.set_cache_detail_null(news_id)
                return None, None, "MISS"

            payload = _payload(row)
            await news_cache.set_cache_detail(news_id, payload)
            return payload, row.views, "MISS"
        finally:
            await lock.release(lock_key, token)

    # 没抢到锁：等赢家写完缓存。退避窗口约 2.55s，覆盖绝大多数慢查询。
    waited = await _wait_for_cache(news_id)
    if waited is not _MISS:
        return waited

    # 等不到（DB 比退避窗口还慢、缓存写失败、Redis 慢）：自己回源兜底，
    # 不能把请求拖成 500。代价是极端情况下仍会有重复回源，这是有意的取舍。
    row = await news_crud.get_news_detail(db, news_id)
    if row is None:
        await news_cache.set_cache_detail_null(news_id)
        return None, None, "MISS"
    return _payload(row), row.views, "MISS"


async def load(db: AsyncSession, news_id: int) -> tuple[dict | None, int | None, str]:
    """读详情，并在唯一出口记录一次缓存指标。

    拆成 _load + 外壳，是为了不管走哪条 return 都只记一次；
    如果把 inc() 散在 _load 的每个 return 前面，很容易漏记或重复记。
    """
    payload, known_views, status = await _load(db, news_id)
    CACHE_REQUESTS.labels(kind="detail", result=status.lower()).inc()
    return payload, known_views, status
