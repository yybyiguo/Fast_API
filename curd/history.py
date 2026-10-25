from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.history import History
from models.news import News


async def add_user_history(db:AsyncSession,news_id:int,user_id:int,update_time:datetime):
    stmt = select(News).where(News.id==news_id)
    num = await db.execute(stmt)
    if not num.scalar_one_or_none():
        return False
    history = History(user_id=user_id,news_id=news_id,update_time=update_time)
    db.add(history)
    return True


async def get_list(db: AsyncSession, user_id: int, offset: int, page_size: int):
    stmt = (
        select(
            History.id,
            History.news_id,
            History.update_time,
            News.title,
            News.description,
            News.image,
            News.author,
            News.category_id,
            News.views,
            News.publish_time,
        )
        .join(News, History.news_id == News.id)
        .where(History.user_id == user_id)
        .order_by(History.update_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return [dict(row) for row in result.mappings()]


async def get_count(db: AsyncSession, user_id: int):
    stmt = select(func.count(History.id)).where(History.user_id == user_id)
    return await db.scalar(stmt)


async def delete_history(db:AsyncSession,user_id:int,news_id:int):
    stmt = select(History).where(History.news_id == news_id, History.user_id == user_id)
    record= await db.scalar(stmt)
    if record:
        await db.delete(record)
        return True
    return False


async def delete_all_history(db: AsyncSession, user_id: str):
    stmt = delete(History).where(History.user_id == user_id)
    result = await db.execute(stmt)

    return result.rowcount or 0
