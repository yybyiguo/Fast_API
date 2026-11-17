from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from curd import news
from services import news_detail, news_views
from utils.traffic import limit

router = APIRouter(
    prefix="/api/news",
    tags=["news"],
    dependencies=[Depends(limit("news", 120, 60))],
)


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100):
    categories = await news.get_categories(db, skip, limit)
    return {"code": 200, "msg": "获取分类成功", "data": categories}


@router.get("/list")
async def get_news_list(
    categories_id: int = Query(..., alias="categoryId"),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pagesize", ge=1, le=100),
):
    offset = (page - 1) * page_size
    news_list = await news.get_news_list(categories_id, db, offset, page_size)
    # 正文缓存里没有 views，返回前统一从计数器补；计数器缺失时这批函数会回库回填
    await news_views.attach_views(db, news_list)

    totol = await news.get_news_count(db, categories_id)
    hasmore = (offset + len(news_list)) < totol
    return {
        "code": 200,
        "msg": "获取news_list成功",
        "data": {"list": news_list, "totol": totol, "hasmore": hasmore},
    }


@router.get("/detail")
async def get_news_detail(
    response: Response,
    news_id: int = Query(..., alias="id"),
    db: AsyncSession = Depends(get_db),
):
    payload, known_views, cache_status = await news_detail.load(db, news_id)
    # 本次请求的缓存结局：HIT / NEGATIVE / MISS，方便 curl 和前端排障
    response.headers["X-Cache"] = cache_status

    if payload is None:
        # raise 之后上面设置的 response 会被丢掉，header 要在这里再带一次
        raise HTTPException(
            status_code=404,
            detail="不存在",
            headers={"X-Cache": cache_status},
        )

    # views 不进正文缓存：Redis 计数器是唯一真相源，这里是自增后的总数
    views = await news_views.increment(db, news_id, known_db_views=known_views)

    related = await news.get_related_news(db, news_id, payload["categoryId"], 10)
    await news_views.attach_views(db, related)

    # payload 里是正文（不含 views），响应时再把计数和相关推荐拼进去
    return {
        "code": 200,
        "msg": "获取详情成功",
        "data": {**payload, "views": views, "relatedNews": related},
    }
