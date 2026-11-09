import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from config.db_config import async_engine
from routers import favorite, health, history, news, rss, user
from utils.exception_handlers import register_exception_handlers
from utils.logging import setup_logging
from utils.metrics import metrics_loop
from utils.request_context import reset_request_id, set_request_id
from utils.response import success_response

logger = logging.getLogger("api")
setup_logging()


# 装饰器快速创建异步上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表交给 Alembic（alembic upgrade head），应用启动不再碰 DDL。
    # 业务指标后台刷新，指标自身失败不能影响请求。
    stop = asyncio.Event()
    task = asyncio.create_task(metrics_loop(stop))
    try:
        yield
    finally:
        stop.set()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await async_engine.dispose()


app = FastAPI(lifespan=lifespan)

# /metrics 给 Prometheus 抓取。多 worker 时每个进程各算各的，
# 所以 compose 里 api 固定 --workers 1；要横向扩就改 multiprocess 或独立 exporter。
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


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
app.include_router(health.router)
