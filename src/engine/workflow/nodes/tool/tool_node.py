import json
import time
from typing import Optional, Any

from langgraph.types import Command
from pydantic import PrivateAttr
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from src.engine.tools.api.entities.tool_entity import ToolEntity
from src.engine.workflow.node_entity import NodeResult, NodeStatus
from src.engine.workflow.workflow_entity import WorkflowState
from src.engine.workflow.nodes.base_node import BaseNode
from src.engine.helper import extract_variables_from_state
from src.core.exception.exception import FailException, NotFoundException
from src.engine.workflow.nodes.tool.tool_entity import ToolNodeData
from src.store.model import ApiTool, ApiToolProvider


class ToolNode(BaseNode):
    """扩展插件节点"""
    node_data: ToolNodeData
    _tool: BaseTool = PrivateAttr(None)

    def __init__(self, *args: Any, **kwargs: Any):
        """构造函数，完成对内置工具的初始化"""
        # 1.调用父类构造函数完成数据初始化
        super().__init__(*args, **kwargs)
        # 2.导入依赖注入及工具提供者
        from src.core.di_config import injector
        # 3.判断是内置插件还是API插件，执行不同的操作
        if self.node_data.tool_type == "builtin_tool":
            from src.engine.tools.builtin.provider_manager import BuiltinProviderManager
            builtin_provider_manager = injector.get(BuiltinProviderManager)

            # 4.调用内置提供者获取内置插件
            _tool = builtin_provider_manager.get_tool(self.node_data.provider_id, self.node_data.tool_id)
            if not _tool:
                raise NotFoundException("该内置插件扩展不存在，请核实后重试")

            self._tool = _tool(**self.node_data.params)
        else:
            # 5.API插件，调用数据库查询记录并创建API插件
            from src.store.database_manager import DatabaseManager
            db = injector.get(DatabaseManager)

            # 6.根据传递的提供者名字+工具名字查询工具
            api_tool = db.session.query(ApiTool).filter(
                ApiTool.provider_id == self.node_data.provider_id,
                ApiTool.name == self.node_data.tool_id
            ).one_or_none()
            if not api_tool:
                raise NotFoundException("该API扩展插件不存在，请核实重试")

            # @property
            # def provider(self) -> "ApiToolProvider":
            #     """只读属性，返回当前工具关联/归属的工具提供者信息"""
            #     return self.session.query(ApiToolProvider).get(self.provider_id)
            tool_provider = db.session.query(ApiToolProvider).get(api_tool.provider_id)

            # 7.导入API插件提供者
            from src.engine.tools.api.providers import ApiProviderManager
            api_provider_manager = injector.get(ApiProviderManager)

            # 8.创建API工具提供者并赋值
            self._tool = api_provider_manager.get_tool(ToolEntity(
                id=str(api_tool.id),
                name=api_tool.name,
                url=api_tool.url,
                method=api_tool.method,
                description=api_tool.description,
                headers=tool_provider.headers,
                parameters=api_tool.parameters,
            ))

    def invoke(self, state: WorkflowState, config: Optional[RunnableConfig] = None) -> Command:
        """扩展插件执行节点，根据传递的信息调用预设的插件，涵盖内置插件及API插件"""
        # 1.提取节点中的输入数据
        start_at = time.perf_counter()
        inputs_dict = extract_variables_from_state(self.node_data.inputs, state)

        # 2.调用插件并获取结果
        try:
            result = self._tool.invoke(inputs_dict)
        except Exception as e:
            raise FailException("扩展插件执行失败，请稍后尝试")

        # 3.检测result是否为字符串，如果不是则转换
        if not isinstance(result, str):
            result = json.dumps(result)

        # 4.提取并构建输出数据结构
        outputs = {}
        if self.node_data.outputs:
            outputs[self.node_data.outputs[0].name] = result
        else:
            outputs["text"] = result

        # 5.构建响应状态并返回
        # state["node_results"] = [NodeResult(
        #             node_data=self.node_data,
        #             status=NodeStatus.SUCCEEDED,
        #             inputs=inputs_dict,
        #             outputs=outputs,
        #             latency=(time.perf_counter() - start_at),
        #         )]
        # return state

        return Command(
            update={
                "node_results": [
                    NodeResult(
                        node_data=self.node_data,
                        status=NodeStatus.SUCCEEDED,
                        inputs=inputs_dict,
                        outputs=outputs,
                        latency=(time.perf_counter() - start_at),
                    )
                ]}
        )

        # return {
        #     "node_results": [
        #         NodeResult(
        #             node_data=self.node_data,
        #             status=NodeStatus.SUCCEEDED,
        #             inputs=inputs_dict,
        #             outputs=outputs,
        #             latency=(time.perf_counter() - start_at),
        #         )
        #     ]
        # }
