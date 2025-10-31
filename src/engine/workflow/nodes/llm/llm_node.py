import time
from typing import Optional
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.enums.workflow_enum import NodeStatus
from src.engine.workflow.node_entity import NodeResult
from src.engine.workflow.workflow_entity import WorkflowState
from src.engine.workflow.nodes.base_node import BaseNode
from src.engine.helper import extract_variables_from_state

from src.engine.workflow.nodes.llm.llm_entity import LLMNodeData


class LLMNode(BaseNode):
    node_data: LLMNodeData

    def invoke(self, state: WorkflowState, config: Optional[RunnableConfig] = None) -> Command:
        """大语言模型节点调用工具，根据输入字段+预设prompt生成对应内容后输出"""
        # 1.提取节点中的输入数据
        start_at = time.perf_counter()
        inputs_dict = extract_variables_from_state(self.node_data.inputs, state)
        # 2.使用jinja2格式模板信息
        template = Template(self.node_data.prompt)
        prompt_value = template.render(**inputs_dict)

        # 3.通过依赖管理器获取language_model_service并加载模型
        # from app.http.module import injector
        # from internal.service import LanguageModelService
        #
        # language_model_service = injector.get(LanguageModelService)
        # llm = language_model_service.load_language_model(self.node_data.language_model_config)
        from langchain.agents import create_agent

        from langchain_openai import ChatOpenAI
        import httpx

        llm = ChatOpenAI(
            model="DeepSeek-V3.1",
            base_url="https://llm-guard.mininglamp.com/v1",
            api_key="sk-D9Ct1QbqDNpsaYv6B7C8AbDaA2Ea4a338c0b1d5d95FfD3E6",
            temperature=0,
            http_client=httpx.Client(verify=False),
            http_async_client=httpx.AsyncClient(verify=False)
        )

        # if self.node_data.tools:
        from src.engine.tools.builtin.providers.time import current_time
        print("绑定了tool")

        from src.core.di_config import injector
        from src.engine.tools.builtin.provider_manager import BuiltinProviderManager
        builtin_provider_manager = injector.get(BuiltinProviderManager)

        # 4.调用内置提供者获取内置插件
        _tool = builtin_provider_manager.get_tool("time", "current_time")
        # if not _tool:
        #     raise NotFoundException("该内置插件扩展不存在，请核实后重试")

        _tool = _tool(**{})
        # print(_tool)
        # from src.engine.tools.builtin.providers.time.current_time import get_current_time
        # llm.bind_tools([get_current_time])

        agent = create_agent(
            model=llm,
            tools=[_tool],
            system_prompt=prompt_value,
        )

        # 4.使用stream来代替invoke，避免接口长时间未响应超时
        # content = ""
        print(inputs_dict)
        content = agent.invoke(inputs_dict)
        # for chunk in agent.invoke(inputs_dict):
        #     content += chunk.content
        print(content)
        print("---------------")

        # 5.提取并构建输出数据结构
        outputs = {}
        if self.node_data.outputs:
            outputs[self.node_data.outputs[0].name] = content
        else:
            outputs["output"] = content

        # 6.构建响应状态并返回

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
        #
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
