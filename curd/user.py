from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from sqlalchemy import func, select, update
from models.user import User, UserToken
from schemas.users import PasswordUpdateRequest, UserRequest, userUpdateRequest
from utils import security
from utils.security import get_password_hash, verify_password
import uuid

async def get_user_by_username(db:AsyncSession,username:str):
    stmt=select(User).where(User.username==username)
    result= await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(db:AsyncSession,user_data:UserRequest):
    hashed_password=get_password_hash(user_data.password)
    user=User(username=user_data.username,password=hashed_password)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

async def create_token(db:AsyncSession,user_id:int):
    token= str(uuid.uuid4())
    expires_at= datetime.now()+timedelta(days=7)
    stmt = select(UserToken).where(UserToken.id==user_id)
    result=await db.execute(stmt)
    user_token=result.scalar_one_or_none()
    if user_token:
        user_token.token=token
        user_token.expires_at=expires_at
    else:
        user_token=UserToken(id=user_id,token=token,expires_at=expires_at)
        db.add(user_token)
    return token

# 验证是否注册过
async def authenticate_user(db:AsyncSession,user_name:str,password:str):
    user=await get_user_by_username(db,user_name)
    if not user:
        return None
    if not security.verify_password(password,user.password):
        return None
    return user

async def get_user_by_token(db:AsyncSession,token:str):
    stmt=select(UserToken).where(UserToken.token==token)
    result= await db.execute(stmt)
    db_token=result.scalar_one_or_none()
    if not db_token or db_token.expires_at<datetime.now():
        return None
    result2=await db.execute(select(User).where(db_token.id==User.id))
    return result2.scalar_one_or_none()

async def update_user(db:AsyncSession,user_name:str,user_data:userUpdateRequest):
    query= update(User).where(User.username==user_name).values(** user_data.model_dump(exclude_unset=True))
    result =await db.execute(query)
    if result.rowcount==0:
        raise HTTPException(status_code=404,detail='用户不存在')
    updated_user=await get_user_by_username(db,user_name)
    return updated_user


async def update_user_password(
    db: AsyncSession, password: PasswordUpdateRequest, user: User
):

    ispass = verify_password(password.old_password,user.password)
    if not ispass :
        return None
    pw=get_password_hash(password.new_password)
    query= update(User).where(User.username==user.username).values(password=pw)
    result = await db.execute(query)
    await db.flush()
    if result.rowcount==0:
        raise HTTPException(status_code=404,detail='用户不存在')
    updated_user= await get_user_by_username(db,user.username)
    return updated_user
