from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.news import Category, News
from models.rss import RssFeed
from schemas.rss import RssFeedIn, RssFeedPatch


async def list_feeds(db: AsyncSession) -> list[RssFeed]:
    return (await db.execute(select(RssFeed).order_by(RssFeed.id))).scalars().all()


async def get_feed(db: AsyncSession, feed_id: int) -> RssFeed | None:
    return await db.get(RssFeed, feed_id)


async def _category_name(db: AsyncSession, name: str, exclude_id: int | None = None) -> str:
    """分类名要唯一：重名时自动加序号，避免两个源共用一个 tab。"""
    base = (name or "").strip()[:50] or "未命名"
    candidate = base
    index = 2
    while True:
        stmt = select(Category.id).where(Category.name == candidate)
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        if await db.scalar(stmt) is None:
            return candidate
        suffix = f" {index}"
        candidate = f"{base[: 50 - len(suffix)]}{suffix}"
        index += 1


async def create_feed(db: AsyncSession, data: RssFeedIn) -> RssFeed:
    """建源时自动建一个同名分类，首页 tab 直接显示这个名字。"""
    category_id = data.category_id
    if category_id is None:
        max_sort = await db.scalar(select(func.max(Category.sort_order))) or 0
        category = Category(
            name=await _category_name(db, data.name),
            sort_order=max_sort + 1,
        )
        db.add(category)
        await db.flush()
        category_id = category.id

    feed = RssFeed(
        category_id=category_id,
        **data.model_dump(exclude={"category_id"}),
    )
    db.add(feed)
    await db.flush()
    return feed


async def update_feed(db: AsyncSession, feed: RssFeed, data: RssFeedPatch) -> RssFeed:
    values = data.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(feed, field, value)

    # 改名时同步 tab 名称，否则首页还显示旧名字
    if "name" in values:
        category = await db.get(Category, feed.category_id)
        if category is not None:
            category.name = await _category_name(db, feed.name, exclude_id=category.id)

    # 换了地址就当作新源，清空旧地址的抓取状态，等待下一次抓取
    if "url" in values:
        feed.site_url = None
        feed.last_fetch_at = None
        feed.last_status = None
        feed.last_error = ""
        feed.error_count = 0

    await db.flush()
    return feed


async def delete_feed(db: AsyncSession, feed: RssFeed) -> int | None:
    """删源；如果分类既没有文章也没有别的源，一起清掉，避免留下空 tab。"""
    category_id = feed.category_id
    await db.delete(feed)
    await db.flush()

    news_count = await db.scalar(
        select(func.count()).select_from(News).where(News.category_id == category_id)
    )
    feed_count = await db.scalar(
        select(func.count()).select_from(RssFeed).where(RssFeed.category_id == category_id)
    )
    if not news_count and not feed_count:
        await db.execute(delete(Category).where(Category.id == category_id))
        return category_id
    return None
