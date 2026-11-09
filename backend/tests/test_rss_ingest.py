"""RSS 入库链路：fetch_and_store 的 200 / 304 / 错误 / 非法内容。"""

import httpx
from sqlalchemy import func, select

from models.news import News
from models.rss import RssFeed
from services.rss_fetcher import fetch_and_store

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>test</title>
  <link href="https://example.com/"/>
  <entry>
    <title>First &amp; Title</title>
    <link href="https://example.com/p/1"/>
    <id>tag:example.com,2026:1</id>
    <updated>2026-01-01T00:00:00Z</updated>
    <summary>summary</summary>
    <content type="html">&lt;p&gt;para one&lt;/p&gt;</content>
  </entry>
</feed>
"""


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=ATOM, headers={"ETag": '"v1"'}, request=request)


async def _make_feed(db, category, **overrides) -> RssFeed:
    feed = RssFeed(
        name="test",
        url="https://example.com/feed",
        category_id=category.id,
        enabled=True,
        **overrides,
    )
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return feed


async def _count_news(db, feed_id: int) -> int:
    return await db.scalar(select(func.count(News.id)).where(News.feed_id == feed_id))


async def test_first_fetch_inserts_news(db, category):
    feed = await _make_feed(db, category)

    async with _client(_ok) as client:
        result = await fetch_and_store(db, feed, client)
    await db.commit()

    assert result.status == "ok"
    assert (result.fetched, result.inserted, result.skipped) == (1, 1, 0)
    assert await _count_news(db, feed.id) == 1
    assert feed.last_status == "ok"
    assert feed.error_count == 0
    assert feed.etag == '"v1"'
    # 源的站点首页第一次抓取时自动补全
    assert feed.site_url == "https://example.com/"


async def test_second_fetch_dedupes_by_guid(db, category):
    feed = await _make_feed(db, category)

    async with _client(_ok) as client:
        first = await fetch_and_store(db, feed, client)
        await db.commit()
        second = await fetch_and_store(db, feed, client)
        await db.commit()

    assert first.inserted == 1
    assert second.inserted == 0
    assert second.skipped == 1
    assert await _count_news(db, feed.id) == 1


async def test_304_returns_not_modified_and_keeps_etag(db, category):
    feed = await _make_feed(db, category, etag='"v1"')
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["if_none_match"] = request.headers.get("if-none-match")
        return httpx.Response(304, request=request)

    async with _client(handler) as client:
        result = await fetch_and_store(db, feed, client)
    await db.commit()

    assert seen["if_none_match"] == '"v1"'
    assert result.status == "not_modified"
    assert feed.last_status == "not_modified"
    assert feed.etag == '"v1"'
    assert await _count_news(db, feed.id) == 0


async def test_http_error_records_status_without_insert(db, category):
    feed = await _make_feed(db, category)

    async with _client(lambda request: httpx.Response(503, request=request)) as client:
        result = await fetch_and_store(db, feed, client)
    await db.commit()

    assert result.status == "error"
    assert feed.last_status == "error"
    assert feed.error_count == 1
    assert feed.last_error
    assert await _count_news(db, feed.id) == 0


async def test_invalid_payload_is_error_not_ok(db, category):
    feed = await _make_feed(db, category)
    html = b"<html><body>cloudflare challenge</body></html>"

    async with _client(
        lambda request: httpx.Response(200, content=html, request=request)
    ) as client:
        result = await fetch_and_store(db, feed, client)
    await db.commit()

    assert result.status == "error"
    assert "RSS" in (feed.last_error or "")
    assert await _count_news(db, feed.id) == 0


async def test_oversized_payload_is_rejected(db, category, monkeypatch):
    feed = await _make_feed(db, category)
    monkeypatch.setattr("services.rss_fetcher.MAX_BYTES", 10)

    async with _client(_ok) as client:
        result = await fetch_and_store(db, feed, client)
    await db.commit()

    assert result.status == "error"
    assert "字节" in (feed.last_error or "")
    assert await _count_news(db, feed.id) == 0
