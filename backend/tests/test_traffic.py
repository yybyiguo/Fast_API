"""通用流量控制：按“IP + 接口分组”计数，超限返回 429。"""

from prometheus_client import REGISTRY


def _sample(bucket: str) -> float:
    return REGISTRY.get_sample_value("rate_limit_rejected_total", {"bucket": bucket}) or 0


async def test_news_rate_limited(client, monkeypatch):
    async def _deny(key: str, limit: int, window: int):
        assert key == "rl:news:127.0.0.1"
        assert (limit, window) == (120, 60)
        return (False, 30)

    monkeypatch.setattr("utils.rate_limit.reserve", _deny)

    response = await client.get(
        "/api/news/list",
        params={"page": 1, "pageSize": 5, "categoryId": 1},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"


async def test_health_is_not_limited(client, monkeypatch):
    async def _deny(*args, **kwargs):
        return (False, 30)

    monkeypatch.setattr("utils.rate_limit.reserve", _deny)

    response = await client.get("/healthz")

    assert response.status_code == 200


async def test_different_buckets_do_not_share_quota(client, monkeypatch):
    seen: list[str] = []

    async def _deny(key: str, limit: int, window: int):
        seen.append(key)
        return (False, 30)

    monkeypatch.setattr("utils.rate_limit.reserve", _deny)

    await client.get("/api/news/list", params={"page": 1, "pageSize": 5, "categoryId": 1})
    await client.get("/api/favorite/list", params={"page": 1, "pageSize": 5})

    assert seen == ["rl:news:127.0.0.1", "rl:favorite:127.0.0.1"]


async def test_rejection_increments_metric(client, monkeypatch):
    before = _sample("news")

    async def _deny(key: str, limit: int, window: int):
        return (False, 30)

    monkeypatch.setattr("utils.rate_limit.reserve", _deny)

    await client.get("/api/news/list", params={"page": 1, "pageSize": 5, "categoryId": 1})

    assert _sample("news") == before + 1


async def test_authenticated_route_uses_user_bucket(client, auth, monkeypatch):
    seen: list[str] = []

    async def _reserve(key: str, limit: int, window: int):
        seen.append(key)
        # IP 桶放行，用户桶拒绝
        return (False, 30) if ":u:" in key else (True, 0)

    monkeypatch.setattr("utils.rate_limit.reserve", _reserve)

    response = await client.get(
        "/api/favorite/list",
        params={"page": 1, "pageSize": 5},
        headers=auth["headers"],
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"
    assert "rl:favorite:u:1" in seen
