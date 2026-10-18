from fastapi import FastAPI
from contextlib import asynccontextmanager
from models.user import Base
from routers import news,user
from config.db_config import async_engine
from utils.exception_handlers import register_exception_handlers
from fastapi.middleware.cors import CORSMiddleware


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

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,       # 允许携带 cookie
    allow_methods=["*"],          # 允许的请求方法
    allow_headers=["*"],          # 允许的请求头
)


@app.get('/')
async def root():
    return {
        "status":200,
        "msg":'成功',
        'data':None
    }

app.include_router(news.router)
app.include_router(user.router)
