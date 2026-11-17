"""浏览量计数器：Redis 存绝对值，MySQL 只是每 10 秒同步一次的备份。

为什么不是"增量 + 回填"：
    增量模型需要在"取走增量"和"写回数据库"之间保证原子，任何一步失败都会
    让数字卡住或倒退；读取时还得把数据库的 base 和 Redis 的 delta 拼起来，
    一旦其中一半进了缓存，两边就永远对不上。
    改成绝对值后，Redis 就是唯一真相源，flush 只是幂等覆盖，读路径没有拼接。
"""

import logging

from config.cache_config import new_client, redis_client

logger = logging.getLogger(__name__)

# 每篇文章一个计数器，存的是总数（不是增量）
VIEW_KEY = "news:views:total:{news_id}"
# 脏集合：哪些文章有还没落库的浏览，供后台任务遍历
DIRTY_SET = "news:views:dirty"


def key(news_id: int) -> str:
    return VIEW_KEY.format(news_id=news_id)


async def read(news_id: int) -> int | None:
    """读当前总数；key 不存在返回 None，由调用方决定用哪个值回填。"""
    try:
        value = await redis_client.get(key(news_id))
        return int(value) if value is not None else None
    except Exception:
        logger.warning("读取浏览量失败 news_id=%s", news_id, exc_info=True)
        return None


async def read_many(news_ids: list[int]) -> list[int | None]:
    """批量读，顺序和入参一致。

    Redis 故障时全部返回 None，调用方会退回数据库并尝试回填，
    这样页面最多显示得旧一点，不会突然变成 0。
    """
    if not news_ids:
        return []
    try:
        values = await redis_client.mget([key(news_id) for news_id in news_ids])
        return [int(value) if value is not None else None for value in values]
    except Exception:
        logger.warning("批量读取浏览量失败 count=%s", len(news_ids), exc_info=True)
        return [None] * len(news_ids)


async def seed(news_id: int, value: int) -> None:
    """用数据库当前值回填计数。

    必须是 SET NX：并发回填时只有第一个生效，不会把已经涨上去的计数
    覆盖回数据库的旧值。
    """
    try:
        await redis_client.set(key(news_id), int(value), nx=True)
    except Exception:
        logger.warning("回填浏览量失败 news_id=%s", news_id, exc_info=True)


async def seed_many(pairs: list[tuple[int, int]]) -> None:
    """批量回填，pairs 是 (news_id, 数据库当前值)。"""
    if not pairs:
        return
    try:
        pipe = redis_client.pipeline(transaction=False)
        for news_id, value in pairs:
            pipe.set(key(news_id), int(value), nx=True)
        await pipe.execute()
    except Exception:
        logger.warning("批量回填浏览量失败 count=%s", len(pairs), exc_info=True)


async def bump(news_id: int) -> int | None:
    """这一次浏览 +1，并标记待落库，返回自增后的总数。

    INCR 和 SADD 放同一个 pipeline，只花一次往返；
    Redis 故障返回 None，由调用方决定降级显示数据库的值。
    """
    try:
        async with redis_client.pipeline(transaction=False) as pipe:
            pipe.incr(key(news_id))
            pipe.sadd(DIRTY_SET, news_id)
            value, _ = await pipe.execute()
        return int(value)
    except Exception:
        logger.warning("浏览量自增失败 news_id=%s", news_id, exc_info=True)
        return None


async def delete_many(news_ids: list[int], client=None) -> int:
    """文章被删除时清掉计数，避免 key 永久泄漏。"""
    if not news_ids:
        return 0

    own = client is None
    if own:
        client = new_client()
    try:
        removed = await client.delete(*[key(news_id) for news_id in news_ids])
        await client.srem(DIRTY_SET, *news_ids)
        return int(removed)
    except Exception:
        logger.warning("删除浏览量失败 count=%s", len(news_ids), exc_info=True)
        return 0
    finally:
        if own:
            await client.aclose()
