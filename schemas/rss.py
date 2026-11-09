from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RssFeedIn(BaseModel):
    name: str = Field(..., max_length=100)
    url: str = Field(..., max_length=500)
    # 不传就自动建一个同名分类，首页 tab 用这个名字
    category_id: int | None = Field(None, alias="categoryId")
    fetch_interval: int = Field(900, ge=300, le=86400, alias="fetchInterval")
    enabled: bool = True

    model_config = ConfigDict(populate_by_name=True)


class RssFeedPatch(BaseModel):
    name: str | None = Field(None, max_length=100)
    category_id: int | None = Field(None, alias="categoryId")
    fetch_interval: int | None = Field(None, ge=300, le=86400, alias="fetchInterval")
    enabled: bool | None = None

    model_config = ConfigDict(populate_by_name=True)


class RssFeedOut(BaseModel):
    id: int
    name: str
    url: str
    site_url: str | None = Field(None, alias="siteUrl")
    category_id: int = Field(..., alias="categoryId")
    enabled: bool
    fetch_interval: int = Field(..., alias="fetchInterval")
    last_fetch_at: datetime | None = Field(None, alias="lastFetchAt")
    last_status: str | None = Field(None, alias="lastStatus")
    last_error: str | None = Field(None, alias="lastError")
    error_count: int = Field(..., alias="errorCount")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
