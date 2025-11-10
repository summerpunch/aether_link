"""
数据库模型定义
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
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


class AppConfig(Base, SerializableMixin):
    """应用配置模型"""
    __tablename__ = "app_config"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(100), nullable=False)  # 关联应用id
    model_config = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 模型配置
    dialog_round = Column(Integer, nullable=False, server_default=text("0"))  # 上下文轮数
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
    dialog_round = Column(Integer, nullable=False, server_default=text("0"))  # 上下文轮数
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
    is_pinned = Column(Boolean, nullable=False, server_default=text("false"))  # 是否置顶
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))  # 是否删除
    invoke_from = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 调用来源
    created_by = Column(
        String(100),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AgentRun(Base, SerializableMixin):
    __tablename__ = "agent_runs"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False, server_default=text('false'))
    created_by = Column(
        String(100),
        nullable=True,
    )


class Message(Base, SerializableMixin):
    """交流消息模型"""
    __tablename__ = "messages"
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(100), nullable=False)
    conversation_id = Column(String(100), nullable=False)
    agent_run_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    message_type = Column(String(50), nullable=False)
    content = Column(JSONB, nullable=True)
