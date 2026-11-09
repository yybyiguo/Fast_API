"""缓存层：列表缓存 key 规则与按分类失效。不连真实 Redis。"""

from cache import news_cache


class FakeRedis:
    def __init__(self, keys=(), fail=False):
        self.keys = list(keys)
        self.fail = fail
        self.deleted = []
        self.closed = False

    async def scan_iter(self, match=None, count=None):
        if self.fail:
            raise RuntimeError("redis down")
        for key in self.keys:
            yield key

    async def delete(self, *keys):
        self.deleted.extend(keys)
        return len(keys)

    async def aclose(self):
        self.closed = True


async def test_invalidate_deletes_matching_keys():
    fake = FakeRedis(["news:list:1:1:10", "news:list:1:2:10"])

    removed = await news_cache.invalidate_news_list(1, client=fake)

    assert removed == 2
    assert fake.deleted == ["news:list:1:1:10", "news:list:1:2:10"]
    # 传进来的 client 不归函数管，不能关
    assert fake.closed is False


async def test_invalidate_without_keys_returns_zero():
    fake = FakeRedis([])

    assert await news_cache.invalidate_news_list(3, client=fake) == 0
    assert fake.deleted == []


async def test_invalidate_swallows_redis_error():
    fake = FakeRedis(fail=True)

    assert await news_cache.invalidate_news_list(1, client=fake) == 0


async def test_cache_key_shape(monkeypatch):
    captured = {}

    async def fake_get(key):
        captured["get"] = key
        return [{"id": 1}]

    async def fake_set(key, value, expire):
        captured["set"] = (key, value, expire)

    monkeypatch.setattr(news_cache, "get_json_cache", fake_get)
    monkeypatch.setattr(news_cache, "set_cache", fake_set)

    assert await news_cache.get_cache_news_list(1, 2, 10) == [{"id": 1}]
    assert captured["get"] == "news:list:1:2:10"

    await news_cache.set_cache_news_list([{"id": 1}], 1, 2, 10)
    assert captured["set"][0] == "news:list:1:2:10"
    assert captured["set"][2] == 300

    await news_cache.set_cache_categories([{"id": 1}])
    assert captured["set"][0] == "news:categories"
    assert captured["set"][2] == 1200
