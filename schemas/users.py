from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

class Gender(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"

class UserRequest(BaseModel):
    username:str
    password:str


class UserInfoBase(BaseModel):
    """
    用户信息基础数据模型
    """
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[Gender] = Field(None, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")

class userInfoResponse(UserInfoBase):
    id:int
    username:str
    model_config=ConfigDict(
        from_attributes=True,#允许从ORM对象取值
        populate_by_name=True
    )

class userAuthResponse(BaseModel):
    token:str
    user_info:userInfoResponse=Field(...,alias='userInfo')

    model_config=ConfigDict(
        from_attributes=True,#允许从ORM对象取值
        populate_by_name=True
    )

class userUpdateRequest(BaseModel):
    nickname:str|None
    avatar:str|None
    gender:Gender|None
    bio:str|None