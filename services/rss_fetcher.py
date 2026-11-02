"""RSS 抓取 → 清洗 → 入库。

约定：
- 对外函数都返回结果对象，不抛异常（任务失败只记录到 rss_feeds.last_error）
- 时间统一转成 Asia/Shanghai 的 naive datetime，和项目其它字段一致
- 入库用 INSERT IGNORE + 预查询双保险，重复抓取不会产生重复新闻
"""

from __future__ import annotations

import hashlib
import html
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone, UTC
from typing import Any
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import feedparser
import httpx
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.news import News
from models.rss import RssFeed

logger = logging.getLogger(__name__)

CST = ZoneInfo("Asia/Shanghai")
USER_AGENT = "Mozilla/5.0 (compatible; ToutiaoRSS/1.0)"
MAX_BYTES = 5 * 1024 * 1024
MAX_ENTRIES = 200
MAX_CONTENT = 15_000  # TEXT 列 64KB，按 utf8mb4 最坏 4 字节/字算，1.5 万字符是安全线


@dataclass
class IngestResult:
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0
    status: str = "ok"


def html_to_text(raw: str | None) -> str:
    if not raw:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|blockquote|tr)\s*>", "\n\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


# RSS 摘要末尾常带“查看全文”这类链接文字，HTML 清洗后只剩纯文本，
# 去掉它，改用详情页底部的“查看全文”按钮。
_READ_MORE_RE = re.compile(r"[\s.…·]*(?:查看全文|查看原文|阅读原文|阅读更多|(?<!可)阅读全文)\s*$")


def strip_read_more(text: str | None) -> str:
    return _READ_MORE_RE.sub("", text or "").strip()


def entry_hash(entry: Any) -> str:
    base = (
        entry.get("id")
        or entry.get("link")
        or f"{entry.get('title', '')}|{entry.get('published', '')}"
    )
    return hashlib.sha256(base.strip().encode("utf-8")).hexdigest()


def entry_time(entry: Any) -> datetime:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=UTC).astimezone(CST).replace(tzinfo=None)
    return datetime.now(CST).replace(tzinfo=None)


def entry_image(entry: Any, base_url: str) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key) or []:
            if media.get("url"):
                return urljoin(base_url, media["url"])
    for enc in entry.get("enclosures") or []:
        if (enc.get("type") or "").startswith("image/") and enc.get("href"):
            return urljoin(base_url, enc["href"])
    body = (entry.get("content") or [{}])[0].get("value") or entry.get("summary") or ""
    match = re.search(r'<img[^>]+src=["\']([^"\']+)', body, re.I)
    return urljoin(base_url, match.group(1)) if match else None


def _normalize(parsed: Any, feed: RssFeed, limit: int) -> list[dict[str, Any]]:
    site = parsed.feed.get("link") or feed.site_url or feed.url
    items: list[dict[str, Any]] = []
    for entry in parsed.entries[:limit]:
        link = urljoin(site, entry.get("link") or "") or feed.url
        summary = strip_read_more(html_to_text(entry.get("summary")))
        body = (
            strip_read_more(html_to_text((entry.get("content") or [{}])[0].get("value"))) or summary
        )
        image = entry_image(entry, link)
        author = html_to_text(entry.get("author")) or None
        items.append(
            {
                "title": (html_to_text(entry.get("title")) or "无标题")[:300],
                "description": (summary or body)[:500] or None,
                "content": body[:MAX_CONTENT] or "（该源仅提供标题，点击查看原文）",
                "image": image[:1000] if image else None,
                "author": author[:50] if author else None,
                "category_id": feed.category_id,
                "feed_id": feed.id,
                "guid_hash": entry_hash(entry),
                "source_url": link[:1000],
                "publish_time": entry_time(entry),
                "views": 0,
                "is_top": False,
            }
        )
    return items


def _parse(payload: bytes, feed: RssFeed):
    parsed = feedparser.parse(payload)
    if parsed.bozo:
        logger.warning("feed 解析告警 url=%s err=%s", feed.url, parsed.bozo_exception)
    # HTTP 200 但返回验证页/HTML 时 entries 为空，不能当成“源正常但没更新”
    if not parsed.entries and not parsed.get("version"):
        raise ValueError("返回内容不是有效的 RSS/Atom")
    return parsed


def parse_entries(payload: bytes, feed: RssFeed, limit: int = MAX_ENTRIES) -> list[dict[str, Any]]:
    """只解析不落库，CLI --dry-run、preview 接口和单测都走这里。"""
    return _normalize(_parse(payload, feed), feed, limit)


async def fetch_and_store(
    session: AsyncSession,
    feed: RssFeed,
    client: httpx.AsyncClient,
    limit: int = MAX_ENTRIES,
) -> IngestResult:
    """抓一次并写库。不 commit，由调用方统一提交。"""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
    }
    if feed.etag:
        headers["If-None-Match"] = feed.etag
    if feed.last_modified:
        headers["If-Modified-Since"] = feed.last_modified

    result = IngestResult()
    feed.last_fetch_at = datetime.now(CST).replace(tzinfo=None)
    try:
        resp = await client.get(feed.url, headers=headers)
        if resp.status_code == 304:
            feed.last_status, feed.last_error, feed.error_count = (
                "not_modified",
                None,
                0,
            )
            result.status = "not_modified"
            return result
        resp.raise_for_status()
        if len(resp.content) > MAX_BYTES:
            raise ValueError(f"feed 超过 {MAX_BYTES} 字节")

        parsed = _parse(resp.content, feed)
        items = _normalize(parsed, feed, limit)
        result.fetched = len(items)

        if items:
            hashes = [item["guid_hash"] for item in items]
            existing = set(
                (
                    await session.execute(
                        select(News.guid_hash).where(
                            News.feed_id == feed.id,
                            News.guid_hash.in_(hashes),
                        )
                    )
                ).scalars()
            )
            fresh = [item for item in items if item["guid_hash"] not in existing]
            if fresh:
                # INSERT IGNORE 兜住并发下的重复键；长度已在上游截断
                await session.execute(insert(News).prefix_with("IGNORE"), fresh)
            result.inserted = len(fresh)
            result.skipped = len(items) - len(fresh)

        feed.last_status, feed.last_error, feed.error_count = "ok", None, 0
        feed.etag = resp.headers.get("etag") or None
        feed.last_modified = resp.headers.get("last-modified") or None
        if not feed.site_url:
            feed.site_url = parsed.feed.get("link") or None
        return result

    except Exception as exc:  # 网络/解析/长度问题都收敛成状态，不打断其它源
        feed.last_status = "error"
        feed.last_error = str(exc)[:500]
        feed.error_count = (feed.error_count or 0) + 1
        result.status = "error"
        logger.warning("RSS 抓取失败 url=%s: %s", feed.url, exc)
        return result


def assert_public_http_url(url: str, allowed_hosts: set[str] | None = None) -> None:
    """禁止内网/回环地址，避免管理接口变成 SSRF 跳板。

    allowed_hosts 用于放行本地 RSSHub 这类明确可信的主机。
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("只支持 http/https 地址")
    if allowed_hosts and parsed.hostname in allowed_hosts:
        return
    for info in socket.getaddrinfo(parsed.hostname, None):
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("不允许访问内网地址")
