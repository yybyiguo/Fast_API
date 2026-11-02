import logging
from typing import Any

from redis.asyncio import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from config.cache_config import get_json_cache, set_cache
from config.db_config import settings

logger = logging.getLogger(__name__)


categories_key = "news:categories"
news_list_key = "news:list:"


async def invalidate_news_list(category_id: int, client: Redis | None = None) -> int:
    """抓取后清掉该分类的列表缓存，否则首页最多 5 分钟看不到新内容。"""
    own = client is None
    if own:
        client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            retry=Retry(NoBackoff(), 0),
        )
    try:
        keys = [
            key
            async for key in client.scan_iter(match=f"{news_list_key}{category_id}:*", count=200)
        ]
        if keys:
            await client.delete(*keys)
        return len(keys)
    except Exception as exc:
        logger.warning("失效新闻列表缓存失败 category=%s: %s", category_id, exc)
        return 0
    finally:
        if own:
            await client.aclose()


async def get_cache_categories():
    return await get_json_cache(categories_key)


async def set_cache_categories(data: list[dict[str, Any]], expire: int = 1200):
    return await set_cache(categories_key, data, expire)


async def set_cache_news_list(
    data: list[dict[str, Any]],
    category_id: int | None,
    page: int,
    size: int,
    expire: int = 300,
):
    category_part = category_id if category_id is not None else "all"
    key = f"{news_list_key}{category_part}:{page}:{size}"
    return await set_cache(key, data, expire)


async def get_cache_news_list(category_id: int, page: int, size: int):
    category_part = category_id if category_id is not None else "all"
    key = f"{news_list_key}{category_part}:{page}:{size}"
    return await get_json_cache(key)
