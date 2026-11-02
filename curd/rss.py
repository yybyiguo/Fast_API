from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.rss import RssFeed
from schemas.rss import RssFeedIn, RssFeedPatch


async def list_feeds(db: AsyncSession) -> list[RssFeed]:
    return (await db.execute(select(RssFeed).order_by(RssFeed.id))).scalars().all()


async def get_feed(db: AsyncSession, feed_id: int) -> RssFeed | None:
    return await db.get(RssFeed, feed_id)


async def create_feed(db: AsyncSession, data: RssFeedIn) -> RssFeed:
    feed = RssFeed(**data.model_dump())
    db.add(feed)
    await db.flush()
    return feed


async def update_feed(db: AsyncSession, feed: RssFeed, data: RssFeedPatch) -> RssFeed:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(feed, field, value)
    await db.flush()
    return feed
