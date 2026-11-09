"""健康检查与 Prometheus 指标。"""

import asyncio
from datetime import datetime

from models.rss import RssFeed
from utils import metrics


async def test_healthz(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readyz_allows_redis_degraded(client):
    response = await client.get("/readyz")
    # Redis 在 CI/本地可能没起，只要求数据库可用且状态是 ok/degraded
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["checks"]["db"] == "ok"


async def test_metrics_endpoint(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "toutiao_news_total" in response.text


async def test_refresh_once_sets_business_gauges(db, session_factory, category):
    db.add(
        RssFeed(
            name="ok",
            url="https://example.com/ok.xml",
            category_id=category.id,
            last_status="ok",
            last_fetch_at=datetime(2026, 1, 1, 8, 0),
        )
    )
    db.add(
        RssFeed(
            name="bad",
            url="https://example.com/bad.xml",
            category_id=category.id,
            last_status="error",
        )
    )
    await db.commit()

    await metrics.refresh_once(session_factory)

    assert metrics.RSS_TOTAL._value.get() == 2
    assert metrics.RSS_OK._value.get() == 1
    assert metrics.RSS_ERROR._value.get() == 1
    assert metrics.RSS_NEVER._value.get() == 0


async def test_metrics_loop_exits_on_stop(session_factory):
    stop = asyncio.Event()
    stop.set()
    # 循环体先刷新一次，再看到 stop 立即返回
    await asyncio.wait_for(metrics.metrics_loop(stop, session_factory), timeout=5)
