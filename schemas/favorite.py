from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FavoriteCheckResponse(BaseModel):
    is_favorite: bool


class FavoriteItem(BaseModel):
    id: int
    news_id: int
    created_at: datetime
    title: str
    description: str | None = None
    image: str | None = None
    author: str | None = None
    category_id: int = Field(alias="categoryId")
    views: int
    publish_time: datetime | None = Field(None, alias="publishedTime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FavoriteListResponse(BaseModel):
    list: list[FavoriteItem]
    total: int
    has_more: bool

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象取值
        populate_by_name=True,
    )
