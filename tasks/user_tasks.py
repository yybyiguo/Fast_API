"""清理过期的 token。每 1 小时跑一次。

练习说明：
    文件里有 3 处 ____，每处对应一个关键决策。
    其他代码是现成的，不用改。填完把整个文件发我。
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.db_config import DB_URL
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _clean_once() -> int:
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)
    try:
        async with async_sessionmaker(bind=engine, expire_on_commit=False)() as db:
            result = await db.execute(
                text("DELETE FROM user_token WHERE expires_at < :now"),
                # ── 空 1 ──────────────────────────────────────────────
                # now 传什么？
                # 提示：要和你 curd/user.py 里写 expires_at 时用的是同一个时钟。
                #       那边是 datetime.now() + timedelta(days=7)，本地时间、naive。
                #       如果你填 datetime.utcnow() 或带时区的，会发生什么？
                {"now": datetime.now()},
            )
            # ── 空 2 ──────────────────────────────────────────────
            # 删除语句执行完，还需要做什么，数据才会真的落库？
            await db.commit()
            # ── 空 3 ──────────────────────────────────────────────
            # 怎么拿到"这次删了几条"？result 的哪个属性？
            return result.rowcount or 0
    finally:
        await engine.dispose()


@celery_app.task(name="tasks.user_tasks.clean_expired_tokens")
def clean_expired_tokens() -> int:
    try:
        deleted = asyncio.run(_clean_once())
        logger.info("清理过期 token 完成，删除 %s 条", deleted)
        return deleted
    except Exception:
        logger.exception("清理过期 token 失败")
        return 0
