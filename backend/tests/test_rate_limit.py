"""登录失败限流：被锁、计数、清零、取真实 IP。"""

from prometheus_client import REGISTRY
from starlette.requests import Request

from utils.rate_limit import client_ip


def _rejected(bucket: str) -> float:
    return REGISTRY.get_sample_value("rate_limit_rejected_total", {"bucket": bucket}) or 0


def _request(headers: dict[str, str] | None = None, client: tuple[str, int] | None = None):
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": client,
    }
    return Request(scope)


def test_client_ip_uses_forwarded_header():
    request = _request({"x-forwarded-for": "1.2.3.4, 10.0.0.1"}, client=("10.0.0.1", 1))
    assert client_ip(request) == "1.2.3.4"


def test_client_ip_falls_back_to_socket():
    assert client_ip(_request(client=("8.8.8.8", 1))) == "8.8.8.8"


async def test_login_locked_returns_429(client, auth, monkeypatch):
    async def _locked(key: str):
        # “来源 + 账号”已达上限，“按 IP 总量”还没到
        return (0, 0) if key.startswith("login:fail:ip:") else (5, 600)

    monkeypatch.setattr("utils.rate_limit.state", _locked)
    before = _rejected("login")

    response = await client.post(
        "/api/user/login",
        json={"username": "alice", "password": "secret123"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "600"
    assert "分钟后再试" in response.json()["message"]
    assert _rejected("login") == before + 1


async def test_wrong_password_hits_both_counters(client, auth, monkeypatch):
    calls: list[str] = []

    async def _state(key: str):
        return (0, 0)

    async def _hit(key: str, window: int = 900):
        calls.append(key)
        return (1, 900)

    monkeypatch.setattr("utils.rate_limit.state", _state)
    monkeypatch.setattr("utils.rate_limit.hit", _hit)

    response = await client.post(
        "/api/user/login",
        json={"username": "alice", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert "login:fail:127.0.0.1:alice" in calls
    assert any(key.startswith("login:fail:ip:") for key in calls)


async def test_fifth_failure_returns_429(client, auth, monkeypatch):
    async def _state(key: str):
        return (0, 0)

    async def _hit(key: str, window: int = 900):
        # 这次失败之后刚好到达 5 次
        return (5, 900) if key.endswith(":alice") else (1, 900)

    monkeypatch.setattr("utils.rate_limit.state", _state)
    monkeypatch.setattr("utils.rate_limit.hit", _hit)

    response = await client.post(
        "/api/user/login",
        json={"username": "alice", "password": "wrong-password"},
    )

    assert response.status_code == 429


async def test_success_resets_only_user_counter(client, auth, monkeypatch):
    reset_keys: list[str] = []

    async def _state(key: str):
        return (1, 600)

    async def _reset(key: str):
        reset_keys.append(key)

    monkeypatch.setattr("utils.rate_limit.state", _state)
    monkeypatch.setattr("utils.rate_limit.reset", _reset)

    response = await client.post(
        "/api/user/login",
        json={"username": "alice", "password": "secret123"},
    )

    assert response.status_code == 200
    assert reset_keys == ["login:fail:127.0.0.1:alice"]


async def test_register_locked_returns_429(client, monkeypatch):
    async def _reserve(key: str, limit: int, window: int):
        # 路由上的 auth 桶放行，注册桶拒绝，才能真正走到注册自己的 429
        if key.startswith("rl:auth:"):
            return (True, 0)
        return (False, 1800)

    monkeypatch.setattr("utils.rate_limit.reserve", _reserve)
    before = _rejected("register")

    response = await client.post(
        "/api/user/register",
        json={"username": "bob", "password": "secret123"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "1800"
    assert _rejected("register") == before + 1


async def test_register_reserves_slot_before_creating(client, monkeypatch):
    reserved: list[tuple[str, int, int]] = []

    async def _reserve(key: str, limit: int, window: int):
        reserved.append((key, limit, window))
        return (True, 3600)

    monkeypatch.setattr("utils.rate_limit.reserve", _reserve)

    created = await client.post(
        "/api/user/register",
        json={"username": "bob", "password": "secret123"},
    )

    assert created.status_code == 200
    # traffic limit 先于业务限流执行：auth 桶先占位，注册名额后占位
    assert reserved == [
        ("rl:auth:127.0.0.1", 10, 60),
        ("register:ip:127.0.0.1", 3, 3600),
    ]


async def test_register_releases_slot_when_creation_fails(client, monkeypatch):
    released: list[str] = []

    async def _reserve(key: str, limit: int, window: int):
        return (True, 3600)

    async def _release(key: str):
        released.append(key)

    monkeypatch.setattr("utils.rate_limit.reserve", _reserve)
    monkeypatch.setattr("utils.rate_limit.release", _release)

    created = await client.post(
        "/api/user/register",
        json={"username": "bob", "password": "secret123"},
    )
    assert created.status_code == 200
    # 成功不归还
    assert released == []

    # 重复用户名：占位的名额要还回去
    duplicate = await client.post(
        "/api/user/register",
        json={"username": "bob", "password": "secret123"},
    )
    assert duplicate.status_code == 400
    assert released == ["register:ip:127.0.0.1"]
