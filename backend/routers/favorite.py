from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from curd import favorite
from models.user import User
from schemas.favorite import FavoriteCheckResponse, FavoriteListResponse
from utils import auth
from utils.response import success_response
from utils.traffic import limit

router = APIRouter(
    prefix="/api/favorite",
    tags=["favorite"],
    dependencies=[Depends(limit("favorite", 60, 60))],
)


@router.get("/check")
async def check_favorite(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth.get_current_user),
):
    ischecked = await favorite.is_favorite(db, user.id, news_id)

    return success_response(message="check成功", data=FavoriteCheckResponse(is_favorite=ischecked))


@router.post("/shift")
async def shift_favorite(
    news_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(auth.get_current_user)
):
    ischecked = await favorite.is_favorite(db, user.id, news_id)
    if not ischecked:
        try:
            result = await favorite.add_favorite(db, user.id, news_id)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return success_response(message="已收藏", data=None)
        return success_response(message="添加收藏成功", data=result)
    else:
        await favorite.delete_favorite(db, user.id, news_id)
        await db.commit()
        return success_response(message="删除收藏成功", data=None)


@router.get("/list")
async def get_favorite_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, alias="pagesize", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth.get_current_user),
):

    offset = (page - 1) * page_size
    result = await favorite.get_list(db, user.id, offset, page_size)
    total = await favorite.get_count(db, user.id)
    has_more = offset + len(result) < total

    return success_response(
        message="暂无收藏" if not result else "success",
        data=FavoriteListResponse(list=result, total=total, has_more=has_more),
    )


@router.delete("/clear")
async def clear_favorite(
    user: User = Depends(auth.get_current_user), db: AsyncSession = Depends(get_db)
):
    num = await favorite.delete_all_favorite(db, user.id)
    await db.commit()
    return success_response(message="删除成功", data=f"删除{num}条数据")
