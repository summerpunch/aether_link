from src.core.exception.exception import ValidateErrorException
from src.engine.tools.api.entities import OpenAPISchema
from src.engine.tools.builtin.provider_manager import BuiltinProviderManager
from injector import inject
import json
from src.schema.tool_schema import CreateApiToolReq
from src.service.base_service import BaseService
from dataclasses import dataclass
from src.store.database_manager import DatabaseManager
from pydantic import BaseModel, create_model, Field

from src.store.model import ApiToolProvider, ApiTool


@inject
@dataclass
class ToolService(BaseService):
    database_manager: DatabaseManager
    builtin_provider_manager: BuiltinProviderManager

    def get_tool_inputs(self, tool) -> list:
        """根据传入的工具获取inputs信息"""
        inputs = []
        if hasattr(tool, "args_schema") and issubclass(tool.args_schema, BaseModel):
            for field_name, model_field in tool.args_schema.model_fields.items():
                inputs.append({
                    "name": field_name,
                    "description": model_field.field_info.description or "",
                    "required": model_field.required,
                    "type": model_field.outer_type_.__name__,
                })
        return inputs

    @classmethod
    def parse_openapi_schema(cls, openapi_schema_str: str) -> OpenAPISchema:
        """解析传递的openapi_schema字符串，如果出错则抛出错误"""
        try:
            data = json.loads(openapi_schema_str.strip())
            if not isinstance(data, dict):
                raise
        except Exception as e:
            raise ValidateErrorException("传递数据必须符合OpenAPI规范的JSON字符串")

        return OpenAPISchema(**data)

    async def create_api_tool(self, req: CreateApiToolReq, account: str):
        """根据传递的请求创建自定义API工具"""
        # 1.检验并提取openapi_schema对应的数据
        openapi_schema = self.parse_openapi_schema(req.openapi_schema)

        # 2.查询当前登录的账号是否已经创建了同名的工具提供者，如果是则抛出错误
        api_tool_provider = self.database_manager.session.query(ApiToolProvider).filter_by(
            account_id=account,
            name=req.name,
        ).one_or_none()
        if api_tool_provider:
            raise ValidateErrorException(f"该工具提供者名字{req.name}已存在")

        # 3.首先创建工具提供者，并获取工具提供者的id信息，然后在创建工具信息
        api_tool_provider = self.create(
            ApiToolProvider,
            account_id=account,
            name=req.name,
            icon=req.icon,
            description=openapi_schema.description,
            openapi_schema=req.openapi_schema,
            headers=req.headers,
        )

        # 4.创建api工具并关联api_tool_provider
        for path, path_item in openapi_schema.paths.items():
            for method, method_item in path_item.items():
                self.create(
                    ApiTool,
                    account_id=account,
                    provider_id=api_tool_provider.id,
                    name=method_item.get("operationId"),
                    description=method_item.get("description"),
                    url=f"{openapi_schema.server}{path}",
                    method=method,
                    parameters=method_item.get("parameters", []),
                )


async def get_builtin_tools(self):
    providers = self.builtin_provider_manager.get_providers()
    builtin_tools = []
    for provider in providers:
        provider_entity = provider.provider_entity
        builtin_tool = {
            **provider_entity.model_dump(exclude=["icon"]),
            "tools": [],
        }
        for tool_entity in provider.get_tool_entities():
            tool = provider.get_tool(tool_entity.name)
            tool_dict = {
                **tool_entity.model_dump(),
                "inputs": self.get_tool_inputs(tool),
            }
            builtin_tool["tools"].append(tool_dict)

        builtin_tools.append(builtin_tool)

    return builtin_tools
