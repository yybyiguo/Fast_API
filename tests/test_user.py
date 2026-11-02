"""用户接口测试。"""

from sqlalchemy import text

from curd import user as user_crud


async def test_register_success(client, db):
    # ── Arrange：准备请求数据 ──
    payload = {"username": "alice", "password": "secret123"}

    # ── Act：发请求 ──
    response = await client.post("/api/user/register", json=payload)

    # ── Assert：三层断言 ──
    # 1) HTTP 层
    assert response.status_code == 200, response.text

    # 2) 响应体层
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "注册成功"
    data = body["data"]
    assert data["token"]
    assert data["userInfo"]["username"] == "alice"
    # 密码不能出现在响应里
    assert "password" not in data["userInfo"]

    # 3) 数据库层：接口说成功了，库里真的有一行吗？
    row = (
        (
            await db.execute(
                text("SELECT id, username, password FROM `user` WHERE username = :name"),
                {"name": "alice"},
            )
        )
        .mappings()
        .one()
    )
    assert row["id"] == data["userInfo"]["id"]
    assert row["password"] != "secret123"  # 存的是哈希，不是明文

    # 返回的 token 也必须真的落库，而不是只在内存里拼出来的
    token_row = (
        (await db.execute(text("SELECT token FROM user_token WHERE id = :id"), {"id": row["id"]}))
        .mappings()
        .one()
    )
    assert token_row["token"] == data["token"]


async def test_register_duplicate_username(client, db):
    payload = {"username": "bob", "password": "secret123"}

    first = await client.post("/api/user/register", json=payload)
    assert first.status_code == 200

    second = await client.post("/api/user/register", json=payload)
    body = second.json()

    assert second.status_code == 400, body
    assert body["code"] == 400
    assert body["message"] == "该用户已经存在"
    assert body["data"] is None

    # 被拒绝的那次不能留下第二行
    count = (
        await db.execute(
            text("SELECT COUNT(*) FROM `user` WHERE username = :name"),
            {"name": "bob"},
        )
    ).scalar_one()
    assert count == 1


async def test_register_rolls_back_when_token_fails(strict_client, monkeypatch, db):
    async def boom(db, user_id):
        raise RuntimeError("模拟创建 token 失败")

    # 只在这一个测试内把 create_token 换掉，测试结束自动还原
    monkeypatch.setattr(user_crud, "create_token", boom)

    response = await strict_client.post(
        "/api/user/register",
        json={"username": "carol", "password": "secret123"},
    )

    assert response.status_code == 500
    assert response.json()["code"] == 500

    users = (await db.execute(text("SELECT COUNT(*) FROM `user`"))).scalar_one()
    tokens = (await db.execute(text("SELECT COUNT(*) FROM user_token"))).scalar_one()

    assert users == 0, "用户不该被留下来"
    assert tokens == 0


async def test_get_info_with_token(client, auth):
    response = await client.get("/api/user/info", headers=auth["headers"])
    body = response.json()

    assert response.status_code == 200, body
    assert body["code"] == 200
    assert body["data"]["username"] == "alice"


async def test_get_info_without_token(client):
    response = await client.get("/api/user/info")
    body = response.json()

    assert response.status_code == 401
    assert body["code"] == 401
    assert body["message"] == "未提供有效的认证凭证"
    assert body["data"] is None


async def test_update_nickname_only(client, auth, db):
    response = await client.put(
        "/api/user/update",
        json={"nickname": "新昵称"},  # 只改昵称，其他都不传
        headers=auth["headers"],
    )
    body = response.json()
    assert response.status_code == 200, body
    assert body["data"]["nickname"] == "新昵称"

    row = (
        (
            await db.execute(
                text("SELECT nickname FROM `user` WHERE username = :name"),
                {"name": "alice"},
            )
        )
        .mappings()
        .one()
    )
    assert row["nickname"] == "新昵称"


async def test_update_can_clear_bio(client, auth, db):
    # 1) 先写一个简介进去
    first = await client.put("/api/user/update", json={"bio": "我是简介"}, headers=auth["headers"])
    assert first.status_code == 200, first.json()
    assert first.json()["data"]["bio"] == "我是简介"

    # 2) 再把它清空
    second = await client.put("/api/user/update", json={"bio": None}, headers=auth["headers"])
    body = second.json()

    assert second.status_code == 200, body
    assert body["data"]["bio"] is None

    row = (
        (
            await db.execute(
                text("SELECT bio FROM `user` WHERE username = :name"),
                {"name": "alice"},
            )
        )
        .mappings()
        .one()
    )
    assert row["bio"] is None
