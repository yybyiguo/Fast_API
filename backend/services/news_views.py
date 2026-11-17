"""views 从正文拆出来后的统一读写。

规则只有一条：任何返回 views 的地方都读同一个计数器；
计数器缺失时用数据库当前值回填，绝不拿缓存里的旧值播种。
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from cache import view_counter
from curd import news as news_crud

logger = logging.getLogger(__name__)


async def attach_views(db: AsyncSession, items: list[dict]) -> list[dict]:
    """给列表/相关推荐的条目补上 views（原地修改并返回）。

    - 计数器命中：直接用；
    - 计数器缺失：只用一条 IN 查询拿数据库当前值，展示并 SET NX 回填。
      不能省这一步，否则新文章会显示 0、老文章会显示缓存里的旧值。
    """
    if not items:
        return items

    ids = [int(item["id"]) for item in items]
    values = await view_counter.read_many(ids)
    missing = [news_id for news_id, value in zip(ids, values, strict=False) if value is None]

    fallback: dict[int, int] = {}
    if missing:
        fallback = await news_crud.get_views_map(db, missing)
        await view_counter.seed_many([(news_id, fallback.get(news_id, 0)) for news_id in missing])

    for item, value in zip(items, values, strict=False):
        if value is not None:
            item["views"] = int(value)
        else:
            item["views"] = int(fallback.get(int(item["id"]), 0))
    return items


async def increment(db: AsyncSession, news_id: int, known_db_views: int | None = None) -> int:
    """给详情页加一次浏览，返回自增后的总数。

    known_db_views 是刚才查库顺手拿到的值，能省一次查询；
    详情命中缓存时没有这个值，计数器又恰好缺失，才回库读一次。
    """
    current = await view_counter.read(news_id)
    if current is None:
        base = known_db_views
        if base is None:
            base = (await news_crud.get_views_map(db, [news_id])).get(news_id)
        if base is None:
            return 0
        await view_counter.seed(news_id, base)
        current = base

    bumped = await view_counter.bump(news_id)
    if bumped is None:
        # Redis 挂了：显示数据库里的值，不把详情页拖垮
        return int(current)
    return int(bumped)
