from fastapi import FastAPI
from contextlib import asynccontextmanager
from models.news import Base
from routers import news
from config.db_config import async_engine


async def create_table():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建成功！")

#装饰器快速创建异步上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_table()
    yield
    await async_engine.dispose()
    print("✅ 数据库连接已关闭")

app = FastAPI(lifespan=lifespan)
@app.get('/')
async def root():
    return {
        "status":200,
        "msg":'成功',
        'data':None
    }

app.include_router(news.router)