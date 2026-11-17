"""浏览量计数器：绝对值语义、批量读、SET NX 回填、自增标记脏集合。

conftest 的 autouse fixture 会把这些函数 patch 成空实现，
所以这里在模块导入时先保存原始函数，再在单个测试里替换 redis_client。
"""

from cache import view_counter

_orig_read = view_counter.read
_orig_read_many = view_counter.read_many
_orig_seed = view_counter.seed
_orig_seed_many = view_counter.seed_many
_orig_bump = view_counter.bump
_orig_delete_many = view_counter.delete_many


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def incr(self, key):
        self.ops.append(("incr", key))

    def sadd(self, key, member):
        self.ops.append(("sadd", key, member))

    def set(self, key, value, nx=False):
        self.ops.append(("set", key, value, nx))

    async def execute(self):
        if self.redis.fail:
            raise RuntimeError("redis down")

        results = []
        for op in self.ops:
            if op[0] == "incr":
                current = int(self.redis.values.get(op[1], 0))
                self.redis.values[op[1]] = str(current + 1)
                results.append(current + 1)
            elif op[0] == "sadd":
                self.redis.dirty.add(op[2])
                results.append(1)
            elif op[0] == "set":
                _, key, value, nx = op
                if nx and key in self.redis.values:
                    results.append(None)
                else:
                    self.redis.values[key] = str(value)
                    results.append(True)
        return results


class FakeRedis:
    def __init__(self, values=None, fail=False):
        self.values = dict(values or {})
        self.dirty = set()
        self.fail = fail
        self.pipeline_ops = []
        self.deleted = []
        self.closed = False

    def pipeline(self, transaction=False):
        pipe = FakePipeline(self)
        self.pipeline_ops.append(pipe)
        return pipe

    async def get(self, key):
        if self.fail:
            raise RuntimeError("redis down")
        return self.values.get(key)

    async def mget(self, keys):
        if self.fail:
            raise RuntimeError("redis down")
        return [self.values.get(key) for key in keys]

    async def set(self, key, value, nx=False):
        if self.fail:
            raise RuntimeError("redis down")
        if nx and key in self.values:
            return None
        self.values[key] = str(value)
        return True

    async def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self.values:
                del self.values[key]
                removed += 1
        self.deleted.extend(keys)
        return removed

    async def srem(self, key, *members):
        for member in members:
            self.dirty.discard(member)
        return len(members)

    async def aclose(self):
        self.closed = True


async def test_read_returns_total(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis({"news:views:total:7": "105"}))

    assert await _orig_read(7) == 105


async def test_read_returns_none_when_key_missing(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis())

    assert await _orig_read(7) is None


async def test_read_returns_none_on_redis_failure(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis(fail=True))

    assert await _orig_read(7) is None


async def test_read_many_keeps_order_and_missing(monkeypatch):
    fake = FakeRedis(
        {
            "news:views:total:1": "10",
            "news:views:total:3": "30",
        }
    )
    monkeypatch.setattr(view_counter, "redis_client", fake)

    assert await _orig_read_many([1, 2, 3]) == [10, None, 30]
    assert await _orig_read_many([]) == []


async def test_read_many_degrades_to_none(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis(fail=True))

    assert await _orig_read_many([1, 2]) == [None, None]


async def test_seed_uses_set_nx_and_does_not_overwrite(monkeypatch):
    fake = FakeRedis({"news:views:total:7": "105"})
    monkeypatch.setattr(view_counter, "redis_client", fake)

    await _orig_seed(7, 100)

    # 计数已经涨到 105，回填不能把它盖回 100
    assert fake.values["news:views:total:7"] == "105"


async def test_seed_many_writes_only_missing(monkeypatch):
    fake = FakeRedis({"news:views:total:1": "10"})
    monkeypatch.setattr(view_counter, "redis_client", fake)

    await _orig_seed_many([(1, 5), (2, 20)])

    assert fake.values["news:views:total:1"] == "10"
    assert fake.values["news:views:total:2"] == "20"


async def test_bump_incr_and_marks_dirty(monkeypatch):
    fake = FakeRedis({"news:views:total:7": "105"})
    monkeypatch.setattr(view_counter, "redis_client", fake)

    assert await _orig_bump(7) == 106
    assert fake.values["news:views:total:7"] == "106"
    assert 7 in fake.dirty


async def test_bump_returns_none_on_redis_failure(monkeypatch):
    monkeypatch.setattr(view_counter, "redis_client", FakeRedis(fail=True))

    # 浏览量统计失败不能影响详情页
    assert await _orig_bump(7) is None


async def test_delete_many_removes_counter_and_dirty(monkeypatch):
    fake = FakeRedis({"news:views:total:7": "105"})
    fake.dirty.add(7)
    monkeypatch.setattr(view_counter, "redis_client", fake)

    assert await _orig_delete_many([7], client=fake) == 1
    assert "news:views:total:7" not in fake.values
    assert 7 not in fake.dirty
    # 外部传进来的 client 不归函数管，不能关
    assert fake.closed is False
