"""新闻列表/详情的接口测试。

覆盖两个曾经真实踩过的坑：
1. 列表没有 ORDER BY，新入库的 RSS 新闻永远排不到第一页；
2. 详情没返回 sourceUrl，前端“查看全文”按钮永远不渲染。
"""

from datetime import datetime


async def test_list_orders_by_publish_time_desc(client, make_news):
    older = await make_news(title="旧闻", publish_time=datetime(2026, 1, 1, 8, 0))
    newer = await make_news(title="新闻", publish_time=datetime(2026, 2, 1, 8, 0))

    response = await client.get(
        "/api/news/list",
        params={"categoryId": newer.category_id, "page": 1, "pagesize": 10},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert [item["id"] for item in data["list"]] == [newer.id, older.id]
    assert data["totol"] == 2
    assert data["hasmore"] is False


async def test_list_pagination_has_more(client, make_news):
    for index in range(3):
        await make_news(title=f"新闻{index}", publish_time=datetime(2026, 3, index + 1))

    first = await client.get("/api/news/list", params={"categoryId": 1, "page": 1, "pagesize": 2})
    data = first.json()["data"]

    assert len(data["list"]) == 2
    assert data["totol"] == 3
    assert data["hasmore"] is True

    second = await client.get("/api/news/list", params={"categoryId": 1, "page": 2, "pagesize": 2})
    assert len(second.json()["data"]["list"]) == 1
    assert second.json()["data"]["hasmore"] is False


async def test_detail_returns_source_url(client, make_news):
    news = await make_news(source_url="https://example.com/post/1")

    response = await client.get("/api/news/detail", params={"id": news.id})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["sourceUrl"] == "https://example.com/post/1"
    assert data["content"] == "测试正文"


async def test_detail_404(client):
    response = await client.get("/api/news/detail", params={"id": 999999})
    assert response.status_code == 404


async def test_list_views_come_from_counter(client, make_news, monkeypatch):
    news = await make_news(views=100)

    async def fake_read_many(news_ids):
        return [105 for _ in news_ids]

    monkeypatch.setattr("cache.view_counter.read_many", fake_read_many)

    response = await client.get(
        "/api/news/list",
        params={"categoryId": news.category_id, "page": 1, "pagesize": 10},
    )

    item = response.json()["data"]["list"][0]
    assert item["views"] == 105
    # 列表缓存只存正文投影，正文不进列表
    assert "content" not in item


async def test_detail_views_come_from_counter(client, make_news, monkeypatch):
    news = await make_news(views=100)

    async def fake_read(news_id):
        return 105

    async def fake_bump(news_id):
        return 106

    monkeypatch.setattr("cache.view_counter.read", fake_read)
    monkeypatch.setattr("cache.view_counter.bump", fake_bump)

    response = await client.get("/api/news/detail", params={"id": news.id})

    assert response.status_code == 200, response.text
    # 详情返回的是计数器自增后的值，不是数据库的 100
    assert response.json()["data"]["views"] == 106


async def test_detail_sets_x_cache_header(client, make_news, monkeypatch):
    """同一个 id 第一次回源是 MISS，第二次走缓存是 HIT。"""
    news = await make_news()
    store = {}

    async def fake_get(news_id):
        return store.get(news_id)

    async def fake_set(news_id, data, expire=None):
        store[news_id] = data

    monkeypatch.setattr("cache.news_cache.get_cache_detail", fake_get)
    monkeypatch.setattr("cache.news_cache.set_cache_detail", fake_set)

    first = await client.get("/api/news/detail", params={"id": news.id})
    second = await client.get("/api/news/detail", params={"id": news.id})

    assert first.headers["x-cache"] == "MISS"
    assert second.headers["x-cache"] == "HIT"


async def test_detail_404_sets_x_cache_header(client):
    response = await client.get("/api/news/detail", params={"id": 999999})

    assert response.status_code == 404
    # raise 也要把 header 带出去，排障时才知道这次是回源确认的
    assert response.headers["x-cache"] == "MISS"
