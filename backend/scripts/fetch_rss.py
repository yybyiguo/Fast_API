"""手工抓取单个 RSS 源，不依赖 Celery。

用法：
    python -m scripts.fetch_rss https://sspai.com/feed --dry-run
    python -m scripts.fetch_rss https://sspai.com/feed --name 少数派
    python -m scripts.fetch_rss --feed-id 1
    python -m scripts.fetch_rss --feed-id 1 --force
    python -m scripts.fetch_rss --list
"""

import argparse
import asyncio
import sys
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from cache.news_cache import invalidate_categories, invalidate_news_list
from config.db_config import AsyncSessionLocal, async_engine
from curd import rss as rss_curd
from models.rss import RssFeed
from schemas.rss import RssFeedIn
from services.rss_fetcher import USER_AGENT, fetch_and_store, parse_entries


def _print_items(items: list[dict]) -> None:
    for index, item in enumerate(items, 1):
        print(f"{index:>2}. [{item['publish_time']:%m-%d %H:%M}] {item['title'][:50]}")
        print(
            f"    正文 {len(item['content'])} 字 | 图片 {'有' if item['image'] else '无'}"
            f" | {item['source_url'][:80]}"
        )


async def _run(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=8.0),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        if args.dry_run:
            if args.feed_id:
                async with AsyncSessionLocal() as db:
                    stored = await db.get(RssFeed, args.feed_id)
                if stored is None:
                    sys.exit(f"源不存在: {args.feed_id}")
                url, name, category_id = stored.url, stored.name, stored.category_id
            else:
                url, name, category_id = (
                    args.url,
                    args.name or "dry-run",
                    args.category or 0,
                )
            feed = RssFeed(name=name, url=url, category_id=category_id)
            resp = await client.get(feed.url)
            resp.raise_for_status()
            items = parse_entries(resp.content, feed, limit=args.limit)
            print(f"解析到 {len(items)} 条：")
            _print_items(items)
            return

        async with AsyncSessionLocal() as db:
            feed = None
            created = False
            if args.feed_id:
                feed = await db.get(RssFeed, args.feed_id)
            elif args.url:
                feed = (
                    await db.execute(select(RssFeed).where(RssFeed.url == args.url))
                ).scalar_one_or_none()
                if feed is None:
                    host = urlparse(args.url).hostname or args.url[:100]
                    data = RssFeedIn(
                        name=args.name or host,
                        url=args.url,
                        category_id=args.category,
                        fetch_interval=args.interval,
                    )
                    try:
                        # 和 Web 端同一条路径：自动建同名分类
                        feed = await rss_curd.create_feed(db, data)
                        await db.flush()
                        created = True
                    except IntegrityError as exc:
                        await db.rollback()
                        sys.exit(f"创建源失败: {exc.orig}")
            if feed is None:
                sys.exit("源不存在：检查 --feed-id / url")

            result = await fetch_and_store(
                db,
                feed,
                client,
                limit=args.limit,
                force=args.force or bool(args.feed_id),
            )
            await db.commit()

            if result.inserted:
                await invalidate_news_list(feed.category_id)
            if created:
                await invalidate_categories()

            print(
                f"源 #{feed.id} {feed.name}: status={result.status} "
                f"解析={result.fetched} 新增={result.inserted} 跳过={result.skipped} "
                f"错误={feed.last_error or '-'}"
            )


async def _list() -> None:
    async with AsyncSessionLocal() as db:
        feeds = (await db.execute(select(RssFeed).order_by(RssFeed.id))).scalars().all()
    for feed in feeds:
        print(
            f"#{feed.id} {feed.name} [{feed.last_status or '未抓取'}] "
            f"interval={feed.fetch_interval}s category={feed.category_id} {feed.url}"
        )


async def _amain(args: argparse.Namespace) -> None:
    try:
        if args.list:
            await _list()
        else:
            await _run(args)
    finally:
        # 全局连接池的连接绑在当前事件循环上；不主动 dispose 的话，
        # asyncio.run 关掉 loop 后连接才被 GC，aiomysql.__del__ 会报 Event loop is closed
        await async_engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?")
    parser.add_argument("--feed-id", type=int)
    parser.add_argument("--category", type=int)
    parser.add_argument("--name")
    parser.add_argument("--interval", type=int, default=900)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="忽略 ETag，强制回源")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if not args.list and not args.url and not args.feed_id:
        parser.error("需要 url 或 --feed-id")
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
