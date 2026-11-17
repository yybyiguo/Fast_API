import json
import logging
import random
from typing import Any

from redis.asyncio import Redis

from config.cache_config import get_cache, get_json_cache, new_client, set_cache

logger = logging.getLogger(__name__)

categories_key = "news:categories"
news_list_key = "news:list:"
news_detail_key = "news:detail:"
# 详情缓存的空值标记：不存在的 id 也缓存一小段时间，挡住重复的穿透请求
NULL_MARK = "__NULL__"

# 详情正文缓存 15 分钟，加 0~120 秒随机抖动，避免同一批 key 同时过期
DETAIL_TTL_BASE = 900
DETAIL_TTL_JITTER = 120


def detail_ttl() -> int:
    return DETAIL_TTL_BASE + random.randint(0, DETAIL_TTL_JITTER)


def _detail_key(news_id: int) -> str:
    return f"{news_detail_key}{news_id}"


async def invalidate_news_list(category_id: int, client: Redis | None = None) -> int:
    """抓取新数据后清掉该分类的列表缓存旧数据，否则首页最多 5 分钟看不到新内容。"""
    own = client is None
    if own:
        client = new_client()
    try:
        keys = [
            key
            # scan_iter 把所有匹配的 key 全找出来，塞进 keys 列表，每次查200条
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


async def invalidate_categories(client: Redis | None = None) -> int:
    """增删改源会同步分类，分类缓存必须立刻失效。"""
    own = client is None
    if own:
        client = new_client()
    try:
        return await client.delete(categories_key)
    except Exception as exc:
        logger.warning("失效分类缓存失败: %s", exc)
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


async def get_cache_detail(news_id: int) -> dict[str, Any] | str | None:
    """读详情缓存。

    返回 dict 表示命中正文；返回 NULL_MARK 表示这个 id 已知不存在；
    返回 None 表示未命中，调用方需要回源。
    """
    raw = await get_cache(_detail_key(news_id))
    if raw is None:
        return None
    if raw == NULL_MARK:
        return NULL_MARK
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("详情缓存内容损坏 news_id=%s", news_id)
        return None


async def set_cache_detail(news_id: int, data: dict[str, Any], expire: int | None = None) -> None:
    await set_cache(_detail_key(news_id), data, expire or detail_ttl())


async def set_cache_detail_null(news_id: int, expire: int = 60) -> None:
    await set_cache(_detail_key(news_id), NULL_MARK, expire)


async def invalidate_detail(news_id: int, client: Redis | None = None) -> int:
    """文章被删/被改时清掉详情缓存。"""
    own = client is None
    if own:
        client = new_client()
    try:
        return await client.delete(_detail_key(news_id))
    except Exception as exc:
        logger.warning("失效详情缓存失败 news_id=%s: %s", news_id, exc)
        return 0
    finally:
        if own:
            await client.aclose()


async def invalidate_detail_many(news_ids: list[int], client: Redis | None = None) -> int:
    """批量失效详情缓存，给清理旧文章的定时任务用。"""
    if not news_ids:
        return 0

    own = client is None
    if own:
        client = new_client()
    try:
        return await client.delete(*[_detail_key(news_id) for news_id in news_ids])
    except Exception as exc:
        logger.warning("批量失效详情缓存失败 count=%s: %s", len(news_ids), exc)
        return 0
    finally:
        if own:
            await client.aclose()
