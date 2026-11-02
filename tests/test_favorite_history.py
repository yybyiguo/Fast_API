"""收藏 / 历史的接口测试。

覆盖曾经的两个真实故障：
- 收藏列表查了不存在的 Favorite.created_at，接口 500；
- 历史重复浏览撞唯一约束，以及前端路径少斜杠导致 404（这里锁死后端路由）。
"""


async def test_favorite_list_and_toggle(client, auth, make_news):
    news = await make_news(title="可收藏的新闻")

    added = await client.post(
        "/api/favorite/shift",
        params={"news_id": news.id},
        headers=auth["headers"],
    )
    assert added.status_code == 200, added.text

    listing = await client.get("/api/favorite/list", headers=auth["headers"])
    assert listing.status_code == 200, listing.text
    data = listing.json()["data"]
    assert data["total"] == 1
    item = data["list"][0]
    assert item["news_id"] == news.id
    assert item["title"] == "可收藏的新闻"
    # 回归：模型里是 create_time，接口必须仍然给出 created_at
    assert item["created_at"]

    checked = await client.get(
        "/api/favorite/check",
        params={"news_id": news.id},
        headers=auth["headers"],
    )
    assert checked.json()["data"]["is_favorite"] is True

    removed = await client.post(
        "/api/favorite/shift",
        params={"news_id": news.id},
        headers=auth["headers"],
    )
    assert removed.status_code == 200, removed.text

    listing = await client.get("/api/favorite/list", headers=auth["headers"])
    assert listing.json()["data"]["total"] == 0


async def test_favorite_requires_login(client, make_news):
    news = await make_news()

    response = await client.get(
        "/api/favorite/list",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


async def test_history_add_is_upsert(client, auth, make_news):
    news = await make_news(title="会被看两次的新闻")

    for _ in range(2):
        response = await client.post(
            "/api/history/add_history",
            params={"news_id": news.id},
            headers=auth["headers"],
        )
        assert response.status_code == 200, response.text
        assert response.json()["message"] == "添加成功"

    listing = await client.get("/api/history/list", headers=auth["headers"])
    assert listing.status_code == 200, listing.text
    data = listing.json()["data"]
    # 重复浏览只能有一条，且不能因为唯一约束报错
    assert data["total"] == 1
    assert data["list"][0]["news_id"] == news.id

    deleted = await client.delete(
        "/api/history/delete",
        params={"news_id": news.id},
        headers=auth["headers"],
    )
    assert deleted.status_code == 200, deleted.text

    listing = await client.get("/api/history/list", headers=auth["headers"])
    assert listing.json()["data"]["total"] == 0


async def test_history_add_unknown_news(client, auth):
    response = await client.post(
        "/api/history/add_history",
        params={"news_id": 999999},
        headers=auth["headers"],
    )

    assert response.status_code == 200
    assert response.json()["message"] == "添加失败"
