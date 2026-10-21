import json
from typing import Any

import redis.asyncio as redis
from config.db_config import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=settings.redis_decode_responses
    )

async def get_cache(key:str):
    try:
        return await redis_client.get(key)
    except Exception as e :
        print(f'获取缓存字符串失败：{e}')
        return None

async def get_json_cache(key:str):
    try:
        data = await redis_client.get(key)
        if data :
            print(f'获取缓存成功')
            return json.loads(data)

        return None
    except Exception as e :
        print(f'获取缓存json失败：{e}')
        return None

async def set_cache(key:str,value:Any,expire:int =3600):
    try:
        if isinstance(value,(dict,list)):
            value=json.dumps(value,ensure_ascii=False)
        await redis_client.setex(key,expire,value)
        print(f'设置缓存成功')
        return None
    except Exception as e:
        print(f'设置缓存失败：{e}')
        return None
