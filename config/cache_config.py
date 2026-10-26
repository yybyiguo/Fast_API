import json
from typing import Any

import redis.asyncio as redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from config.db_config import settings
import logging

logger = logging.getLogger(__name__)
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=settings.redis_decode_responses,
    socket_connect_timeout=1,   # 建连最多等 1 秒
    socket_timeout=1,           # 建连后读写最多等 1 秒
    # 缓存是"锦上添花"，挂了就立刻放弃去查库。
    # retry_on_timeout 在 redis-py 6+ 已废弃且默认会重试超时，这里显式关掉。
    retry=Retry(NoBackoff(), 0),
    )

async def get_cache(key:str):
    try:
        return await redis_client.get(key)
    except Exception as e :
        logger.warning("读缓存失败 key=%s: %s", key, e)
        return None 

async def get_json_cache(key:str):
    try:
        data = await redis_client.get(key)
        if data :
            return json.loads(data)

        return None
    except Exception as e :
        logger.warning("读缓存JSON失败 key=%s: %s", key, e)
        return None

async def set_cache(key:str,value:Any,expire:int =3600):
    try:
        if isinstance(value,(dict,list)):
            value=json.dumps(value,ensure_ascii=False)
        await redis_client.setex(key,expire,value)
        return None
    except Exception as e:
        logger.warning("写缓存失败 key=%s: %s", key, e)
        return None
