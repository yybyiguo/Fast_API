from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from config.db_config import get_db
from curd import user

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='未提供有效的认证凭证',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    token = credentials.credentials
    isuser = await user.get_user_by_token(db, token)
    if not isuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='无效令牌或者已经过期',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return isuser



