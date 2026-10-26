import traceback
import logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status

from config.db_config import settings
from utils.request_context import get_request_id

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    """取出这次请求的编号。

    优先读中间件写在 request.state 上的值：app 级的 Exception 处理器
    跑在 ServerErrorMiddleware 里，位于我们中间件的外层，执行到这里时
    ContextVar 已经被 reset 回默认值了，只靠 get_request_id() 会拿到 "-"。
    """
    rid = getattr(request.state, "request_id", None)
    return rid or get_request_id()


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    处理 HTTPException 异常
    """
    # HTTPException 通常是业务逻辑主动抛出的, data 保持 None
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        },
        headers=getattr(exc, "headers", None),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    处理数据库完整性约束错误
    """
    error_msg = str(exc.orig)

    # 判断具体的约束错误类型
    if "username_UNIQUE" in error_msg or "Duplicate entry" in error_msg:
        detail = "已存在"
    elif "FOREIGN KEY" in error_msg:
        detail = "关联数据不存在"
    else:
        detail = "数据约束冲突，请检查输入"

    # 开发模式下返回详细错误信息
    error_data = None
    if settings.debug:
        error_data = {
            "error_type": "IntegrityError",
            "error_detail": error_msg,
            "path": str(request.url)
        }

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "message": detail,
            "data": error_data
        }
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """
    处理 SQLAlchemy 数据库错误
    """
    # 开发模式下返回详细错误信息
    error_data = None
    if settings.debug:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": traceback.format_exc(),
            "path": str(request.url)
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "数据库操作失败，请稍后重试",
            "data": error_data,
            "request_id": _request_id(request),
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    处理所有未捕获的异常
    """
    rid = _request_id(request)
    logger.error(
        "未处理异常 %s %s", request.method, request.url.path,
        exc_info=exc,                 # 自动带上完整堆栈
        extra={"request_id": rid},    # ContextVar 已失效，显式带上编号
    )
    # 开发模式下返回详细错误信息
    error_data = None
    if settings.debug:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            # 格式化异常信息为字符串，方便日志记录和调试
            "traceback": traceback.format_exc(),
            "path": str(request.url)
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": error_data,
            "request_id": rid,
        }
    )
