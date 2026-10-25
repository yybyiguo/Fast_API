from fastapi import FastAPI
from contextlib import asynccontextmanager

from routers import favorite, history, news,user
from config.db_config import async_engine
from utils.exception_handlers import register_exception_handlers
from fastapi.middleware.cors import CORSMiddleware

from utils.response import success_response


# 装饰器快速创建异步上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表交给 Alembic（alembic upgrade head），应用启动不再碰 DDL
    yield
    await async_engine.dispose()

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
    return success_response()

app.include_router(news.router)
app.include_router(user.router)
app.include_router(favorite.router)
app.include_router(history.router)
