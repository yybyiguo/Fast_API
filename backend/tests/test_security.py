"""安全工具单元测试（不碰数据库/接口）。"""

import pytest
from pydantic import ValidationError

from schemas.users import PasswordUpdateRequest
from utils.security import get_password_hash, verify_password


def test_password_is_hashed():
    hashed = get_password_hash("abc123")

    assert hashed != "abc123"
    assert verify_password("abc123", hashed)
    assert not verify_password("wrong", hashed)


def test_password_cannot_be_same():
    with pytest.raises(ValidationError):
        PasswordUpdateRequest(old_password="abc", new_password="abc")
