from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.enums import Gender


class UserRequest(BaseModel):
    username: str
    password: str


class UserInfoBase(BaseModel):
    """
    用户信息基础数据模型
    """

    nickname: str | None = Field(None, max_length=50, description="昵称")
    avatar: str | None = Field(None, max_length=255, description="头像URL")
    gender: Gender | None = Field(None, description="性别")
    bio: str | None = Field(None, max_length=500, description="个人简介")


class userInfoResponse(UserInfoBase):
    id: int
    username: str
    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象取值
        populate_by_name=True,
    )


class userAuthResponse(BaseModel):
    token: str
    user_info: userInfoResponse = Field(..., alias="userInfo")

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象取值
        populate_by_name=True,
    )


class userUpdateRequest(BaseModel):
    nickname: str | None = None
    avatar: str | None = None
    gender: Gender | None = None
    bio: str | None = None


class PasswordUpdateRequest(BaseModel):
    old_password: str = Field(..., min_length=3, description="旧密码")
    new_password: str = Field(..., min_length=3, description="新密码")

    @model_validator(mode="after")
    def check_password_not_same(self):
        if self.old_password == self.new_password:
            raise ValueError("新密码不能和旧密码相同")
        return self
