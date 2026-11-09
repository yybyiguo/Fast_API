"""抓取层的行为测试：不连数据库、不联网，用 MockTransport 造假响应。"""

import httpx
import pytest

from models.rss import RssFeed
from services.rss_fetcher import MAX_BYTES, fetch_payload, parse_entries

FEED_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>test</title>
    <link>https://example.com/</link>
    <item>
      <title>hello</title>
      <link>https://example.com/p/1</link>
      <guid>tag:example.com,2026:1</guid>
      <description>world</description>
    </item>
  </channel>
</rss>
"""


def make_feed(etag=None, last_modified=None) -> RssFeed:
    return RssFeed(
        name="test",
        url="https://example.com/feed",
        category_id=1,
        etag=etag,
        last_modified=last_modified,
    )


def make_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_304_uses_conditional_headers():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["if-none-match"] = request.headers.get("if-none-match")
        return httpx.Response(304, headers={"etag": '"v1"'})

    async with make_client(handler) as client:
        outcome = await fetch_payload(client, make_feed(etag='"v1"'))

    assert outcome.status == 304
    assert outcome.payload is None
    assert seen["if-none-match"] == '"v1"'


@pytest.mark.asyncio
async def test_force_skips_conditional_headers():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["if-none-match"] = request.headers.get("if-none-match")
        seen["if-modified-since"] = request.headers.get("if-modified-since")
        return httpx.Response(200, content=FEED_XML, headers={"etag": '"v1"'})

    async with make_client(handler) as client:
        outcome = await fetch_payload(
            client,
            make_feed(etag='"v1"', last_modified="Sun, 01 Nov 2026 00:00:00 GMT"),
            force=True,
        )

    assert outcome.status == 200
    assert outcome.payload
    assert seen["if-none-match"] is None
    assert seen["if-modified-since"] is None


@pytest.mark.asyncio
async def test_200_payload_can_be_parsed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=FEED_XML)

    async with make_client(handler) as client:
        outcome = await fetch_payload(client, make_feed())

    items = parse_entries(outcome.payload, make_feed())
    assert len(items) == 1
    assert items[0]["title"] == "hello"


@pytest.mark.asyncio
async def test_oversize_content_length_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-length": str(MAX_BYTES + 1)},
        )

    async with make_client(handler) as client:
        with pytest.raises(ValueError):
            await fetch_payload(client, make_feed())


@pytest.mark.asyncio
async def test_timeout_propagates():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    async with make_client(handler) as client:
        with pytest.raises(httpx.TimeoutException):
            await fetch_payload(client, make_feed())
