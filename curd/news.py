from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from sqlalchemy import func, select, update
from models.news import Category,News



async def get_categories(db: AsyncSession,skip:int=0,limit:int=100):
    stmt=select(Category).offset(skip).limit(limit)
    result=await db.execute(stmt)
    return result.scalars().all()

async def get_news_list(
    categories_id:int,
    db: AsyncSession,
    skip:int=0,
    limit:int=10):
    stmt=select(News).where(News.category_id==categories_id).offset(skip).limit(limit)
    result=await db.execute(stmt)
    return result.scalars().all()

async def get_news_count(db: AsyncSession,category_id:int):
    stmt=select(func.count(News.id)).where(News.category_id==category_id)
    result=await db.execute(stmt)   
    return result.scalar_one()#只能一个结果不然报错


async def get_news_detail(db: AsyncSession,news_id:int):
    stmt=select(News).where(News.id==news_id)
    result=await db.execute(stmt)
    return result.scalar_one_or_none()#只能一个结果不然报错

#更新操作要检查数据库是否真的命中了数据
async def increase_news_views(db: AsyncSession,news_id:int):
    stmt=update(News).where(News.id==news_id).values(views=News.views+1)
    result=await db.execute(stmt)
    await db.commit()
    return result.rowcount>0


async def get_related_news(db:AsyncSession,news_id:int,category_id:int,limit:int=5,):
    stmt=select(News).where(News.id!=news_id,News.category_id==category_id).order_by(News.views.desc()).limit(limit)
    result=await db.execute(stmt)
    related_news= result.scalars().all()
    return [{'id':result.id,
            'title':result.title,
            'author':result.author,
            'image':result.image,
            'publishTime':result.publish_time,
            'categoryId':result.category_id,
            'content':result.content,
            'views':result.views,
            } for result in related_news]






