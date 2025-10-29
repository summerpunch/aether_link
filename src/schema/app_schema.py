from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator, ValidationError, conint, constr


class AllRequest(BaseModel):
    """标签请求 - 接受任意JSON结构"""

    class Config:
        extra = "allow"  # 允许额外字段

    def __init__(self, **data):
        super().__init__(**data)

    def dict(self, **kwargs):
        """返回字典格式，包含所有字段"""
        return super().dict(**kwargs)


class CreateAppReq(BaseModel):
    """创建Agent应用请求结构体"""
    name: str = Field(..., description="name")
    description: str = Field(..., description="description")
    icon: str = Field(..., description="icon")


class ChatReq(BaseModel):
    """应用调试会话请求结构体"""
    app_id: str = Field(..., description="app_id")
    query: str = Field(..., description="用户提问内容")
    image_urls: list = Field(default_factory=list, description="用户提问内容")
