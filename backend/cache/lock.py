"""一个最小的 Redis 分布式锁。

只用来做缓存的"单飞"：同一个 key 缓存失效时，只放一个请求回源，
其余请求等它把缓存写好，避免一起打到数据库。

和 RSS 抓取锁是同一套写法：SET NX EX 占位，token 标记归属，
释放时用 Lua 比较 token，避免锁过期后误删别人的锁。
"""

import logging
import secrets

from config.cache_config import redis_client

logger = logging.getLogger(__name__)

_RELEASE_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


async def acquire(key: str, ttl: int = 5) -> str | None:
    """抢锁：抢到返回 token，没抢到返回 None。

    Redis 故障时返回一个 token（放行）：缓存本来也不可用，所有请求都会回源，
    这时候再把请求挡在锁上只会雪上加霜。失败会记日志，但不影响请求。
    """
    token = secrets.token_hex(8)
    try:
        locked = await redis_client.set(key, token, nx=True, ex=ttl)
    except Exception:
        logger.warning("抢锁失败，放行 key=%s", key, exc_info=True)
        return token
    return token if locked else None


async def release(key: str, token: str) -> None:
    """只删自己加的锁。"""
    try:
        await redis_client.eval(_RELEASE_LUA, 1, key, token)
    except Exception:
        logger.warning("释放锁失败 key=%s", key, exc_info=True)
