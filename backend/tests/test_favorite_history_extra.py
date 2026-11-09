"""收藏/历史的清空、分页和边界分支。"""

from curd import favorite as favorite_crud


async def test_clear_favorites(client, auth, make_news):
    for index in range(3):
        news = await make_news(title=f"收藏{index}")
        await client.post(
            "/api/favorite/shift",
            params={"news_id": news.id},
            headers=auth["headers"],
        )

    cleared = await client.delete("/api/favorite/clear", headers=auth["headers"])
    assert cleared.status_code == 200, cleared.text

    listing = await client.get("/api/favorite/list", headers=auth["headers"])
    assert listing.json()["data"]["total"] == 0


async def test_favorite_list_pagination(client, auth, make_news):
    for index in range(3):
        news = await make_news(title=f"收藏{index}")
        await client.post(
            "/api/favorite/shift",
            params={"news_id": news.id},
            headers=auth["headers"],
        )

    first = await client.get(
        "/api/favorite/list",
        params={"page": 1, "pagesize": 2},
        headers=auth["headers"],
    )
    first_data = first.json()["data"]
    assert len(first_data["list"]) == 2
    assert first_data["has_more"] is True

    second = await client.get(
        "/api/favorite/list",
        params={"page": 2, "pagesize": 2},
        headers=auth["headers"],
    )
    second_data = second.json()["data"]
    assert len(second_data["list"]) == 1
    assert second_data["has_more"] is False


async def test_duplicate_favorite_is_reported_as_already_saved(
    client, auth, make_news, monkeypatch
):
    news = await make_news(title="重复收藏")
    await client.post(
        "/api/favorite/shift",
        params={"news_id": news.id},
        headers=auth["headers"],
    )

    async def always_false(*args, **kwargs):
        return False

    # 模拟并发：检查时还不存在，插入时撞唯一约束
    monkeypatch.setattr(favorite_crud, "is_favorite", always_false)

    response = await client.post(
        "/api/favorite/shift",
        params={"news_id": news.id},
        headers=auth["headers"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "已收藏"


async def test_clear_history(client, auth, make_news):
    for index in range(2):
        news = await make_news(title=f"历史{index}")
        await client.post(
            "/api/history/add_history",
            params={"news_id": news.id},
            headers=auth["headers"],
        )

    cleared = await client.delete("/api/history/clear", headers=auth["headers"])
    assert cleared.status_code == 200, cleared.text

    listing = await client.get("/api/history/list", headers=auth["headers"])
    assert listing.json()["data"]["total"] == 0


async def test_delete_unknown_history_is_idempotent(client, auth):
    response = await client.delete(
        "/api/history/delete",
        params={"news_id": 999999},
        headers=auth["headers"],
    )

    assert response.status_code == 200
    assert response.json()["message"] == "没有这条记录"
