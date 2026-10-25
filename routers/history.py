from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from curd import history
from curd.history import add_user_history
from models.user import User
from schemas.history import HistoryListResponse
from utils import auth
from utils.response import success_response

router=APIRouter(prefix='/api/history',tags=['history'])


@router.post('/add_history')
async def add_history(
    news_id:int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth.get_current_user),
):
    result = await add_user_history(db,news_id,user.id,datetime.now())
    if result :
        await db.commit()
        return success_response(message='添加成功')
    else:
        return success_response(message="添加失败")


@router.get("/list")
async def get_favorite_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pagesize", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth.get_current_user),
):

    offset = (page - 1) * page_size
    result = await history.get_list(db, user.id, offset, page_size)
    total = await history.get_count(db, user.id)
    has_more = offset + len(result) < total

    return success_response(
        message="暂无历史记录" if not result else "success",
        data=HistoryListResponse(list=result, total=total, has_more=has_more),
    )


@router.delete('/delete')
async def delete_one_history(news_id:int,db: AsyncSession = Depends(get_db),user: User = Depends(auth.get_current_user)):
    result = await history.delete_history(db,user.id,news_id)
    if result:
        await db.commit()
        return success_response(message='删除成功',data=result)

@router.delete('/clear')
async def clear_history(user:User=Depends(auth.get_current_user),db: AsyncSession = Depends(get_db)):
    num = await history.delete_all_history(db, user.id)
    await db.commit()
    return success_response(message="删除成功", data=f"删除{num}条数据")
