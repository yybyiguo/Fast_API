"""登录失败限流：用 Redis 做固定窗口计数。

三个设计决定：

1. 计数放 Redis，不放在进程内存里。否则多个 worker/多台机器各算各的，
   限流等于没做。
2. 用 TTL 表示窗口：第一次失败时设 15 分钟过期，之后只加数、不动过期时间，
   到点 key 自动消失，计数归零。
3. 加数和设过期必须原子。分成两条命令的话，进程在中间崩溃就会留下一个
   "永远不过期"的 key——账号被永久锁死。所以用一段 Lua 脚本一次做完。
"""

import logging

from fastapi import Request

from config.cache_config import redis_client

logger = logging.getLogger(__name__)

# 同一个来源、同一个账号：连续错 5 次，锁 15 分钟
USER_LIMIT = 5
# 同一个来源、换着账号试：20 次，锁 15 分钟
IP_LIMIT = 20
WINDOW = 15 * 60

# 注册：同一个来源每小时最多建 3 个账号
REGISTER_LIMIT = 3
REGISTER_WINDOW = 60 * 60

# KEYS[1] 是计数器，ARGV[1] 是窗口秒数；返回 {当前次数, 剩余秒数}
_HIT_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


def client_ip(request: Request) -> str:
    """取请求来源 IP。

    经过 Nginx 后 request.client.host 是代理的地址，真实来源在 X-Forwarded-For
    的第一个。注意：只有确认请求一定经过自己的可信代理时才该信任这个头，
    否则客户端可以自己伪造，绕过限流。
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def user_key(ip: str, username: str) -> str:
    # 带上 IP：别人从他的 IP 试你的账号，锁的是"他的 IP + 你的账号"，不影响你登录
    return f"login:fail:{ip}:{username.lower()}"


def ip_key(ip: str) -> str:
    return f"login:fail:ip:{ip}"


def register_key(ip: str) -> str:
    # 和登录的 key 分开：一个数“失败”，一个数“成功建号”，语义不能混
    return f"register:ip:{ip}"


async def hit(key: str, window: int = WINDOW) -> tuple[int, int]:
    """记一次失败，返回 (当前次数, 剩余秒数)。"""
    try:
        count, ttl = await redis_client.eval(_HIT_LUA, 1, key, window)
        return int(count), max(int(ttl), 0)
    except Exception:
        # 限流依赖 Redis；Redis 挂了应该"放行"而不是让所有人都登不进来。
        logger.warning("登录限流计数失败，放行本次 key=%s", key, exc_info=True)
        return 0, 0


async def state(key: str) -> tuple[int, int]:
    """只读查询，返回 (当前次数, 剩余秒数)，不增加计数。"""
    try:
        pipe = redis_client.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        value, ttl = await pipe.execute()
        return (int(value) if value else 0), max(int(ttl), 0)
    except Exception:
        logger.warning("登录限流状态读取失败，放行本次 key=%s", key, exc_info=True)
        return 0, 0


async def reset(key: str) -> None:
    """登录成功后清零。只清"这个来源 + 这个账号"，不清按 IP 的总量。"""
    try:
        await redis_client.delete(key)
    except Exception:
        logger.warning("登录限流计数清零失败 key=%s", key, exc_info=True)


def retry_after_seconds(*ttls: int) -> int:
    valid = [ttl for ttl in ttls if ttl > 0]
    return max(valid) if valid else WINDOW
