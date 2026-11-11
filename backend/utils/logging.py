import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.request_context import get_request_id


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # 调用方用 extra={"request_id": ...} 显式指定时优先，不覆盖
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return True


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

# 给人看的格式：LOG_FORMAT=text 时用它，和改造前完全一致，方便回退。
TEXT_FORMAT = "%(asctime)s | %(levelname)-7s | %(request_id)s | %(name)s | %(message)s"

# LogRecord 自带的字段名。遍历 extra 时要跳过它们，否则会把 args、exc_info
# 这类内部对象也写进日志。
_STD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    """一行一条、字段固定的日志，方便机器检索和统计。

    - 时间带时区，跨机器对时间不会差 8 小时；
    - 异常堆栈塞进 exc 字段，json.dumps 会把换行转义成 \n，所以仍然是一行；
    - 调用方通过 extra={...} 传的字段（如 status、duration_ms）会自动带上。
    """

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "service": os.getenv("SERVICE_NAME", "api"),
            "env": os.getenv("app_env", "dev"),
        }

        # 调用方 extra 里的业务字段（路径、状态码、耗时……）一并带上。
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                data[key] = value

        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)

        # default=str：万一 extra 里塞了不能序列化的对象，退化成字符串而不是把日志打挂
        return json.dumps(data, ensure_ascii=False, default=str)


def setup_logging(level: int | None = None) -> None:
    # LOG_LEVEL=DEBUG/INFO/WARNING... 不改代码就能调级别
    if level is None:
        level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

    # LOG_FORMAT=text 回退成人看的格式；默认 json
    if os.getenv("LOG_FORMAT", "json").lower() == "text":
        formatter: logging.Formatter = logging.Formatter(TEXT_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    else:
        formatter = JsonFormatter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)

    # 测试/CI 里日志目录可能不可写，也可能根本不需要落盘。
    # 设 LOG_TO_FILE=0 就只输出到控制台。
    if os.getenv("LOG_TO_FILE", "1") != "0":
        LOG_DIR.mkdir(exist_ok=True)
        service = os.getenv("SERVICE_NAME", "api")
        log_name = "app.log" if service == "api" else f"{service}.log"
        file = RotatingFileHandler(
            LOG_DIR / log_name,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file.setFormatter(formatter)
        file.addFilter(RequestIdFilter())
        root.addHandler(file)

    # uvicorn 在加载 app 之前就用自己的 LOGGING_CONFIG 配好了这三个 logger：
    # 独立 handler + propagate=False，所以它们的日志不会走上面的格式。
    # app 导入时（晚于 uvicorn 的 configure_logging）把 handler 摘掉、打开传播。
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    # 访问日志已经由 main.py 的 access_log 中间件统一输出（带 request_id 和耗时），
    # 关掉 uvicorn 自带的 access log，否则一次请求会出现两条。
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True
