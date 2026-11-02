"""造测试数据：批量插入新闻，用于观察慢查询。

用法：
    python -m scripts.seed_news 100000     # 造 10 万条
    python -m scripts.seed_news --clean    # 清空 news 表

三个设计点：
    1. 批量插入（一条 INSERT 带 1000 行），而不是循环 10 万次单条 INSERT
    2. 每批 commit，不攒一个大事务（否则 undo log 撑爆、锁持太久）
    3. views 用长尾分布，不是均匀分布 —— 真实世界里少数爆款、多数冷门
"""

import asyncio
import random
import sys
import time
from datetime import datetime, timedelta

from sqlalchemy import text

from config.db_config import AsyncSessionLocal

BATCH_SIZE = 1000
CATEGORY_COUNT = 5


async def ensure_categories(db) -> None:
    for i in range(1, CATEGORY_COUNT + 1):
        await db.execute(
            text(
                "INSERT INTO news_categories (id, name, sort_order, create_time, update_time) "
                "VALUES (:id, :name, :sort, NOW(), NOW()) "
                "ON DUPLICATE KEY UPDATE name = VALUES(name)"
            ),
            {"id": i, "name": f"分类{i}", "sort": i},
        )
    await db.commit()


async def seed(total: int) -> None:
    async with AsyncSessionLocal() as db:
        await ensure_categories(db)

        start = time.perf_counter()
        inserted = 0
        now = datetime.now()

        while inserted < total:
            n = min(BATCH_SIZE, total - inserted)
            placeholders = []
            params = {}

            for j in range(n):
                k = inserted + j
                placeholders.append(f"(:t{k}, :d{k}, :c{k}, :cid{k}, :v{k}, :p{k})")
                params[f"t{k}"] = f"新闻标题 {k}"
                params[f"d{k}"] = f"新闻简介 {k}"
                params[f"c{k}"] = f"这是第 {k} 条新闻的正文内容。"
                params[f"cid{k}"] = random.randint(1, CATEGORY_COUNT)
                # 长尾：4 次方压低绝大多数值，少数接近 10 万
                params[f"v{k}"] = int(100_000 * (random.random() ** 4))
                params[f"p{k}"] = now - timedelta(
                    days=random.randint(0, 365),
                    seconds=random.randint(0, 86_400),
                )

            sql = (
                "INSERT INTO news (title, description, content, category_id, views, publish_time) "
                "VALUES " + ",".join(placeholders)
            )
            await db.execute(text(sql), params)
            await db.commit()

            inserted += n
            if inserted % 20_000 == 0 or inserted == total:
                print(f"  已插入 {inserted}/{total}  ({time.perf_counter() - start:.1f}s)")

        print(f"完成：{inserted} 条，总耗时 {time.perf_counter() - start:.1f}s")


async def clean() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        await db.execute(text("TRUNCATE TABLE news"))
        await db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    print("已清空 news 表")


def main() -> None:
    nums = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--clean" in sys.argv:
        asyncio.run(clean())
        return
    asyncio.run(seed(int(nums[0]) if nums else 100_000))


if __name__ == "__main__":
    main()
