from typing import Any, Optional, AsyncGenerator
from dotenv import load_dotenv
import time
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
from src.store.model import Workflow, ApiTool, WorkflowResult
from src.lib.helper import convert_model_to_dict
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

    async def debug_workflow(self, workflow_id: str, inputs: dict[str, Any], account: str) -> AsyncGenerator:
        """调试指定的工作流API接口，该接口为流式事件输出（异步版本）"""
        # 1.根据传递的id获取工作流并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.创建工作流工具
        workflow_tool = WorkflowTool(workflow_config=WorkflowConfig(
            account_id=account,
            name=workflow.tool_call_name,
            description=workflow.description,
            nodes=workflow.draft_graph.get("nodes", []),
            edges=workflow.draft_graph.get("edges", []),
        ))

        # 3.定义变量存储所有节点运行结果
        node_results = []

        # 4.添加数据库工作流运行结果记录
        workflow_result = self.create(WorkflowResult, **{
            "app_id": None,
            "account_id": account,
            "workflow_id": workflow.id,
            "graph": workflow.draft_graph,
            "state": [],
            "latency": 0,
            "status": WorkflowResultStatus.RUNNING,
        })
        async for chunk in workflow_tool.stream_events(inputs):
            yield chunk

    def get_workflow(self, workflow_id: str, account: str) -> Workflow:
        """根据传递的工作流id，获取指定的工作流基础信息"""
        # 1.查询数据库获取工作流基础信息
        workflow = self.get(Workflow, workflow_id)

        # 2.判断工作流是否存在
        if not workflow:
            raise NotFoundException("该工作流不存在，请核实后重试")

        # 3.判断当前账号是否有权限访问该应用
        if workflow.account_id != account:
            raise ForbiddenException("当前账号无权限访问该应用，请核实后尝试")

        return workflow

    def delete_workflow(self, workflow_id: str, account: str) -> Workflow:
        """根据传递的工作流id+账号信息，删除指定的工作流"""
        # 1.获取工作流基础信息并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.删除工作流
        self.delete(workflow)

        return workflow

    def update_draft_graph(self, workflow_id: str, draft_graph: dict[str, Any], account: str) -> Workflow:
        """根据传递的工作流id+草稿图配置+账号更新工作流的草稿图"""
        # 1.根据传递的id获取工作流并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.校验传递的草稿图配置，因为有可能边有可能还未建立，所以需要校验关联的数据
        # validate_draft_graph = self._validate_graph(draft_graph)

        # 3.更新工作流草稿图配置，每次修改都将is_debug_passed的值重置为False，该处可以优化对比字典里除position的其他属性
        # self.update(workflow, **{
        #     "draft_graph": validate_draft_graph,
        #     "is_debug_passed": False,
        # })

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
        # 1.根据传递的id获取工作流并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.提取草稿图结构信息并校验(不更新校验后的数据到数据库)
        draft_graph = workflow.draft_graph
        # validate_draft_graph = self._validate_graph(draft_graph)
        validate_draft_graph = draft_graph

        # 3.循环遍历节点信息，为工具节点/知识库节点附加元数据
        for node in validate_draft_graph["nodes"]:
            if node.get("node_type") == NodeType.TOOL:
                # 4.判断工具的类型执行不同的操作
                if node.get("tool_type") == "builtin_tool":
                    # 5.节点类型为工具，则附加工具的名称、图标、参数等额外信息
                    provider = self.builtin_provider_manager.get_provider(node.get("provider_id"))
                    if not provider:
                        continue

                    # 6.获取提供者下的工具实体，并检测是否存在
                    tool_entity = provider.get_tool_entity(node.get("tool_id"))
                    if not tool_entity:
                        continue

                    # 7.判断工具的params和草稿中的params是否一致，如果不一致则全部重置为默认值（或者考虑删除这个工具的引用）
                    param_keys = set([param.name for param in tool_entity.params])
                    params = node.get("params")
                    if set(params.keys()) - param_keys:
                        params = {
                            param.name: param.default
                            for param in tool_entity.params
                            if param.default is not None
                        }

                    # 8.数据校验成功附加展示信息
                    provider_entity = provider.provider_entity
                    node["meta"] = {
                        "type": "builtin_tool",
                        "provider": {
                            "id": provider_entity.name,
                            "name": provider_entity.name,
                            "label": provider_entity.label,
                            # "icon": f"{request.scheme}://{request.host}/builtin-tools/{provider_entity.name}/icon",
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
                    # 9.查询数据库获取对应的工具记录，并检测是否存在
                    tool_record = self.database_manager.session.query(ApiTool).filter(
                        ApiTool.provider_id == node.get("provider_id"),
                        ApiTool.name == node.get("tool_id"),
                        ApiTool.account_id == account,
                    ).one_or_none()
                    if not tool_record:
                        continue

                    # 10.组装api工具展示信息
                    provider = tool_record.provider
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
                else:
                    node["meta"] = {
                        "type": "api_tool",
                        "provider": {
                            "id": "",
                            "name": "",
                            "label": "",
                            "icon": "",
                            "description": "",
                        },
                        "tool": {
                            "id": "",
                            "name": "",
                            "label": "",
                            "description": "",
                            "params": {},
                        },
                    }

        return validate_draft_graph

    def _validate_graph(self, graph: dict[str, Any]) -> dict[str, Any]:
        """校验传递的graph信息，涵盖nodes和edges对应的数据，该函数使用相对宽松的校验方式，并且因为是草稿，不需要校验节点与边的关系"""
        # 1.提取nodes和edges数据
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # 2.构建节点类型与节点数据类映射
        node_data_classes = {
            NodeType.START: StartNodeData,
            NodeType.END: EndNodeData,
            NodeType.LLM: LLMNodeData,
            NodeType.TOOL: ToolNodeData,
        }

        # 3.循环校验nodes中各个节点对应的数据
        node_data_dict: dict[str, BaseNodeData] = {}
        start_nodes = 0
        end_nodes = 0
        for node in nodes:
            try:
                # 4.校验传递的node数据是不是字典，如果不是则跳过当前数据
                if not isinstance(node, dict):
                    raise ValidateErrorException("工作流节点数据类型出错，请核实后重试")

                # 5.提取节点的node_type类型，并判断类型是否正确
                node_type = node.get("node_type", "")
                node_data_cls = node_data_classes.get(node_type, None)
                if node_data_cls is None:
                    raise ValidateErrorException("工作流节点类型出错，请核实后重试")

                # 6.实例化节点数据类型，如果出错则跳过当前数据
                node_data = node_data_cls(**node)

                # 7.判断节点id是否唯一，如果不唯一，则将当前节点清除
                if node_data.id in node_data_dict:
                    raise ValidateErrorException("工作流节点id必须唯一，请核实后重试")

                # 8.判断节点title是否唯一，如果不唯一，则将当前节点清除
                if any(item.title.strip() == node_data.title.strip() for item in node_data_dict.values()):
                    raise ValidateErrorException("工作流节点title必须唯一，请核实后重试")

                # 9.对特殊节点进行判断，涵盖开始/结束/知识库检索/工具
                if node_data.node_type == NodeType.START:
                    if start_nodes >= 1:
                        raise ValidateErrorException("工作流中只允许有1个开始节点")
                    start_nodes += 1
                elif node_data.node_type == NodeType.END:
                    if end_nodes >= 1:
                        raise ValidateErrorException("工作流中只允许有1个结束节点")
                    end_nodes += 1

                # 11.将数据添加到node_data_dict中
                node_data_dict[node_data.id] = node_data
            except Exception:
                continue

        # 14.循环校验edges中各个节点对应的数据
        edge_data_dict: dict[str, BaseEdgeData] = {}
        for edge in edges:
            try:
                # 15.边类型为非字典则抛出错误，否则转换成BaseEdgeData
                if not isinstance(edge, dict):
                    raise ValidateErrorException("工作流边数据类型出错，请核实后重试")
                edge_data = BaseEdgeData(**edge)

                # 16.校验边edges的id是否唯一
                if edge_data.id in edge_data_dict:
                    raise ValidateErrorException("工作流边数据id必须唯一，请核实后重试")

                # 17.校验边中的source/target/source_type/target_type必须和nodes对得上
                if (
                        edge_data.source not in node_data_dict
                        or edge_data.source_type != node_data_dict[edge_data.source].node_type
                        or edge_data.target not in node_data_dict
                        or edge_data.target_type != node_data_dict[edge_data.target].node_type
                ):
                    raise ValidateErrorException("工作流边起点/终点对应的节点不存在或类型错误，请核实后重试")

                # 18.校验边Edges里的边必须唯一(source+target必须唯一)
                if any(
                        (item.source == edge_data.source and item.target == edge_data.target)
                        for item in edge_data_dict.values()
                ):
                    raise ValidateErrorException("工作流边数据不能重复添加")

                # 19.基础数据校验通过，将数据添加到edge_data_dict中
                edge_data_dict[edge_data.id] = edge_data
            except Exception:
                continue

        return {
            "nodes": [convert_model_to_dict(node_data) for node_data in node_data_dict.values()],
            "edges": [convert_model_to_dict(edge_data) for edge_data in edge_data_dict.values()],
        }

    async def create_workflow(self, req: Optional[CreateWorkflowReq], account: str) -> Optional[Workflow]:
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
