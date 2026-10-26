from fastapi import APIRouter, Depends, HTTPException,Query
from curd import news
from sqlalchemy.ext.asyncio import  AsyncSession
from config.db_config import get_db
import logging

logger = logging.getLogger(__name__)


router=APIRouter(prefix='/api/news',tags=['news'])

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db),skip:int=0,limit:int=100):
    categories=await news.get_categories(db,skip,limit)
    return {
        "code":200,
        "msg":'获取分类成功',
        'data':categories
        }


@router.get('/list')
async def get_news_list(
    categories_id:int=Query(...,alias='categoryId'),
    db: AsyncSession = Depends(get_db),
    page:int=1,
    page_size:int=Query(10,alias='pagesize',le=100)):
    offset=(page-1)*page_size
    news_list=await news.get_news_list(categories_id,db,offset,page_size)
    totol= await news.get_news_count(db,categories_id)
    hasmore=(offset+len(news_list))<totol
    return {
        "code":200,
        "msg":'获取news_list成功',
        'data':{
            'list':news_list,
            'totol':totol,
            'hasmore':hasmore
        }
        }

@router.get('/detail')
async def get_news_detail(news_id:int=Query(...,alias='id'), db: AsyncSession = Depends(get_db)):
    try:
        views_result=await news.increase_news_views(db,news_id)
        if not views_result:
            raise HTTPException(status_code=404,detail='这不存在')
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        # 事务已进入失败状态，必须回滚，否则同一个 session 后面的 SELECT 会报 PendingRollbackError
        await db.rollback()
        logger.warning("增加浏览量失败", exc_info=True)
    result= await news.get_news_detail(db,news_id)
    if not result:
        raise HTTPException(status_code=404,detail='不存在')
    relatedNews=await news.get_related_news(db,news_id,result.category_id,10)
    return {
        "code":200,
        "msg":'获取详情成功',
        'data':{
            'id':result.id,
            'title':result.title,
            'author':result.author,
            'image':result.image,
            'publishTime':result.publish_time,
            'categoryId':result.category_id,
            'content':result.content,
            'views':result.views,
            'relatedNews':relatedNews
        }
        }
