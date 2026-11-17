import json
import logging
from typing import Any

import redis.asyncio as redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from config.db_config import settings
from utils.metrics import CACHE_ERRORS

logger = logging.getLogger(__name__)


def new_client() -> redis.Redis:
    """新建一个 Redis 客户端，供独立事件循环使用。

    全局 redis_client 绑定在 FastAPI 的事件循环上；Celery 任务里用
    asyncio.run 会新建循环，复用全局客户端会报 "attached to a different loop"。
    所以任务里必须就地创建、用完关闭。
    """
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=settings.redis_decode_responses,
        socket_connect_timeout=1,  # 建连最多等 1 秒
        socket_timeout=1,  # 建连后读写最多等 1 秒
        # 缓存是"锦上添花"，挂了就立刻放弃去查库。
        # retry_on_timeout 在 redis-py 6+ 已废弃且默认会重试超时，这里显式关掉。
        retry=Retry(NoBackoff(), 0),
    )


redis_client = new_client()


async def get_cache(key: str):
    try:
        return await redis_client.get(key)
    except Exception as e:
        CACHE_ERRORS.labels(op="get").inc()
        logger.warning("读缓存失败 key=%s: %s", key, e)
        return None


async def get_json_cache(key: str):
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)

        return None
    except Exception as e:
        CACHE_ERRORS.labels(op="get").inc()
        logger.warning("读缓存JSON失败 key=%s: %s", key, e)
        return None


async def set_cache(key: str, value: Any, expire: int = 3600):
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        await redis_client.setex(key, expire, value)
        return None
    except Exception as e:
        CACHE_ERRORS.labels(op="set").inc()
        logger.warning("写缓存失败 key=%s: %s", key, e)
        return None
