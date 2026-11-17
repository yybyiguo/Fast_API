"""curd/news：缓存命中/未命中、计数、详情、相关推荐、views 批量查询。"""

from curd import news as news_crud
from models.news import Category


async def test_get_categories_cache_hit(db, monkeypatch):
    cached = [{"id": 1, "name": "缓存分类"}]

    async def fake_get():
        return cached

    async def should_not_set(*args, **kwargs):
        raise AssertionError("缓存命中时不应写缓存")

    monkeypatch.setattr(news_crud, "get_cache_categories", fake_get)
    monkeypatch.setattr(news_crud, "set_cache_categories", should_not_set)

    assert await news_crud.get_categories(db) == cached


async def test_get_categories_empty_cache_is_a_hit(db, monkeypatch):
    async def fake_get():
        return []

    async def should_not_set(*args, **kwargs):
        raise AssertionError("缓存命中时不应写缓存")

    monkeypatch.setattr(news_crud, "get_cache_categories", fake_get)
    monkeypatch.setattr(news_crud, "set_cache_categories", should_not_set)

    assert await news_crud.get_categories(db) == []


async def test_get_categories_cache_miss_writes_cache(db, monkeypatch):
    captured = {}

    async def fake_get():
        return None

    async def fake_set(data):
        captured["data"] = data

    monkeypatch.setattr(news_crud, "get_cache_categories", fake_get)
    monkeypatch.setattr(news_crud, "set_cache_categories", fake_set)

    db.add(Category(name="分类A", sort_order=1))
    db.add(Category(name="分类B", sort_order=2))
    await db.commit()

    rows = await news_crud.get_categories(db)

    assert [row.name for row in rows] == ["分类A", "分类B"]
    assert [item["name"] for item in captured["data"]] == ["分类A", "分类B"]


async def test_get_news_list_cache_hit(db, monkeypatch):
    cached = [{"id": 1, "title": "缓存新闻", "views": 0}]

    async def fake_get(category_id, page, limit):
        return cached

    async def should_not_set(*args, **kwargs):
        raise AssertionError("缓存命中时不应写缓存")

    monkeypatch.setattr(news_crud, "get_cache_news_list", fake_get)
    monkeypatch.setattr(news_crud, "set_cache_news_list", should_not_set)

    assert await news_crud.get_news_list(1, db) == cached


async def test_get_news_list_cache_miss_writes_projection(db, make_news, monkeypatch):
    captured = {}

    async def fake_get(category_id, page, limit):
        return None

    async def fake_set(data, category_id, page, limit, expire=300):
        captured["data"] = data
        captured["expire"] = expire

    monkeypatch.setattr(news_crud, "get_cache_news_list", fake_get)
    monkeypatch.setattr(news_crud, "set_cache_news_list", fake_set)

    news = await make_news(title="数据库新闻")

    rows = await news_crud.get_news_list(news.category_id, db, 0, 10)

    assert [row["id"] for row in rows] == [news.id]
    assert [item["id"] for item in captured["data"]] == [news.id]
    # 列表缓存不带正文和 views：正文由详情提供，views 由计数器提供
    assert "content" not in rows[0]
    assert "views" not in rows[0]
    assert captured["expire"] == 300


async def test_empty_list_is_cached_with_short_ttl(db, monkeypatch):
    captured = {}

    async def fake_get(category_id, page, limit):
        return None

    async def fake_set(data, category_id, page, limit, expire=300):
        captured["data"] = data
        captured["expire"] = expire

    monkeypatch.setattr(news_crud, "get_cache_news_list", fake_get)
    monkeypatch.setattr(news_crud, "set_cache_news_list", fake_set)

    rows = await news_crud.get_news_list(999999, db, 0, 10)

    assert rows == []
    assert captured["data"] == []
    # 空分类只缓存 30 秒，新文章抓回来后不用等满 5 分钟
    assert captured["expire"] == 30


async def test_get_news_count_and_detail(db, make_news):
    news = await make_news(title="详情")

    assert await news_crud.get_news_count(db, news.category_id) == 1
    assert (await news_crud.get_news_detail(db, news.id)).id == news.id
    assert await news_crud.get_news_detail(db, 999999) is None


async def test_get_views_map_returns_only_existing_ids(db, make_news):
    first = await make_news(title="第一篇", views=7)
    second = await make_news(title="第二篇", views=11)

    views = await news_crud.get_views_map(db, [first.id, second.id, 999999])

    assert views == {first.id: 7, second.id: 11}
    assert await news_crud.get_views_map(db, []) == {}


async def test_get_related_news_excludes_self_and_sorts_by_views(db, make_news):
    current = await make_news(title="当前", views=1)
    low = await make_news(title="低", views=2)
    high = await make_news(title="高", views=9)

    related = await news_crud.get_related_news(db, current.id, current.category_id, limit=2)

    assert [item["id"] for item in related] == [high.id, low.id]
