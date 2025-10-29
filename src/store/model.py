"""
数据库模型定义
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import make_transient
from src.engine.conversation_entity import InvokeFrom
from typing import Dict, Any, TypeVar
from sqlalchemy import (
    Column,
    UUID,
    String,
    Text,
    Boolean,
    DateTime,
    Float,
    text,
    PrimaryKeyConstraint,
    Index,
    Integer, Numeric,
)

Base = declarative_base()

T = TypeVar('T', bound='SerializableMixin')


class SerializableMixin:
    """序列化混入类，为所有模型提供通用的序列化功能"""

    def to_dict(self) -> Dict[str, Any]:
        """将对象转换为字典"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.strftime("%Y-%m-%d %H:%M:%S") if value else None
            elif isinstance(value, Decimal):
                result[column.name] = float(value)
            else:
                result[column.name] = value
        return result

class App(Base, SerializableMixin):
    """AI应用基础模型类"""
    __tablename__ = "app"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(100), nullable=False)  # 创建账号id
    app_config_id = Column(String(100), nullable=True)  # 发布配置id，当值为空时代表没有发布
    draft_app_config_id = Column(String(100), nullable=True)  # 关联的草稿配置id
    debug_conversation_id = Column(String(100), nullable=True)  # 应用调试会话id，为None则代表没有会话信息
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 应用名字
    icon = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 应用图标
    description = Column(Text, nullable=False, server_default=text("''::text"))  # 应用描述
    token = Column(String(255), nullable=True, server_default=text("''::character varying"))  # 应用凭证信息
    status = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 应用状态
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    @property
    def debug_conversation(self) -> "Conversation":
        """获取应用的调试会话记录"""
        # 1.根据debug_conversation_id获取调试会话记录
        debug_conversation = None
        from src.store.database_manager import _database_manager
        if self.debug_conversation_id is not None:
            debug_conversation = _database_manager.session.query(Conversation).filter(
                Conversation.id == self.debug_conversation_id,
                Conversation.invoke_from == InvokeFrom.DEBUGGER,
            ).one_or_none()

        # 2.检测数据是否存在，如果不存在则创建
        if not self.debug_conversation_id or not debug_conversation:
            # 3.开启数据库自动提交上下文
            with _database_manager.auto_commit():
                # 4.创建应用调试会话记录并刷新获取会话id
                debug_conversation = Conversation(
                    app_id=self.id,
                    name="New Conversation",
                    invoke_from=InvokeFrom.DEBUGGER,
                    created_by=self.account_id,
                )
                _database_manager.session.add(debug_conversation)
                _database_manager.session.flush()
                _database_manager.session.expunge(debug_conversation)

                # 5.更新当前记录的debug_conversation_id
                self.debug_conversation_id = debug_conversation.id

        return debug_conversation


class AppConfig(Base, SerializableMixin):
    """应用配置模型"""
    __tablename__ = "app_config"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(100), nullable=False)  # 关联应用id
    model_config = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 模型配置
    dialog_round = Column(Integer, nullable=False, server_default=text("0"))  # 鞋带上下文轮数
    preset_prompt = Column(Text, nullable=False, server_default=text("''::text"))  # 预设prompt
    tools = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 应用关联工具列表
    workflows = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 应用关联的工作流列表
    retrieval_config = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 检索配置
    long_term_memory = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 长期记忆配置
    opening_statement = Column(Text, nullable=False, server_default=text("''::text"))  # 开场白文案
    opening_questions = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 开场白建议问题列表
    speech_to_text = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 语音转文本配置
    text_to_speech = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 文本转语音配置
    suggested_after_answer = Column(
        JSONB,
        nullable=False,
        server_default=text("'{\"enable\": true}'::jsonb"),
    )  # 回答后生成建议问题
    review_config = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 审核配置
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AppConfigVersion(Base, SerializableMixin):
    """应用配置版本历史表，用于存储草稿配置+历史发布配置"""
    __tablename__ = "app_config_version"

    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(100), nullable=False)  # 关联应用id
    model_config = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 模型配置
    dialog_round = Column(Integer, nullable=False, server_default=text("0"))  # 鞋带上下文轮数
    preset_prompt = Column(Text, nullable=False, server_default=text("''::text"))  # 人设与回复逻辑
    tools = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 应用关联的工具列表
    workflows = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 应用关联的工作流列表
    datasets = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 应用关联的知识库列表
    retrieval_config = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 检索配置
    long_term_memory = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 长期记忆配置
    opening_statement = Column(Text, nullable=False, server_default=text("''::text"))  # 开场白文案
    opening_questions = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 开场白建议问题列表
    speech_to_text = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 语音转文本配置
    text_to_speech = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 文本转语音配置
    suggested_after_answer = Column(
        JSONB,
        nullable=False,
        server_default=text("'{\"enable\": true}'::jsonb"),
    )  # 回答后生成建议问题
    review_config = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 审核配置
    version = Column(Integer, nullable=False, server_default=text("0"))  # 发布版本号
    config_type = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 配置类型
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Workflow(Base, SerializableMixin):
    """工作流模型"""
    __tablename__ = "workflow"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 工作流名字
    tool_call_name = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 工作流工具调用名字
    icon = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 工作流图标
    description = Column(Text, nullable=False, server_default=text("''::text"))  # 应用描述
    graph = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 运行时配置
    draft_graph = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 草稿图配置
    is_debug_passed = Column(Boolean, nullable=False, server_default=text("false"))  # 是否调试通过
    status = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 工作流状态
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WorkflowResult(Base, SerializableMixin):
    """工作流存储结果模型"""
    __tablename__ = "workflow_result"

    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(100), nullable=True)  # 工作流调用的应用id，如果为空则代表非应用调用
    account_id = Column(String(100), nullable=False)  # 创建账号id
    workflow_id = Column(String(100), nullable=False)  # 结果关联的工作流id
    graph = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 运行时配置
    state = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 工作流最终状态
    latency = Column(Float, nullable=False, server_default=text("0.0"))  # 消息的总耗时
    status = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 运行状态
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ApiToolProvider(Base, SerializableMixin):
    """API工具提供者模型"""
    __tablename__ = "api_tool_provider"

    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))
    icon = Column(String(255), nullable=False, server_default=text("''::character varying"))
    description = Column(Text, nullable=False, server_default=text("''::text"))
    openapi_schema = Column(Text, nullable=False, server_default=text("''::text"))
    headers = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ApiTool(Base, SerializableMixin):
    """API工具表"""
    __tablename__ = "api_tool"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(100), nullable=False)
    provider_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))
    description = Column(Text, nullable=False, server_default=text("''::text"))
    url = Column(String(255), nullable=False, server_default=text("''::character varying"))
    method = Column(String(255), nullable=False, server_default=text("''::character varying"))
    parameters = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Conversation(Base, SerializableMixin):
    """交流会话模型"""
    __tablename__ = "conversation"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(100), nullable=False)  # 关联应用id
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 会话名称
    summary = Column(Text, nullable=False, server_default=text("''::text"))  # 会话摘要/长期记忆
    is_pinned = Column(Boolean, nullable=False, server_default=text("false"))  # 是否置顶
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))  # 是否删除
    invoke_from = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 调用来源
    created_by = Column(
        String(100),
        nullable=True,
    )  # 会话创建者，会随着invoke_from的差异记录不同的信息，其中web_app和debugger会记录账号id、service_api会记录终端用户id
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Message(Base, SerializableMixin):
    """交流消息模型"""
    __tablename__ = "message"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 消息关联的记录
    app_id = Column(String(100), nullable=False)  # 关联应用id
    conversation_id = Column(String(100), nullable=False)  # 关联会话id
    invoke_from = Column(
        String(255),
        nullable=False,
        server_default=text("''::character varying"),
    )  # 调用来源，涵盖service_api、web_app、debugger等
    created_by = Column(String(100), nullable=False)  # 消息的创建来源，有可能是LLMOps的用户，也有可能是开放API的终端用户

    # 消息关联的原始问题
    query = Column(Text, nullable=False, server_default=text("''::text"))  # 用户提问的原始query
    image_urls = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 用户提问的图片URL列表信息
    message = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 产生answer的消息列表
    message_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 消息列表的token总数
    message_unit_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 消息的单价
    message_price_unit = Column(Numeric(10, 4), nullable=False, server_default=text("0.0"))  # 消息的价格单位

    # 消息关联的答案信息
    answer = Column(Text, nullable=False, server_default=text("''::text"))  # Agent生成的消息答案
    answer_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 消息答案的token数
    answer_unit_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # token的单位价格
    answer_price_unit = Column(Numeric(10, 4), nullable=False, server_default=text("0.0"))  # token的价格单位

    # 消息的相关统计信息
    latency = Column(Float, nullable=False, server_default=text("0.0"))  # 消息的总耗时
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))  # 软删除标记
    status = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 消息的状态，涵盖正常、错误、停止
    error = Column(Text, nullable=False, server_default=text("''::text"))  # 发生错误时记录的信息
    total_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 消耗的总token数，计算步骤的消耗
    total_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 消耗的总价格，计算步骤的总消耗

    # 消息时间相关信息
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MessageAgentThought(Base, SerializableMixin):
    """智能体消息推理模型，用于记录Agent生成最终消息答案时"""
    __tablename__ = "message_agent_thought"

    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 推理步骤关联信息
    app_id = Column(String(100), nullable=False)  # 关联的应用id
    conversation_id = Column(String(100), nullable=False)  # 关联的会话id
    message_id = Column(String(100), nullable=False)  # 关联的消息id
    invoke_from = Column(
        String(255),
        nullable=False,
        server_default=text("''::character varying"),
    )  # 调用来源，涵盖service_api、web_app、debugger等
    created_by = Column(String(100), nullable=False)  # 消息的创建来源，有可能是LLMOps的用户，也有可能是开放API的终端用户

    # 该步骤在消息中执行的位置
    position = Column(Integer, nullable=False, server_default=text("0"))  # 推理观察的位置

    # 推理与观察，分别记录LLM和非LLM产生的消息
    event = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 事件名称
    thought = Column(Text, nullable=False, server_default=text("''::text"))  # 推理内容(存储LLM生成的内容)
    observation = Column(Text, nullable=False, server_default=text("''::text"))  # 观察内容(存储知识库、工具等非LLM生成的内容，用于让LLM观察)

    # 工具相关，涵盖工具名称、输入，在调用工具时会生成
    tool = Column(Text, nullable=False, server_default=text("''::text"))  # 调用工具名称
    tool_input = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # LLM调用工具的输入，如果没有则为空字典

    # Agent推理观察步骤使用的消息列表(传递prompt消息内容)
    message = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 该步骤调用LLM使用的提示消息
    message_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 消息花费的token数
    message_unit_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 单价，所有LLM的计算方式统一为CNY
    message_price_unit = Column(
        Numeric(10, 4),
        nullable=False,
        server_default=text("0"),
    )  # 价格单位，值为1000代表1000token对应的单价

    # LLM生成内容相关(生成内容)
    answer = Column(Text, nullable=False, server_default=text("''::text"))  # LLM生成的答案内容，值和thought保持一致
    answer_token_count = Column(Integer, nullable=False, server_default=text("0"))  # LLM生成答案消耗token数
    answer_unit_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 单价，所有LLM的计算方式统一为CNY
    answer_price_unit = Column(
        Numeric(10, 4),
        nullable=False,
        server_default=text("0.0"),
    )  # 价格单位，值为1000代表1000token对应的单价

    # Agent推理观察统计相关
    total_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 总消耗token
    total_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 总消耗
    latency = Column(Float, nullable=False, server_default=text("0.0"))  # 推理观察步骤耗时

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
