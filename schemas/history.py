from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HistoryItem(BaseModel):
    id: int
    news_id: int
    update_time: datetime
    title: str
    description: str | None = None
    image: str | None = None
    author: str | None = None
    category_id: int = Field(alias="categoryId")
    views: int
    publish_time: datetime | None = Field(None, alias="publishedTime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HistoryListResponse(BaseModel):
    list: list[HistoryItem]
    total: int
    has_more: bool

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许从ORM对象取值
    )
