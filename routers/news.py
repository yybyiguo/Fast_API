from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cache import view_counter
from config.db_config import get_db
from curd import news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100):
    categories = await news.get_categories(db, skip, limit)
    return {"code": 200, "msg": "获取分类成功", "data": categories}


@router.get("/list")
async def get_news_list(
    categories_id: int = Query(..., alias="categoryId"),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = Query(10, alias="pagesize", le=100),
):
    offset = (page - 1) * page_size
    news_list = await news.get_news_list(categories_id, db, offset, page_size)
    totol = await news.get_news_count(db, categories_id)
    hasmore = (offset + len(news_list)) < totol
    return {
        "code": 200,
        "msg": "获取news_list成功",
        "data": {"list": news_list, "totol": totol, "hasmore": hasmore},
    }


@router.get("/detail")
async def get_news_detail(
    news_id: int = Query(..., alias="id"), db: AsyncSession = Depends(get_db)
):
    result = await news.get_news_detail(db, news_id)
    if not result:
        raise HTTPException(status_code=404, detail="不存在")

    # 浏览量只写 Redis（微秒级），不再 UPDATE 数据库，避免热门新闻被行锁拖死。
    # 数据库里的数字由后台任务定时批量回写。
    await view_counter.increase(news_id)

    relatedNews = await news.get_related_news(db, news_id, result.category_id, 10)
    return {
        "code": 200,
        "msg": "获取详情成功",
        "data": {
            "id": result.id,
            "title": result.title,
            "author": result.author,
            "image": result.image,
            "publishTime": result.publish_time,
            "categoryId": result.category_id,
            "content": result.content,
            # RSS 文章原文链接，前端详情页的“查看全文”按钮依赖它
            "sourceUrl": result.source_url,
            # 数据库里的值 + 还没落库的 Redis 增量，用户刷新能看到实时增长
            "views": result.views + await view_counter.pending(news_id),
            "relatedNews": relatedNews,
        },
    }
