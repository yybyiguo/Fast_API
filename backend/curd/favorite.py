from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.favorite import Favorite
from models.news import News


async def is_favorite(db: AsyncSession, user_id: int, news_id: int):
    stmt = select(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.scalar(stmt)
    if result is None:
        return False
    return True


async def add_favorite(db: AsyncSession, user_id: int, news_id: int):
    favorite = Favorite(user_id=user_id, news_id=news_id)
    db.add(favorite)
    await db.flush()
    await db.refresh(favorite)
    return favorite


async def delete_favorite(db: AsyncSession, user_id: int, news_id: int):
    stmt = select(Favorite).where(Favorite.news_id == news_id, Favorite.user_id == user_id)
    record = await db.scalar(stmt)
    if record:
        await db.delete(record)
        return True
    return False


async def get_list(db: AsyncSession, user_id: int, offset: int, page_size: int):
    stmt = (
        select(
            Favorite.id,
            Favorite.news_id,
            # 模型和表里都是 create_time，没有 created_at；
            # 用 label 保持接口字段不变，前端不用跟着改
            Favorite.create_time.label("created_at"),
            News.title,
            News.description,
            News.image,
            News.author,
            News.category_id,
            News.views,
            News.publish_time,
        )
        .join(News, Favorite.news_id == News.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.create_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return [dict(row) for row in result.mappings()]


async def get_count(db: AsyncSession, user_id: int):
    stmt = select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
    return await db.scalar(stmt)


async def delete_all_favorite(db: AsyncSession, user_id: str):
    stmt = delete(Favorite).where(Favorite.user_id == user_id)
    result = await db.execute(stmt)

    return result.rowcount or 0
