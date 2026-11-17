"""详情缓存与 views 合并：正文和计数彻底分开的行为测试。"""

import asyncio
from datetime import datetime
from types import SimpleNamespace

from prometheus_client import REGISTRY

from cache import news_cache, view_counter
from services import news_detail, news_views

# conftest 的 autouse fixture 会把 detail_ttl 换成常量，这里先留住原始函数
_original_detail_ttl = news_cache.detail_ttl


def _row(**overrides):
    data = {
        "id": 7,
        "title": "标题",
        "author": "作者",
        "image": None,
        "publish_time": datetime(2026, 1, 1, 8, 0),
        "category_id": 3,
        "content": "正文",
        "source_url": "https://example.com/7",
        "views": 9,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


async def test_attach_views_uses_counter_without_touching_db(monkeypatch):
    items = [{"id": 1}, {"id": 2}]

    async def fake_read_many(ids):
        return [105, 0]

    async def should_not_query(*args, **kwargs):
        raise AssertionError("计数器命中时不应查库")

    monkeypatch.setattr(view_counter, "read_many", fake_read_many)
    monkeypatch.setattr(news_views.news_crud, "get_views_map", should_not_query)

    await news_views.attach_views(db=None, items=items)

    assert [item["views"] for item in items] == [105, 0]


async def test_attach_views_backfills_missing_from_db(monkeypatch):
    items = [{"id": 1}, {"id": 2}]
    seeded = []

    async def fake_read_many(ids):
        return [105, None]

    async def fake_views_map(db, ids):
        assert ids == [2]
        return {2: 9}

    async def fake_seed_many(pairs):
        seeded.extend(pairs)

    monkeypatch.setattr(view_counter, "read_many", fake_read_many)
    monkeypatch.setattr(view_counter, "seed_many", fake_seed_many)
    monkeypatch.setattr(news_views.news_crud, "get_views_map", fake_views_map)

    await news_views.attach_views(db=None, items=items)

    assert [item["views"] for item in items] == [105, 9]
    # 回填用的是数据库当前值，不是缓存里的旧值
    assert seeded == [(2, 9)]


async def test_increment_seeds_then_bumps(monkeypatch):
    seeded = []

    async def fake_read(news_id):
        return None

    async def fake_seed(news_id, value):
        seeded.append((news_id, value))

    async def fake_bump(news_id):
        return 10

    async def fake_views_map(db, ids):
        return {7: 9}

    monkeypatch.setattr(view_counter, "read", fake_read)
    monkeypatch.setattr(view_counter, "seed", fake_seed)
    monkeypatch.setattr(view_counter, "bump", fake_bump)
    monkeypatch.setattr(news_views.news_crud, "get_views_map", fake_views_map)

    assert await news_views.increment(db=None, news_id=7) == 10
    assert seeded == [(7, 9)]


async def test_increment_falls_back_to_db_when_redis_fails(monkeypatch):
    async def fake_read(news_id):
        return None

    async def fake_seed(news_id, value):
        return None

    async def fake_bump(news_id):
        return None

    async def fake_views_map(db, ids):
        return {7: 9}

    monkeypatch.setattr(view_counter, "read", fake_read)
    monkeypatch.setattr(view_counter, "seed", fake_seed)
    monkeypatch.setattr(view_counter, "bump", fake_bump)
    monkeypatch.setattr(news_views.news_crud, "get_views_map", fake_views_map)

    assert await news_views.increment(db=None, news_id=7) == 9


async def test_detail_cache_hit_skips_database(monkeypatch):
    payload = {"id": 7, "title": "缓存标题", "categoryId": 3}

    async def fake_get(news_id):
        return payload

    async def should_not_query(*args, **kwargs):
        raise AssertionError("缓存命中时不应查库")

    monkeypatch.setattr(news_detail.news_cache, "get_cache_detail", fake_get)
    monkeypatch.setattr(news_detail.news_crud, "get_news_detail", should_not_query)

    assert await news_detail.load(db=None, news_id=7) == (payload, None, "HIT")


async def test_detail_negative_cache_returns_none(monkeypatch):
    async def fake_get(news_id):
        return news_cache.NULL_MARK

    async def should_not_query(*args, **kwargs):
        raise AssertionError("负缓存命中时不应查库")

    monkeypatch.setattr(news_detail.news_cache, "get_cache_detail", fake_get)
    monkeypatch.setattr(news_detail.news_crud, "get_news_detail", should_not_query)

    assert await news_detail.load(db=None, news_id=7) == (None, None, "NEGATIVE")


async def test_detail_miss_queries_and_caches_without_views(monkeypatch):
    captured = {}

    async def fake_get(news_id):
        return None

    async def fake_row(db, news_id):
        return _row()

    async def fake_set(news_id, data, expire=None):
        captured["payload"] = data

    async def fake_lock(*args, **kwargs):
        return "token"

    async def fake_release(*args, **kwargs):
        return None

    monkeypatch.setattr(news_detail.news_cache, "get_cache_detail", fake_get)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail", fake_set)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail_null", fake_set)
    monkeypatch.setattr(news_detail.news_crud, "get_news_detail", fake_row)
    monkeypatch.setattr(news_detail.lock, "acquire", fake_lock)
    monkeypatch.setattr(news_detail.lock, "release", fake_release)

    payload, known_views, status = await news_detail.load(db=None, news_id=7)

    assert payload["title"] == "标题"
    assert "views" not in payload
    assert known_views == 9
    assert status == "MISS"
    assert "views" not in captured["payload"]
    # 命中缓存/写缓存都不带 views，views 由计数器单独提供
    assert payload["categoryId"] == 3


def _fake_lock(state):
    """进程内的假锁：同一时刻只放一个赢家。"""

    async def fake_acquire(key, ttl=5):
        if state["locked"]:
            return None
        state["locked"] = True
        return "token"

    async def fake_release(key, token):
        state["locked"] = False

    return fake_acquire, fake_release


def _fake_cache(store):
    async def fake_get(news_id):
        return store.get(news_id)

    async def fake_set(news_id, data, expire=None):
        store[news_id] = data

    async def fake_set_null(news_id, expire=60):
        store[news_id] = news_cache.NULL_MARK

    return fake_get, fake_set, fake_set_null


async def test_cold_start_stampede_queries_database_once(monkeypatch):
    """50 个并发同时未命中：锁 + 退避只应该让数据库被查一次。"""
    store: dict[int, object] = {}
    state = {"locked": False, "calls": 0}
    fake_get, fake_set, fake_set_null = _fake_cache(store)
    fake_acquire, fake_release = _fake_lock(state)

    async def slow_row(db, news_id):
        state["calls"] += 1
        await asyncio.sleep(0.3)
        return _row()

    monkeypatch.setattr(news_detail.lock, "acquire", fake_acquire)
    monkeypatch.setattr(news_detail.lock, "release", fake_release)
    monkeypatch.setattr(news_detail.news_cache, "get_cache_detail", fake_get)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail", fake_set)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail_null", fake_set_null)
    monkeypatch.setattr(news_detail.news_crud, "get_news_detail", slow_row)

    results = await asyncio.gather(*(news_detail.load(None, 7) for _ in range(50)))

    assert state["calls"] == 1
    assert all(payload["id"] == 7 for payload, _, _ in results)


async def test_slow_database_still_queries_once(monkeypatch):
    """数据库 0.8s：旧实现 0.5s 等待窗口会让等待者集体回源，退避后不应该。"""
    store: dict[int, object] = {}
    state = {"locked": False, "calls": 0}
    fake_get, fake_set, fake_set_null = _fake_cache(store)
    fake_acquire, fake_release = _fake_lock(state)

    async def slow_row(db, news_id):
        state["calls"] += 1
        await asyncio.sleep(0.8)
        return _row()

    monkeypatch.setattr(news_detail.lock, "acquire", fake_acquire)
    monkeypatch.setattr(news_detail.lock, "release", fake_release)
    monkeypatch.setattr(news_detail.news_cache, "get_cache_detail", fake_get)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail", fake_set)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail_null", fake_set_null)
    monkeypatch.setattr(news_detail.news_crud, "get_news_detail", slow_row)

    results = await asyncio.gather(*(news_detail.load(None, 7) for _ in range(20)))

    assert state["calls"] == 1
    assert all(payload["title"] == "标题" for payload, _, _ in results)


async def test_wait_budget_exhausted_falls_back_to_database(monkeypatch):
    """退避窗口用完还等不到：宁可重复回源，也不能把请求拖成 500。"""
    store: dict[int, object] = {}
    state = {"locked": False, "calls": 0}
    fake_get, fake_set, fake_set_null = _fake_cache(store)
    fake_acquire, fake_release = _fake_lock(state)

    async def very_slow_row(db, news_id):
        state["calls"] += 1
        await asyncio.sleep(0.5)
        return _row()

    monkeypatch.setattr(news_detail, "_WAIT_DELAYS", ())
    monkeypatch.setattr(news_detail.lock, "acquire", fake_acquire)
    monkeypatch.setattr(news_detail.lock, "release", fake_release)
    monkeypatch.setattr(news_detail.news_cache, "get_cache_detail", fake_get)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail", fake_set)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail_null", fake_set_null)
    monkeypatch.setattr(news_detail.news_crud, "get_news_detail", very_slow_row)

    results = await asyncio.gather(*(news_detail.load(None, 7) for _ in range(20)))

    # 一个赢家 + 19 个等不到缓存的等待者，都回源了
    assert state["calls"] == 20
    assert all(payload["id"] == 7 for payload, _, _ in results)


async def test_negative_result_is_cached_and_reused(monkeypatch):
    """查库为空要写哨兵；第二次请求直接命中负缓存，不再回源。"""
    store: dict[int, object] = {}
    state = {"locked": False, "calls": 0}
    fake_get, fake_set, fake_set_null = _fake_cache(store)
    fake_acquire, fake_release = _fake_lock(state)

    async def none_row(db, news_id):
        state["calls"] += 1
        return None

    monkeypatch.setattr(news_detail.lock, "acquire", fake_acquire)
    monkeypatch.setattr(news_detail.lock, "release", fake_release)
    monkeypatch.setattr(news_detail.news_cache, "get_cache_detail", fake_get)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail", fake_set)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail_null", fake_set_null)
    monkeypatch.setattr(news_detail.news_crud, "get_news_detail", none_row)

    assert await news_detail.load(None, 999) == (None, None, "MISS")
    assert store[999] == news_cache.NULL_MARK

    assert await news_detail.load(None, 999) == (None, None, "NEGATIVE")
    assert state["calls"] == 1


def test_detail_ttl_is_jittered():
    """TTL 必须落在 [900, 1020] 且不是常量，否则雪崩时所有 key 同时过期。"""
    values = {_original_detail_ttl() for _ in range(300)}

    assert all(900 <= value <= 1020 for value in values)
    assert len(values) > 10


def _cache_sample(kind: str, result: str) -> float:
    return REGISTRY.get_sample_value("cache_requests_total", {"kind": kind, "result": result}) or 0


async def test_detail_cache_metric_counts_hit_and_miss(monkeypatch):
    """命中率要能算：一次回源记 miss，一次命中记 hit，且一次请求只记一次。"""
    store: dict[int, object] = {}
    fake_get, fake_set, fake_set_null = _fake_cache(store)
    fake_acquire, fake_release = _fake_lock({"locked": False})

    async def row(db, news_id):
        return _row()

    monkeypatch.setattr(news_detail.lock, "acquire", fake_acquire)
    monkeypatch.setattr(news_detail.lock, "release", fake_release)
    monkeypatch.setattr(news_detail.news_cache, "get_cache_detail", fake_get)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail", fake_set)
    monkeypatch.setattr(news_detail.news_cache, "set_cache_detail_null", fake_set_null)
    monkeypatch.setattr(news_detail.news_crud, "get_news_detail", row)

    before_miss = _cache_sample("detail", "miss")
    before_hit = _cache_sample("detail", "hit")

    await news_detail.load(None, 7)  # 第一次回源
    await news_detail.load(None, 7)  # 第二次命中

    assert _cache_sample("detail", "miss") == before_miss + 1
    assert _cache_sample("detail", "hit") == before_hit + 1
