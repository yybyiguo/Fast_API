from fastapi import APIRouter, Depends, HTTPException,Query
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from config.db_config import get_db
from models.user import User
from schemas.users import UserRequest, userAuthResponse, userInfoResponse, userUpdateRequest
from curd import user
from starlette import status

from utils import auth
from utils.response import success_response

router=APIRouter(prefix='/api/user',tags=['user'])

@router.post('/register')
async def register(userData:UserRequest,db:AsyncSession=Depends(get_db)):
    existing_user=await user.get_user_by_username(db,userData.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='该用户已经存在')
    users= await user.create_user(db,userData)
    token= await user.create_token(db,users.id)
    return success_response(message='注册成功',data=userAuthResponse(token=token,userInfo=userInfoResponse.model_validate(users)))

@router.post('/login')
async def login(user_data:UserRequest,db:AsyncSession=Depends(get_db)):
    isuser = await user.authenticate_user(db,user_data.username,user_data.password)
    if not isuser : 
        raise HTTPException(status_code=401,detail='用户或密码错误')
    token=await user.create_token(db,isuser.id)
    response_data=userAuthResponse(token=token,userInfo=userInfoResponse.model_validate(isuser))
    return success_response(message='登录成功',data=response_data)

@router.get('/info')
async def get_user_info(user:User=Depends(auth.get_current_user)):
    return success_response(message='获取个人信息成功',data=userInfoResponse.model_validate(user))

@router.put("/update")
async def update_user_info(
    user_data: userUpdateRequest,
    User:User=Depends(auth.get_current_user),
    db:AsyncSession=Depends(get_db)
):
    await user.update_user(db,User.username,user_data)
    return success_response(message='修改成功',data=userInfoResponse.model_validate(User))

@router.put('password')
async def update_password(
    new_password:str,
    User:User=Depends(auth.get_current_user),
    db:AsyncSession=Depends(get_db)
):
    result= await user.update_user_password(db,new_password,User)
    if not result:
        raise HTTPException(status_code=404,detail='用户不存在')
    return success_response(message='修改成功',data=userInfoResponse.model_validate(User))


