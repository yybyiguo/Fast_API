"""RSS 管理接口的第二批：更新、立即抓取、预览、自动发现、外键错误。"""

from types import SimpleNamespace

import httpx

from config.db_config import settings

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>test</title>
  <link href="https://example.com/"/>
  <entry>
    <title>Preview Title</title>
    <link href="https://example.com/p/1"/>
    <id>tag:example.com,2026:1</id>
    <updated>2026-01-01T00:00:00Z</updated>
    <summary>preview summary</summary>
  </entry>
</feed>
"""


def _as_admin(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rss_admin_users", "alice")


def _mock_http(monkeypatch, handler) -> None:
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("routers.rss.httpx.AsyncClient", factory)


async def _create_feed(client, auth, category, url="https://1.1.1.1/feed") -> dict:
    response = await client.post(
        "/api/rss/feeds",
        json={"name": "test", "url": url, "categoryId": category.id},
        headers=auth["headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def test_update_feed_fields(client, auth, monkeypatch, category):
    _as_admin(monkeypatch)
    feed = await _create_feed(client, auth, category)

    response = await client.patch(
        f"/api/rss/feeds/{feed['id']}",
        json={"enabled": False, "fetchInterval": 1800},
        headers=auth["headers"],
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["enabled"] is False
    assert data["fetchInterval"] == 1800

    missing = await client.patch(
        f"/api/rss/feeds/{feed['id']}",
        json={"categoryId": 999999},
        headers=auth["headers"],
    )
    assert missing.status_code == 422


async def test_create_with_unknown_category_returns_422(client, auth, monkeypatch):
    _as_admin(monkeypatch)

    response = await client.post(
        "/api/rss/feeds",
        json={"name": "bad", "url": "https://1.1.1.1/feed", "categoryId": 999999},
        headers=auth["headers"],
    )

    assert response.status_code == 422
    assert response.json()["message"] == "分类不存在"


async def test_refresh_enqueues_task(client, auth, monkeypatch, category):
    _as_admin(monkeypatch)
    feed = await _create_feed(client, auth, category)

    from tasks import rss_tasks

    calls = []

    def fake_delay(feed_id, request_id=None):
        calls.append((feed_id, request_id))
        return SimpleNamespace(id="task-1")

    monkeypatch.setattr(rss_tasks, "fetch_feed", SimpleNamespace(delay=fake_delay))

    response = await client.post(
        f"/api/rss/feeds/{feed['id']}/refresh",
        headers=auth["headers"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["taskId"] == "task-1"
    # 入队时要把当前请求的单号一起带过去，后台日志才和这次请求对得上
    assert calls == [(feed["id"], calls[0][1])]
    assert calls[0][1] != "-"


async def test_preview_returns_entries(client, auth, monkeypatch):
    _as_admin(monkeypatch)
    _mock_http(monkeypatch, lambda request: httpx.Response(200, content=ATOM, request=request))

    response = await client.get(
        "/api/rss/preview",
        params={"url": "https://1.1.1.1/feed"},
        headers=auth["headers"],
    )

    assert response.status_code == 200, response.text
    items = response.json()["data"]
    assert items[0]["title"] == "Preview Title"


async def test_preview_returns_502_on_fetch_error(client, auth, monkeypatch):
    _as_admin(monkeypatch)
    _mock_http(monkeypatch, lambda request: httpx.Response(503, request=request))

    response = await client.get(
        "/api/rss/preview",
        params={"url": "https://1.1.1.1/feed"},
        headers=auth["headers"],
    )

    assert response.status_code == 502


async def test_discover_finds_feed_link(client, auth, monkeypatch):
    _as_admin(monkeypatch)
    html = (
        '<html><head><link rel="alternate" type="application/rss+xml" '
        'href="/feed.xml"></head></html>'
    )
    _mock_http(monkeypatch, lambda request: httpx.Response(200, text=html, request=request))

    response = await client.post(
        "/api/rss/discover",
        json={"siteUrl": "https://1.1.1.1"},
        headers=auth["headers"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == ["https://1.1.1.1/feed.xml"]
