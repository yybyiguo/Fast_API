from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from sqlalchemy import func, select, update
from models.user import User, UserToken
from schemas.users import UserRequest
from utils.security import get_password_hash
import uuid

async def get_user_by_username(db:AsyncSession,username:str):
    stmt=select(User).where(User.username==username)
    result= await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(db:AsyncSession,user_data:UserRequest):
    hashed_password=get_password_hash(user_data.password)
    user=User(username=user_data.username,password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def create_token(db:AsyncSession,user_id:int):
    token= str(uuid.uuid4())
    expires_at= datetime.now()+timedelta(days=7)
    stmt = select(UserToken).where(UserToken.id==user_id)
    result=await db.execute(stmt)
    user_token=result.scalar_one_or_none()
    if user_token:
        user_token.token=token,
        user_token.expires_at=expires_at
    else:
        user_token=UserToken(id=user_id,token=token,expires_at=expires_at)
        db.add(user_token)
    await db.commit()
    return token
