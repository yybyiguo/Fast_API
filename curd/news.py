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


async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100):
    cache_categories = await get_cache_categories()
    if cache_categories:
        return cache_categories

    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    uncache_categories = result.scalars().all()

    await set_cache_categories(jsonable_encoder(uncache_categories))

    return uncache_categories


async def get_news_list(categories_id: int, db: AsyncSession, skip: int = 0, limit: int = 10):

    page = skip // limit + 1
    cache_news_list = await get_cache_news_list(categories_id, page, limit)
    if cache_news_list:
        return cache_news_list

    # 必须按发布时间倒序：没有 ORDER BY 时 MySQL 走主键顺序，
    # 新抓的 RSS 新闻 id 最大，会永远排在 10 万条 seed 数据的最后。
    stmt = (
        select(News)
        .where(News.category_id == categories_id)
        .order_by(News.publish_time.desc(), News.id.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    # scalars() 只能消费一次：先取成 rows，再缓存和返回，
    # 否则第二次 .all() 拿到空列表（前端以前靠重试兜底）
    rows = result.scalars().all()
    await set_cache_news_list(jsonable_encoder(rows), categories_id, page, limit)
    return rows


async def get_news_count(db: AsyncSession, category_id: int):
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()  # 只能一个结果不然报错


async def get_news_detail(db: AsyncSession, news_id: int):
    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  # 只能一个结果不然报错


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
