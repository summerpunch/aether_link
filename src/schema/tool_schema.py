from typing import List, Dict
from pydantic import BaseModel, Field, HttpUrl, field_validator, ValidationError


class HeaderItem(BaseModel):
    """单个 header 对象校验"""
    key: str = Field(..., description="Header 的键名")
    value: str = Field(..., description="Header 的键值")

class CreateApiToolReq(BaseModel):
    """创建自定义API工具请求"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="工具提供者名字",
        examples=["My API Tool"],
    )
    icon: str = Field(
        ...,
        description="工具提供者的图标 URL",
        examples=["https://example.com/icon.png"],
    )
    openapi_schema: str = Field(
        ...,
        description="OpenAPI schema 字符串",
        examples=["{\"openapi\": \"3.0.0\"}"],
    )
    headers: List[HeaderItem] = Field(
        default_factory=list,
        description="请求头列表，元素包含 key/value",
        examples=[[{"key": "Authorization", "value": "Bearer token"}]],
    )

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v):
        """列表及元素结构校验"""
        for header in v:
            # Pydantic 已确保 header 为 HeaderItem，因此无需类型再判断
            if set(header.model_dump().keys()) != {"key", "value"}:
                raise ValueError("headers里的每一个元素都必须包含key/value两个属性，不允许有其他属性")
        return v
