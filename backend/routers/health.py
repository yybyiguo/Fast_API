"""给容器编排用的健康检查。"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.cache_config import redis_client
from config.db_config import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz():
    # 存活探针：只证明进程还在，不碰数据库/Redis
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(db: AsyncSession = Depends(get_db)):
    # 就绪探针：数据库是硬依赖，挂了返回 503 让编排层停止转发；
    # Redis 只是缓存，挂了标记 degraded 但仍返回 200，避免整站被摘流量。
    checks = {}
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        db_ok = False
        checks["db"] = f"error: {exc}"

    redis_ok = True
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        redis_ok = False
        checks["redis"] = f"error: {exc}"

    if not db_ok:
        status, code = "not_ready", 503
    elif not redis_ok:
        status, code = "degraded", 200
    else:
        status, code = "ok", 200

    return JSONResponse(status_code=code, content={"status": status, "checks": checks})
