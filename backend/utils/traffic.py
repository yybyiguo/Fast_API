"""通用流量控制：按“来源 IP + 接口分组”限制请求频率。

和登录/注册限流的分工：

- 登录、注册：按“业务语义”限——错几次密码、建几个号；
- 这里：按“请求次数”限——同一个来源一分钟能打多少次。

所以两者用不同的 key，互不影响。这里不关心请求成功还是失败，
每次进来都占一个名额；被挡住的请求连路由函数都不会进。
"""

import logging

from fastapi import HTTPException, Request

from utils import rate_limit
from utils.metrics import RATE_LIMIT_REJECTED
from utils.rate_limit import client_ip

logger = logging.getLogger(__name__)


def limit(bucket: str, limit: int, window: int):
    """做一个“按 IP + 分组”的限流依赖。

    用法：APIRouter(dependencies=[Depends(limit("news", 120, 60))])
    同一个 bucket 的请求共用一份额度，不同接口分组各算各的。
    """

    async def _dependency(request: Request) -> None:
        ip = client_ip(request)
        key = f"rl:{bucket}:{ip}"
        # 复用注册那套“原子占位”：并发时也不会多放行
        allowed, ttl = await rate_limit.reserve(key, limit, window)
        if not allowed:
            RATE_LIMIT_REJECTED.labels(bucket=bucket).inc()
            logger.warning(
                "接口限流 ip=%s bucket=%s limit=%s/%ss",
                ip,
                bucket,
                limit,
                window,
            )
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试",
                headers={"Retry-After": str(max(ttl, 1))},
            )

    return _dependency
