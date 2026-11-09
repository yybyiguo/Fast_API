"""并发抓取同一个源：唯一键 + INSERT IGNORE 保证只落一条。"""

import asyncio

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
    <title>Concurrent</title>
    <link href="https://example.com/p/1"/>
    <id>tag:example.com,2026:1</id>
    <updated>2026-01-01T00:00:00Z</updated>
    <summary>summary</summary>
  </entry>
</feed>
"""


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=ATOM, request=request)
        )
    )


async def test_concurrent_fetch_inserts_once(db, category, session_factory):
    feed = RssFeed(
        name="concurrent",
        url="https://example.com/feed",
        category_id=category.id,
        enabled=True,
    )
    db.add(feed)
    await db.commit()
    await db.refresh(feed)

    async def fetch_once():
        async with session_factory() as session:
            current = await session.get(RssFeed, feed.id)
            async with _client() as client:
                result = await fetch_and_store(session, current, client)
            await session.commit()
            return result

    results = await asyncio.gather(fetch_once(), fetch_once())

    async with session_factory() as session:
        count = await session.scalar(select(func.count(News.id)).where(News.feed_id == feed.id))

    assert count == 1
    # 并发下允许其中一个事务因唯一键/锁竞争失败（生产有 Redis 锁兜底），
    # 关键是不能产生重复数据，且至少有一次成功。
    assert any(result.status == "ok" for result in results)
