from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from sqlalchemy import delete, func, select, update
from models.favorite import Favorite
from models.news import Category,News



async def is_favorite(db:AsyncSession,user_id:int,news_id:int):
    stmt=select(Favorite).where(Favorite.user_id==user_id , Favorite.news_id==news_id)
    result = await db.scalar(stmt)
    if result is None:
        return False
    return True

async def add_favorite(db:AsyncSession,user_id:int,news_id:int):
    favorite=Favorite(user_id=user_id,news_id=news_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    return favorite

async def delete_favorite(db:AsyncSession,user_id:int,news_id:int):
    stmt=select(Favorite).where(Favorite.news_id==news_id,Favorite.user_id==user_id)
    record= await db.scalar(stmt)
    if record:
        await db.delete(record)
        await db.commit()
    return True

async def get_list(db:AsyncSession,user_id:int,offset:int,page_size:int):
    stmt = select(
        Favorite.id, Favorite.news_id, Favorite.created_at,
        News.title, News.description, News.image, News.author,
        News.category_id, News.views, News.publish_time,
    ).join(News, Favorite.news_id == News.id).where(
        Favorite.user_id==user_id
    ).order_by(Favorite.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    return [dict(row) for row in result.mappings()]

async def get_count(db:AsyncSession,user_id:int):
    stmt=select(func.count(Favorite.id)).where(Favorite.user_id==user_id)
    return await db.scalar(stmt)


async def delete_all_favorite(db:AsyncSession,user_id:str):
    stmt=delete(Favorite).where(Favorite.user_id==user_id)
    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount or 0