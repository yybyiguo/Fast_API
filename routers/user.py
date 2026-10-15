from fastapi import APIRouter, Depends, HTTPException,Query
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from config.db_config import get_db
from schemas.users import UserRequest
from curd import user
from starlette import status

router=APIRouter(prefix='/api/user',tags=['user'])

@router.post('/register')
async def register(userData:UserRequest,db:AsyncSession=Depends(get_db)):
    existing_user=await user.get_user_by_username(db,userData.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='该用户已经存在')
    users= await user.create_user(db,userData)
    token= await user.create_token(db,users.id)
    return {
        "code":200,
        "msg":'注册成功',
        'data':{
            'token':token,
            'userInfo':{
                'id':users.id,
                'username':users.username,
                'bio':users.bio,
                'avatar':users.avatar
            }
        }
        }
