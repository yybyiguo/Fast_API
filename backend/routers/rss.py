import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cache.news_cache import invalidate_categories, invalidate_news_list
from config.db_config import get_db, settings
from curd import rss
from models.rss import RssFeed
from models.user import User
from schemas.rss import RssFeedIn, RssFeedOut, RssFeedPatch
from services.rss_fetcher import USER_AGENT, assert_public_http_url, parse_entries
from utils.auth import require_rss_admin
from utils.request_context import get_request_id
from utils.response import success_response
from utils.traffic import limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/rss",
    tags=["rss"],
    dependencies=[Depends(limit("rss", 30, 60))],
)


async def _check_url(url: str) -> str:
    """校验地址并补全 RSSHub 路径；不合法统一回 422，而不是 500。"""
    url = url.strip()
    if url.startswith("/"):
        url = f"{settings.rsshub_base.rstrip('/')}{url}"
    try:
        await asyncio.to_thread(assert_public_http_url, url, settings.rss_private_host_set)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return url


def _parse_or_422(payload: bytes, feed: RssFeed, limit: int) -> list[dict]:
    try:
        return parse_entries(payload, feed, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/feeds")
async def list_feeds(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_rss_admin),
):
    feeds = await rss.list_feeds(db)
    return success_response(data=[RssFeedOut.model_validate(item) for item in feeds])


@router.post("/feeds")
async def create_feed(
    data: RssFeedIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_rss_admin),
):
    data.url = await _check_url(data.url)
    try:
        feed = await rss.create_feed(db, data)
        await db.commit()
        await db.refresh(feed)
    except IntegrityError as exc:
        await db.rollback()
        message = str(exc.orig)
        if "FOREIGN KEY" in message:
            raise HTTPException(status_code=422, detail="分类不存在") from exc
        if "news_categories" in message:
            raise HTTPException(status_code=409, detail="源名称已被占用，换一个名字") from exc
        raise HTTPException(status_code=409, detail="该 Feed URL 已存在") from exc

    # 新源自动建了同名分类，首页的 tab 缓存要立刻失效
    await invalidate_categories()

    # 建完顺手抓一次，用户不用再点“立即抓取”
    try:
        from tasks.rss_tasks import fetch_feed as fetch_feed_task

        fetch_feed_task.delay(feed.id, get_request_id())
    except Exception:
        logger.warning("新源入队失败 feed_id=%s", feed.id)

    return success_response(message="创建成功", data=RssFeedOut.model_validate(feed))


@router.patch("/feeds/{feed_id}")
async def update_feed(
    feed_id: int,
    data: RssFeedPatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_rss_admin),
):
    feed = await rss.get_feed(db, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="源不存在")
    if data.url is not None:
        data.url = await _check_url(data.url)
    try:
        # update_feed 内部会 flush，外键错误在这里就会抛，不能等到 commit
        feed = await rss.update_feed(db, feed, data)
        await db.commit()
        await db.refresh(feed)
    except IntegrityError as exc:
        await db.rollback()
        message = str(exc.orig)
        # 外键错误优先判：它的信息里也包含 news_categories
        if "FOREIGN KEY" in message:
            raise HTTPException(status_code=422, detail="分类不存在") from exc
        if "url" in message:
            raise HTTPException(status_code=409, detail="该 Feed URL 已存在") from exc
        if "news_categories" in message:
            raise HTTPException(status_code=409, detail="源名称已被占用") from exc
        raise HTTPException(status_code=422, detail="分类不存在") from exc

    # 改了名字的话，首页 tab 要跟着变
    await invalidate_categories()
    return success_response(message="更新成功", data=RssFeedOut.model_validate(feed))


@router.delete("/feeds/{feed_id}")
async def delete_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_rss_admin),
):
    feed = await rss.get_feed(db, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="源不存在")

    removed_category = await rss.delete_feed(db, feed)
    await db.commit()

    await invalidate_categories()
    if removed_category is not None:
        # 这个分类已经没有文章也没别的源，顺手清掉它的空列表缓存
        await invalidate_news_list(removed_category)

    return success_response(message="删除成功")


@router.post("/feeds/{feed_id}/refresh")
async def refresh_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_rss_admin),
):
    feed = await rss.get_feed(db, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="源不存在")
    from tasks.rss_tasks import fetch_feed as fetch_feed_task

    task = fetch_feed_task.delay(feed.id, get_request_id())
    return success_response(message="已入队", data={"taskId": task.id})


@router.get("/preview")
async def preview(
    url: str = Query(..., max_length=500),
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(require_rss_admin),
):
    url = await _check_url(url)
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"抓取失败：{exc}") from exc

    feed = RssFeed(name="preview", url=url, category_id=0)
    items = _parse_or_422(resp.content, feed, limit)
    return success_response(data=items)


@router.post("/discover")
async def discover(
    body: dict,
    user: User = Depends(require_rss_admin),
):
    """给个站点首页，自动找 RSS/Atom 地址。"""
    import re
    from urllib.parse import urljoin

    site = (body.get("siteUrl") or "").strip()
    if not site:
        raise HTTPException(status_code=422, detail="siteUrl 不能为空")
    site = await _check_url(site)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(site)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"抓取失败：{exc}") from exc

    found = []
    for tag in re.findall(r"<link\b[^>]*>", resp.text, re.I):
        if re.search(r'type=["\']application/(rss|atom)\+xml', tag, re.I):
            href = re.search(r'href=["\']([^"\']+)', tag, re.I)
            if href:
                found.append(urljoin(site, href.group(1)))

    return success_response(data=list(dict.fromkeys(found)))
