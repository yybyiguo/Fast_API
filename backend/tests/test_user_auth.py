"""登录、改密码、token 过期这三条安全相关链路。"""

from datetime import datetime, timedelta

from sqlalchemy import update

from models.user import UserToken


async def test_login_success(client, auth):
    response = await client.post(
        "/api/user/login",
        json={"username": "alice", "password": "secret123"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["token"]
    assert data["userInfo"]["username"] == "alice"


async def test_login_wrong_password(client, auth):
    response = await client.post(
        "/api/user/login",
        json={"username": "alice", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "用户或密码错误"


async def test_change_password_invalidates_old_token(client, auth):
    changed = await client.put(
        "/api/user/password",
        json={"old_password": "secret123", "new_password": "newpass456"},
        headers=auth["headers"],
    )

    assert changed.status_code == 200, changed.text
    new_token = changed.json()["data"]["token"]
    assert new_token and new_token != auth["token"]

    # 旧 token 已被 create_token 覆盖，不能再访问；新 token 可用
    old_token_info = await client.get("/api/user/info", headers=auth["headers"])
    assert old_token_info.status_code == 401

    new_token_info = await client.get(
        "/api/user/info",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert new_token_info.status_code == 200

    # 旧密码登录失败，新密码成功
    old_login = await client.post(
        "/api/user/login",
        json={"username": "alice", "password": "secret123"},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/user/login",
        json={"username": "alice", "password": "newpass456"},
    )
    assert new_login.status_code == 200


async def test_change_password_requires_old_password(client, auth):
    response = await client.put(
        "/api/user/password",
        json={"old_password": "not-my-password", "new_password": "newpass456"},
        headers=auth["headers"],
    )

    assert response.status_code == 400
    assert response.json()["message"] == "原密码错误"


async def test_expired_token_is_rejected(client, auth, db):
    await db.execute(
        update(UserToken)
        .where(UserToken.token == auth["token"])
        .values(expires_at=datetime.now() - timedelta(seconds=1))
    )
    await db.commit()

    response = await client.get("/api/user/info", headers=auth["headers"])

    assert response.status_code == 401
    assert response.json()["message"] == "无效令牌或者已经过期"
