from typing import Any, Optional, AsyncGenerator
from dotenv import load_dotenv
import logging
from src.core.exception.exception import ValidateErrorException, NotFoundException, ForbiddenException
from src.engine.tools.builtin.provider_manager import BuiltinProviderManager
from src.engine.workflow.edge_entity import BaseEdgeData
from src.engine.workflow.nodes.end.end_entity import EndNodeData
from src.engine.workflow.nodes.llm.llm_entity import LLMNodeData
from src.engine.workflow.nodes.start.start_entity import StartNodeData
from src.engine.workflow.nodes.tool.tool_entity import ToolNodeData
from src.engine.workflow.workflow_entity import WorkflowConfig
from src.schema.workflow_schema import CreateWorkflowReq
from src.store.model import Workflow, ApiTool, WorkflowResult, ApiToolProvider
from src.core.lib.helper import convert_model_to_dict
from src.engine.workflow.node_entity import NodeType, BaseNodeData

load_dotenv()

logger = logging.getLogger(__name__)
from injector import inject
from src.store.database_manager import DatabaseManager
from src.service.base_service import BaseService
from dataclasses import dataclass
from src.enums.workflow_enum import WorkflowStatus, DEFAULT_WORKFLOW_CONFIG, WorkflowResultStatus
from src.engine.workflow.workflow import Workflow as WorkflowTool


@inject
@dataclass
class WorkflowService(BaseService):
    database_manager: DatabaseManager
    builtin_provider_manager: BuiltinProviderManager

    async def debug(self, workflow_id: str, inputs: dict[str, Any], account: str) -> AsyncGenerator:
        """调试指定的工作流API接口，该接口为流式事件输出（异步版本）"""
        workflow = self.get_workflow(workflow_id, account)
        workflow_tool = WorkflowTool(workflow_config=WorkflowConfig(
            account_id=account,
            name=workflow.tool_call_name,
            description=workflow.description,
            nodes=workflow.draft_graph.get("nodes", []),
            edges=workflow.draft_graph.get("edges", []),
        ))
        async for chunk in workflow_tool.stream_events(inputs):
            yield chunk

    def get_workflow(self, workflow_id: str, account: str) -> Workflow:
        """根据传递的工作流id，获取指定的工作流基础信息"""

        workflow = self.get(Workflow, workflow_id)

        if not workflow:
            raise NotFoundException("该工作流不存在，请核实后重试")

        if workflow.account_id != account:
            raise ForbiddenException("当前账号无权限访问该应用，请核实后尝试")

        return workflow

    def delete(self, workflow_id: str, account: str) -> bool:
        """根据传递的工作流id+账号信息，删除指定的工作流"""
        return self.delete_by_filter(
            model=Workflow,
            filters={
                "id": f"{workflow_id}",
                "account_id": f"{account}",
            }
        ) > 0

    def update_draft_graph(self,
                           workflow_id: str,
                           draft_graph: dict[str, Any],
                           account: str) -> Workflow:
        """根据传递的工作流id+草稿图配置+账号更新工作流的草稿图"""

        workflow = self.get_workflow(workflow_id, account)

        self.update_by_filter(
            model=Workflow,
            filters={
                "id": f"{workflow_id}",
            },
            update_fields={
                "draft_graph": draft_graph,
                "is_debug_passed": False
            }
        )

        return workflow

    def get_draft_graph(self, workflow_id: str, account: str) -> dict[str, Any]:
        """根据传递的工作流id+账号信息，获取指定工作流的草稿配置信息"""
        workflow = self.get_workflow(workflow_id, account)
        draft_graph = workflow.draft_graph
        for node in draft_graph["nodes"]:
            if node.get("node_type") == NodeType.TOOL:
                if node.get("tool_type") == "builtin_tool":
                    provider = self.builtin_provider_manager.get_provider(node.get("provider_id"))
                    if not provider:
                        continue
                    tool_entity = provider.get_tool_entity(node.get("tool_id"))
                    if not tool_entity:
                        continue
                    param_keys = set([param.name for param in tool_entity.params])
                    params = node.get("params")
                    if set(params.keys()) - param_keys:
                        params = {
                            param.name: param.default
                            for param in tool_entity.params
                            if param.default is not None
                        }

                    provider_entity = provider.provider_entity
                    node["meta"] = {
                        "type": "builtin_tool",
                        "provider": {
                            "id": provider_entity.name,
                            "name": provider_entity.name,
                            "label": provider_entity.label,
                            "icon": "icon",
                            "description": provider_entity.description,
                        },
                        "tool": {
                            "id": tool_entity.name,
                            "name": tool_entity.name,
                            "label": tool_entity.label,
                            "description": tool_entity.description,
                            "params": params,
                        }
                    }
                elif node.get("tool_type") == "api_tool":
                    tool_record = self.database_manager.session.query(ApiTool).filter(
                        ApiTool.provider_id == node.get("provider_id"),
                        ApiTool.name == node.get("tool_id"),
                        ApiTool.account_id == account,
                    ).one_or_none()
                    if not tool_record:
                        continue

                    provider = self.database_manager.session.query(ApiToolProvider).filter(
                        ApiToolProvider.id == node.get("provider_id")
                    ).one_or_none()

                    node["meta"] = {
                        "type": "api_tool",
                        "provider": {
                            "id": str(provider.id),
                            "name": provider.name,
                            "label": provider.name,
                            "icon": provider.icon,
                            "description": provider.description,
                        },
                        "tool": {
                            "id": str(tool_record.id),
                            "name": tool_record.name,
                            "label": tool_record.name,
                            "description": tool_record.description,
                            "params": {},
                        },
                    }

        return draft_graph

    def create_workflow(self, req: Optional[CreateWorkflowReq], account: str) -> Optional[Workflow]:
        """根据传递的请求信息创建工作流"""
        check_workflow = self.database_manager.session.query(Workflow).filter(
            Workflow.tool_call_name == req.tool_call_name.strip(),
            Workflow.account_id == account,
        ).one_or_none()

        if check_workflow:
            raise ValidateErrorException(f"在当前账号下已创建[{req.tool_call_name}]工作流，不支持重名")

        return self.create(Workflow, **{
            **req.model_dump(),
            **DEFAULT_WORKFLOW_CONFIG,
            "account_id": account,
            "is_debug_passed": False,
            "status": WorkflowStatus.DRAFT,
            "tool_call_name": req.tool_call_name.strip(),
        })
