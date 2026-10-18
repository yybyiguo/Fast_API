from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from config.db_config import get_db
from curd import user

bearer_scheme = HTTPBearer(auto_error=False)

# 根据token查询用户
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    print("===鉴权日志===")
    if not credentials:
        print("没有拿到credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='未提供有效的认证凭证',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    token = credentials.credentials
    print("提取到token:", repr(token))
    isuser = await user.get_user_by_token(db, token)
    print("查询得到用户对象:", isuser)
    if not isuser:
        print("查询用户失败，返回None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='无效令牌或者已经过期',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return isuser



