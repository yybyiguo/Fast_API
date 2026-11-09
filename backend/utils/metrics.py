"""业务指标：新闻规模、RSS 源健康度。

HTTP 指标由 prometheus-fastapi-instrumentator 负责，这里只补它看不到的业务状态。
指标每 30 秒从数据库刷新一次，Prometheus 抓取时读内存值，不在请求路径里查库。
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from prometheus_client import Gauge
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import AsyncSessionLocal
from models.news import News
from models.rss import RssFeed

logger = logging.getLogger(__name__)

CST = ZoneInfo("Asia/Shanghai")
REFRESH_SECONDS = 30

NEWS_TOTAL = Gauge("toutiao_news_total", "新闻总数")
RSS_TOTAL = Gauge("toutiao_rss_feeds_total", "RSS 源总数")
RSS_OK = Gauge("toutiao_rss_feeds_ok", "最近一次抓取成功或未变更的源数量")
RSS_ERROR = Gauge("toutiao_rss_feeds_error", "最近一次抓取失败的源数量")
RSS_NEVER = Gauge("toutiao_rss_feeds_never", "从未抓取过的源数量")
RSS_LAST_SUCCESS = Gauge(
    "toutiao_rss_last_success_timestamp",
    "最近一次成功抓取的时间戳（Unix 秒）",
)

SessionFactory = Callable[[], AsyncSession]


async def refresh_once(session_factory: SessionFactory | None = None) -> None:
    factory = session_factory or AsyncSessionLocal
    async with factory() as db:
        rows = (
            await db.execute(
                select(RssFeed.last_status, func.count(RssFeed.id)).group_by(RssFeed.last_status)
            )
        ).all()
        counts = {status or "never": count for status, count in rows}

        RSS_TOTAL.set(sum(counts.values()))
        RSS_OK.set(counts.get("ok", 0) + counts.get("not_modified", 0))
        RSS_ERROR.set(counts.get("error", 0))
        RSS_NEVER.set(counts.get("never", 0))

        last_success: datetime | None = await db.scalar(
            select(func.max(RssFeed.last_fetch_at)).where(
                RssFeed.last_status.in_(("ok", "not_modified"))
            )
        )
        if last_success:
            # 库里存的是 naive 本地时间，显式按 Asia/Shanghai 转 Unix 秒
            RSS_LAST_SUCCESS.set(last_success.replace(tzinfo=CST).timestamp())

        NEWS_TOTAL.set((await db.scalar(select(func.count(News.id)))) or 0)


async def metrics_loop(stop: asyncio.Event, session_factory: SessionFactory | None = None) -> None:
    while True:
        try:
            await refresh_once(session_factory)
        except Exception:
            # 指标刷新失败不能影响主服务，等下一轮
            logger.warning("刷新业务指标失败", exc_info=True)

        try:
            await asyncio.wait_for(stop.wait(), timeout=REFRESH_SECONDS)
        except TimeoutError:
            continue
        else:
            return
