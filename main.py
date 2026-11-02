import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config.db_config import async_engine
from routers import favorite, history, news, rss, user
from utils.exception_handlers import register_exception_handlers
from utils.logging import setup_logging
from utils.request_context import reset_request_id, set_request_id
from utils.response import success_response

logger = logging.getLogger("api")
setup_logging()


# 装饰器快速创建异步上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表交给 Alembic（alembic upgrade head），应用启动不再碰 DDL
    yield
    await async_engine.dispose()


app = FastAPI(lifespan=lifespan)


register_exception_handlers(app)


@app.middleware("http")
async def access_log(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    token = set_request_id(rid)
    # 同时写到 request 上：app 级的 500 兜底处理器跑在中间件外层，
    # 那时 ContextVar 已经 reset，只能从这里取回编号
    request.state.request_id = rid
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        # 只记"请求结果"，堆栈交给异常处理器，避免同一个错误打两遍堆栈
        logger.warning("%s %s -> 500 in %.0fms", request.method, request.url.path, elapsed)
        raise
    else:
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        logger.info(
            "%s %s -> %s in %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response
    finally:
        reset_request_id(token)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,  # 允许携带 cookie
    allow_methods=["*"],  # 允许的请求方法
    allow_headers=["*"],  # 允许的请求头
)


@app.get("/")
async def root():
    return success_response()


app.include_router(news.router)
app.include_router(user.router)
app.include_router(favorite.router)
app.include_router(history.router)
app.include_router(rss.router)
