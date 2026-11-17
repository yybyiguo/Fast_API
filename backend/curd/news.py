from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cache.news_cache import (
    get_cache_categories,
    get_cache_news_list,
    set_cache_categories,
    set_cache_news_list,
)
from models.news import Category, News

# 列表只查卡片需要的字段：不查 content（正文很长，列表用不到），也不查 views
# （views 由 Redis 计数器统一提供，不能跟着正文一起进缓存）。
_LIST_COLUMNS = (
    News.id,
    News.title,
    News.description,
    News.image,
    News.author,
    News.category_id,
    News.publish_time,
    News.is_top,
    News.source_url,
)

# 空列表只缓存 30 秒：分类刚建好、还没抓回文章时，别让"空"这个结果占住 5 分钟
EMPTY_LIST_TTL = 30


async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100):
    cache_categories = await get_cache_categories()
    # 用 is not None：[] 也是合法缓存（分类为空时不该每次回源）
    if cache_categories is not None:
        return cache_categories

    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    uncache_categories = result.scalars().all()

    await set_cache_categories(jsonable_encoder(uncache_categories))

    return uncache_categories


async def get_news_list(
    categories_id: int, db: AsyncSession, skip: int = 0, limit: int = 10
) -> list[dict]:
    page = skip // max(limit, 1) + 1
    cache_news_list = await get_cache_news_list(categories_id, page, limit)
    if cache_news_list is not None:
        return cache_news_list

    # 必须按发布时间倒序：没有 ORDER BY 时 MySQL 走主键顺序，
    # 新抓的 RSS 新闻 id 最大，会永远排在 10 万条 seed 数据的最后。
    stmt = (
        select(*_LIST_COLUMNS)
        .where(News.category_id == categories_id)
        .order_by(News.publish_time.desc(), News.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    items = jsonable_encoder([dict(row._mapping) for row in rows])

    # 空列表也要缓存，否则不存在的分类每次都会打到数据库（缓存穿透）
    await set_cache_news_list(
        items,
        categories_id,
        page,
        limit,
        expire=EMPTY_LIST_TTL if not items else 300,
    )
    return items


async def get_news_count(db: AsyncSession, category_id: int):
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()  # 只能一个结果不然报错


async def get_news_detail(db: AsyncSession, news_id: int):
    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  # 只能一个结果不然报错


async def get_views_map(db: AsyncSession, news_ids: list[int]) -> dict[int, int]:
    """一次 IN 查询拿多篇文章的数据库 views，给计数缺失时兜底/回填用。"""
    if not news_ids:
        return {}
    rows = await db.execute(select(News.id, News.views).where(News.id.in_(news_ids)))
    return {row.id: row.views for row in rows}


async def get_related_news(
    db: AsyncSession,
    news_id: int,
    category_id: int,
    limit: int = 5,
):
    stmt = (
        select(News)
        .where(News.id != news_id, News.category_id == category_id)
        .order_by(News.views.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    related_news = result.scalars().all()
    return [
        {
            "id": result.id,
            "title": result.title,
            "author": result.author,
            "image": result.image,
            "publishTime": result.publish_time,
            "categoryId": result.category_id,
            "content": result.content,
            "views": result.views,
        }
        for result in related_news
    ]
