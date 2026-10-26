"""全局异常处理：生产与开发两种响应形态。"""

from config.db_config import settings
from curd import user as user_crud


async def _boom(*args, **kwargs):
    raise RuntimeError("故意炸")


async def _register_and_fail(strict_client):
    response = await strict_client.post(
        "/api/user/register",
        json={"username": "u", "password": "pass123"},
    )
    return response, response.json()


async def test_500_hides_internals_in_prod(strict_client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(user_crud, "create_token", _boom)

    response, body = await _register_and_fail(strict_client)

    assert response.status_code == 500
    assert body["message"] == "服务器内部错误"
    # 生产环境绝不把内部细节吐给调用方
    assert body["data"] is None
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
    # 但要给出 request_id，用户报错时才能对上日志
    assert body["request_id"] and body["request_id"] != "-"


async def test_500_shows_details_in_dev(strict_client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(user_crud, "create_token", _boom)

    response, body = await _register_and_fail(strict_client)

    assert response.status_code == 500
    assert body["data"]["error_type"] == "RuntimeError"
    assert "Traceback" in body["data"]["traceback"]
    assert body["request_id"] and body["request_id"] != "-"
