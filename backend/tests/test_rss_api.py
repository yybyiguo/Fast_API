"""RSS 管理接口：鉴权、RSSHub 路径拼接、SSRF 拦截、重复源。"""

from config.db_config import settings


def _as_admin(monkeypatch, username: str = "alice") -> None:
    monkeypatch.setattr(settings, "rss_admin_users", username)


async def test_list_requires_login(client):
    response = await client.get("/api/rss/feeds")

    assert response.status_code == 401


async def test_list_forbidden_for_non_admin(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "rss_admin_users", "someone-else")

    response = await client.get("/api/rss/feeds", headers=auth["headers"])

    assert response.status_code == 403


async def test_create_joins_rsshub_path_and_lists(client, auth, monkeypatch, category):
    _as_admin(monkeypatch)

    created = await client.post(
        "/api/rss/feeds",
        json={
            "name": "B站热榜",
            "url": "/bilibili/hot-search",
            "categoryId": category.id,
        },
        headers=auth["headers"],
    )

    assert created.status_code == 200, created.text
    data = created.json()["data"]
    assert data["url"] == "http://127.0.0.1:1200/bilibili/hot-search"
    assert data["categoryId"] == category.id

    listing = await client.get("/api/rss/feeds", headers=auth["headers"])
    assert listing.status_code == 200
    assert [item["name"] for item in listing.json()["data"]] == ["B站热榜"]

    deleted = await client.delete(f"/api/rss/feeds/{data['id']}", headers=auth["headers"])
    assert deleted.status_code == 200


async def test_create_rejects_non_http_scheme(client, auth, monkeypatch, category):
    _as_admin(monkeypatch)

    response = await client.post(
        "/api/rss/feeds",
        json={"name": "bad", "url": "ftp://example.com/feed", "categoryId": category.id},
        headers=auth["headers"],
    )

    assert response.status_code == 422
    assert "http" in response.json()["message"]


async def test_create_rejects_private_host_when_not_allowed(client, auth, monkeypatch, category):
    _as_admin(monkeypatch)
    monkeypatch.setattr(settings, "rss_private_hosts", "")

    response = await client.post(
        "/api/rss/feeds",
        json={
            "name": "local",
            "url": "http://127.0.0.1:1200/bilibili/hot-search",
            "categoryId": category.id,
        },
        headers=auth["headers"],
    )

    assert response.status_code == 422
    assert "内网" in response.json()["message"]


async def test_duplicate_feed_url_returns_409(client, auth, monkeypatch, category):
    _as_admin(monkeypatch)
    payload = {"name": "dup", "url": "https://1.1.1.1/feed", "categoryId": category.id}

    first = await client.post("/api/rss/feeds", json=payload, headers=auth["headers"])
    assert first.status_code == 200, first.text

    second = await client.post("/api/rss/feeds", json=payload, headers=auth["headers"])
    assert second.status_code == 409


async def test_delete_unknown_feed_returns_404(client, auth, monkeypatch):
    _as_admin(monkeypatch)

    response = await client.delete("/api/rss/feeds/999999", headers=auth["headers"])

    assert response.status_code == 404
