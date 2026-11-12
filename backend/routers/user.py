import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_config import get_db
from curd import user
from models.user import User
from schemas.users import (
    PasswordUpdateRequest,
    UserRequest,
    userAuthResponse,
    userInfoResponse,
    userUpdateRequest,
)
from utils import auth, rate_limit
from utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


def _too_many(retry_after: int) -> HTTPException:
    """统一的 429 响应：告诉客户端等多久再试。"""
    minutes = max(retry_after // 60, 1)
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"尝试次数过多，请 {minutes} 分钟后再试",
        headers={"Retry-After": str(retry_after)},
    )


@router.post("/register")
async def register(
    userData: UserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = rate_limit.client_ip(request)
    key = rate_limit.register_key(ip)

    # 先看这个来源今天是不是造得太多了
    count, ttl = await rate_limit.state(key)
    if count >= rate_limit.REGISTER_LIMIT:
        logger.warning("注册被限流 ip=%s count=%s", ip, count)
        raise _too_many(rate_limit.retry_after_seconds(ttl))

    existing_user = await user.get_user_by_username(db, userData.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该用户已经存在")
    users = await user.create_user(db, userData)
    token = await user.create_token(db, users.id)
    await db.commit()

    # 只有真的建出账号才计数：重复用户名、参数不合法不该消耗额度，
    # 否则别人可以故意发失败请求，把同一个出口 IP 下所有人的注册额度烧光。
    await rate_limit.hit(key, rate_limit.REGISTER_WINDOW)

    return success_response(
        message="注册成功",
        data=userAuthResponse(token=token, userInfo=userInfoResponse.model_validate(users)),
    )


@router.post("/login")
async def login(
    user_data: UserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = rate_limit.client_ip(request)
    ukey = rate_limit.user_key(ip, user_data.username)
    ikey = rate_limit.ip_key(ip)

    # 先看有没有被锁，再校验密码：锁住时直接 429，不让 bcrypt 白白消耗 CPU
    ucount, uttl = await rate_limit.state(ukey)
    icount, ittl = await rate_limit.state(ikey)
    if ucount >= rate_limit.USER_LIMIT or icount >= rate_limit.IP_LIMIT:
        retry = rate_limit.retry_after_seconds(uttl, ittl)
        logger.warning(
            "登录被限流 ip=%s username=%s ucount=%s icount=%s",
            ip,
            user_data.username,
            ucount,
            icount,
        )
        raise _too_many(retry)

    isuser = await user.authenticate_user(db, user_data.username, user_data.password)
    if not isuser:
        ucount, uttl = await rate_limit.hit(ukey)
        icount, ittl = await rate_limit.hit(ikey)
        logger.warning(
            "登录失败 ip=%s username=%s ucount=%s icount=%s",
            ip,
            user_data.username,
            ucount,
            icount,
        )
        # 刚好达到阈值时直接返回 429：告诉客户端再试也没用，别继续撞
        if ucount >= rate_limit.USER_LIMIT or icount >= rate_limit.IP_LIMIT:
            raise _too_many(rate_limit.retry_after_seconds(uttl, ittl))
        raise HTTPException(status_code=401, detail="用户或密码错误")

    # 登录成功：清掉“这个来源 + 这个账号”的失败计数；按 IP 的总量保留，它记的是整体坏行为
    await rate_limit.reset(ukey)
    token = await user.create_token(db, isuser.id)
    response_data = userAuthResponse(token=token, userInfo=userInfoResponse.model_validate(isuser))
    await db.commit()
    return success_response(message="登录成功", data=response_data)


@router.get("/info")
async def get_user_info(user: User = Depends(auth.get_current_user)):
    return success_response(message="获取个人信息成功", data=userInfoResponse.model_validate(user))


@router.put("/update")
async def update_user_info(
    user_data: userUpdateRequest,
    User: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_user = await user.update_user(db, User.username, user_data)
    await db.commit()
    return success_response(message="修改成功", data=userInfoResponse.model_validate(new_user))


@router.put("/password")
async def update_password(
    password: PasswordUpdateRequest,
    User: User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await user.update_user_password(db, password, User)
    if not result:
        raise HTTPException(status_code=400, detail="原密码错误")
    new_token = await user.create_token(db, User.id)
    await db.commit()
    return success_response(
        message="修改成功",
        data=userAuthResponse(token=new_token, user_info=userInfoResponse.model_validate(result)),
    )
