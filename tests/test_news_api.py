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
