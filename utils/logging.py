import logging
import os
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


def setup_logging(level: int = logging.INFO) -> None:
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(request_id)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)

    # 测试/CI 里日志目录可能不可写，也可能根本不需要落盘。
    # 设 LOG_TO_FILE=0 就只输出到控制台。
    if os.getenv("LOG_TO_FILE", "1") != "0":
        LOG_DIR.mkdir(exist_ok=True)
        file = RotatingFileHandler(
            LOG_DIR / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file.setFormatter(fmt)
        file.addFilter(RequestIdFilter())
        root.addHandler(file)
