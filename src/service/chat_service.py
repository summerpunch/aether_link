
import logging
from dataclasses import dataclass
from datetime import datetime
from threading import Thread
from typing import Any
from uuid import UUID

from injector import inject
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from .base_service import BaseService
from ..engine.agent.entities.queue_entity import AgentThought, QueueEvent
from ..engine.conversation_entity import InvokeFrom
from ..store.database_manager import DatabaseManager
from ..store.model import Conversation, Message, MessageAgentThought


@inject
@dataclass
class ChatService(BaseService):
    """会话服务"""
    database_manager: DatabaseManager


    def save_agent_thoughts(
            self,
            account_id: str,
            app_id: str,
            app_config: dict[str, Any],
            conversation_id: str,
            message_id: str,
            agent_thoughts: list[AgentThought],
    ):
        """存储智能体推理步骤消息"""
        # 1.定义变量存储推理位置及总耗时
        position = 0
        latency = 0

        # 2.在子线程中重新查询conversation以及message，确保对象会被子线程的会话管理到
        conversation = self.get(Conversation, conversation_id)
        message = self.get(Message, message_id)

        # 3.循环遍历所有的智能体推理过程执行存储操作
        for agent_thought in agent_thoughts:
            # 4.存储长期记忆召回、推理、消息、动作、知识库检索等步骤
            if agent_thought.event in [
                QueueEvent.LONG_TERM_MEMORY_RECALL,
                QueueEvent.AGENT_THOUGHT,
                QueueEvent.AGENT_MESSAGE,
                QueueEvent.AGENT_ACTION,
                QueueEvent.DATASET_RETRIEVAL,
            ]:
                # 5.更新位置及总耗时
                position += 1
                latency += agent_thought.latency

                # 6.创建智能体消息推理步骤
                self.create(
                    MessageAgentThought,
                    app_id=app_id,
                    conversation_id="111",
                    message_id="222",
                    invoke_from=InvokeFrom.DEBUGGER,
                    created_by=account_id,
                    position=position,
                    event=agent_thought.event,
                    thought=agent_thought.thought,
                    observation=agent_thought.observation,
                    tool=agent_thought.tool,
                    tool_input=agent_thought.tool_input,
                    # 消息相关数据
                    message=agent_thought.message,
                    message_token_count=agent_thought.message_token_count,
                    message_unit_price=agent_thought.message_unit_price,
                    message_price_unit=agent_thought.message_price_unit,
                    # 答案相关字段
                    answer=agent_thought.answer,
                    answer_token_count=agent_thought.answer_token_count,
                    answer_unit_price=agent_thought.answer_unit_price,
                    answer_price_unit=agent_thought.answer_price_unit,
                    # Agent推理统计相关
                    total_token_count=agent_thought.total_token_count,
                    total_price=agent_thought.total_price,
                    latency=agent_thought.latency,
                )

            # 7.检测事件是否为Agent_message
            if agent_thought.event == QueueEvent.AGENT_MESSAGE:
                # 8.更新消息信息
                self.update(
                    message,
                    # 消息相关字段
                    message=agent_thought.message,
                    message_token_count=agent_thought.message_token_count,
                    message_unit_price=agent_thought.message_unit_price,
                    message_price_unit=agent_thought.message_price_unit,
                    # 答案相关字段
                    answer=agent_thought.answer,
                    answer_token_count=agent_thought.answer_token_count,
                    answer_unit_price=agent_thought.answer_unit_price,
                    answer_price_unit=agent_thought.answer_price_unit,
                    # Agent推理统计相关
                    total_token_count=agent_thought.total_token_count,
                    total_price=agent_thought.total_price,
                    latency=latency,
                )

                # 9.检测是否开启长期记忆
                # if app_config["long_term_memory"]["enable"]:
                #     Thread(
                #         target=self._generate_summary_and_update,
                #         kwargs={
                #             "flask_app": current_app._get_current_object(),
                #             "conversation_id": conversation.id,
                #             "query": message.query,
                #             "answer": agent_thought.answer,
                #         },
                #     ).start()

                # 10.处理生成新会话名称
                # if conversation.is_new:
                #     Thread(
                #         target=self._generate_conversation_name_and_update,
                #         kwargs={
                #             "flask_app": current_app._get_current_object(),
                #             "conversation_id": conversation.id,
                #             "query": message.query,
                #         }
                #     ).start()

            # 11.判断是否为停止或者错误，如果是则需要更新消息状态
            if agent_thought.event in [QueueEvent.TIMEOUT, QueueEvent.STOP, QueueEvent.ERROR]:
                self.update(
                    message,
                    status=agent_thought.event,
                    error=agent_thought.observation,
                )
                break
