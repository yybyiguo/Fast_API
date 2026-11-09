"""浏览量计数器：请求只碰 Redis，数据库由后台任务批量写回。

为什么这么设计：
    原实现每个详情页请求都执行 UPDATE news SET views = views + 1，
    热门新闻会被 1000 个并发请求抢同一把行锁。
    改成 Redis 自增（内存操作、微秒级、无锁竞争），
    再用后台任务把累计值批量写回 MySQL。
"""

import logging

from config.cache_config import redis_client

logger = logging.getLogger(__name__)

# 每条新闻一个计数器
_VIEW_KEY = "news:views:{news_id}"
# 脏数据集：记下"哪些新闻有未落库的增量"，供后台任务遍历
_DIRTY_SET = "news:views:dirty"


async def increase(news_id: int) -> None:
    """给某条新闻加一次浏览。

    失败只记日志，绝不抛出去 —— 浏览量统计不该让详情页打不开。
    """
    try:
        # 用 pipeline 把两条命令合成一次网络往返
        async with redis_client.pipeline(transaction=False) as pipe:
            pipe.incr(
                _VIEW_KEY.format(news_id=news_id)
            )  # INCR 本身保证原子性。所以并发安全这块，INCR 已经解决了。
            pipe.sadd(_DIRTY_SET, news_id)
            await pipe.execute()
    except Exception:
        logger.warning("浏览量计数失败 news_id=%s", news_id, exc_info=True)


async def pending(news_id: int) -> int:
    """在redis中还没落库的增量。

    详情页返回时要用「数据库里的值 + 这个增量」，
    否则用户刷新页面会看到浏览量不涨。
    """
    try:
        value = await redis_client.get(_VIEW_KEY.format(news_id=news_id))
        return int(value) if value else 0
    except Exception:
        return 0
