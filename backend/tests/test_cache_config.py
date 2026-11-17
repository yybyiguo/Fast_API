"""缓存工具：读写、JSON 序列化、Redis 故障降级。"""

from prometheus_client import REGISTRY

from config import cache_config


class FakeRedis:
    def __init__(self, value=None, fail=False):
        self.value = value
        self.fail = fail
        self.setex_calls = []
        self.closed = False

    async def get(self, key):
        if self.fail:
            raise RuntimeError("redis down")
        return self.value

    async def setex(self, key, expire, value):
        if self.fail:
            raise RuntimeError("redis down")
        self.setex_calls.append((key, expire, value))


async def test_get_cache_returns_value(monkeypatch):
    monkeypatch.setattr(cache_config, "redis_client", FakeRedis(value="v"))

    assert await cache_config.get_cache("k") == "v"


async def test_get_cache_returns_none_on_error(monkeypatch):
    monkeypatch.setattr(cache_config, "redis_client", FakeRedis(fail=True))

    assert await cache_config.get_cache("k") is None


async def test_get_json_cache_parses_json(monkeypatch):
    monkeypatch.setattr(cache_config, "redis_client", FakeRedis(value='{"a": 1}'))

    assert await cache_config.get_json_cache("k") == {"a": 1}


async def test_get_json_cache_returns_none_for_empty_or_invalid(monkeypatch):
    monkeypatch.setattr(cache_config, "redis_client", FakeRedis(value=None))
    assert await cache_config.get_json_cache("k") is None

    monkeypatch.setattr(cache_config, "redis_client", FakeRedis(value="{not-json"))
    assert await cache_config.get_json_cache("k") is None


async def test_set_cache_serializes_structures(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache_config, "redis_client", fake)

    await cache_config.set_cache("k", {"name": "中文"}, expire=120)

    key, expire, value = fake.setex_calls[0]
    assert key == "k"
    assert expire == 120
    assert value == '{"name": "中文"}'
    assert "\\u4e2d" not in value  # ensure_ascii=False


async def test_set_cache_keeps_plain_string(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache_config, "redis_client", fake)

    await cache_config.set_cache("k", "plain")

    assert fake.setex_calls[0][2] == "plain"


async def test_set_cache_returns_none_on_error(monkeypatch):
    monkeypatch.setattr(cache_config, "redis_client", FakeRedis(fail=True))

    assert await cache_config.set_cache("k", {"a": 1}) is None


def _errors(op: str) -> float:
    return REGISTRY.get_sample_value("cache_errors_total", {"op": op}) or 0


async def test_cache_error_metric_counts_redis_failures(monkeypatch):
    """Redis 故障时 miss 和 error 会同时增加，但只有 error 能说明“缓存不可用”。"""
    monkeypatch.setattr(cache_config, "redis_client", FakeRedis(fail=True))

    before_get = _errors("get")
    await cache_config.get_cache("k")
    await cache_config.get_json_cache("k")
    assert _errors("get") == before_get + 2

    before_set = _errors("set")
    await cache_config.set_cache("k", {"a": 1})
    assert _errors("set") == before_set + 1
