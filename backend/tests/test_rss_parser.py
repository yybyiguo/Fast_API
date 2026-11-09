"""RSS 解析的纯函数测试，不连数据库、不联网。"""

import pytest

from models.rss import RssFeed
from services.rss_fetcher import (
    assert_public_http_url,
    html_to_text,
    parse_entries,
    strip_read_more,
)

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>test</title>
  <link href="https://example.com/"/>
  <entry>
    <title>First &amp; Title</title>
    <link href="https://example.com/p/1"/>
    <id>tag:example.com,2026:1</id>
    <updated>2026-01-01T00:00:00Z</updated>
    <summary>summary &lt;b&gt;bold&lt;/b&gt;</summary>
    <content type="html">&lt;p&gt;para one&lt;/p&gt;&lt;p&gt;para two&lt;img src="/cover.jpg"&gt;&lt;/p&gt;</content>
  </entry>
</feed>
"""


def _feed() -> RssFeed:
    return RssFeed(name="test", url="https://example.com/feed", category_id=1)


def test_html_to_text():
    assert html_to_text("<p>a</p><p>b</p>") == "a\n\nb"
    assert html_to_text("a<br>b") == "a\nb"
    assert html_to_text("<script>x()</script>hello") == "hello"
    assert html_to_text(None) == ""


def test_strip_read_more():
    # 摘要末尾的链接文字要清掉，但句号要保留
    assert strip_read_more("正文 ...查看全文") == "正文"
    assert strip_read_more("正文。查看全文") == "正文。"
    # 付费文章里的“可阅读全文”是正文，不能误删
    assert strip_read_more("订阅后可阅读全文。") == "订阅后可阅读全文。"
    assert strip_read_more(None) == ""


def test_parse_atom_entry():
    items = parse_entries(ATOM, _feed())
    assert len(items) == 1

    item = items[0]
    assert item["title"] == "First & Title"
    # UTC 00:00 必须转成北京时间 08:00
    assert item["publish_time"].hour == 8
    assert "para one" in item["content"]
    assert "<p>" not in item["content"]
    assert item["image"] == "https://example.com/cover.jpg"
    assert item["source_url"] == "https://example.com/p/1"
    assert len(item["guid_hash"]) == 64


def test_parse_rejects_non_feed():
    with pytest.raises(ValueError):
        parse_entries(b"<html><body>cloudflare</body></html>", _feed())


def test_entry_hash_is_stable():
    first = parse_entries(ATOM, _feed())[0]["guid_hash"]
    second = parse_entries(ATOM, _feed())[0]["guid_hash"]
    assert first == second


def test_private_host_rejected_by_default():
    with pytest.raises(ValueError, match="内网"):
        assert_public_http_url("http://127.0.0.1:1200/feed")


def test_private_host_allowed_when_configured():
    assert_public_http_url("http://127.0.0.1:1200/feed", allowed_hosts={"127.0.0.1"})


def test_non_http_scheme_rejected():
    with pytest.raises(ValueError, match="http"):
        assert_public_http_url("ftp://example.com/feed")
