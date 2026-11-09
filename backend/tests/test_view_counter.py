"""浏览量计数器：Redis 正常与故障时的行为。

conftest 的 autouse fixture 会把 view_counter 的两个函数 patch 成空实现，
所以这里在模块导入时先保存原始函数，再在单个测试里替换 redis_client。
"""

from cache import view_counter

_original_increase = view_counter.increase
_original_pending = view_counter.pending


class FakePipeline:
    def __init__(self, calls, fail):
        self.calls = calls
        self.fail = fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def incr(self, key):
        self.calls.append(("incr", key))

    def sadd(self, key, member):
        self.calls.append(("sadd", key, member))

    async def execute(self):
        if self.fail:
            raise RuntimeError("redis down")


class FakeRedis:
    def __init__(self, value=None, fail=False):
        self.value = value
        self.fail = fail
        self.calls = []

    def pipeline(self, transaction=False):
        return FakePipeline(self.calls, self.fail)

    async def get(self, key):
        if self.fail:
            raise RuntimeError("redis down")
        return self.value


async def test_increase_incr_and_marks_dirty(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(view_counter, "redis_client", fake)

    await _original_increase(7)

    assert ("incr", "news:views:7") in fake.calls
    assert ("sadd", "news:views:dirty", 7) in fake.calls


async def test_increase_never_raises_on_redis_failure(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis(fail=True))

    # 浏览量统计失败不能影响详情页
    await _original_increase(7)


async def test_pending_reads_counter(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis(value="5"))

    assert await _original_pending(7) == 5


async def test_pending_defaults_to_zero(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis(value=None))

    assert await _original_pending(7) == 0


async def test_pending_returns_zero_on_redis_failure(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis(fail=True))

    assert await _original_pending(7) == 0
