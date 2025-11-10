from enum import Enum


class WorkflowStatus(str, Enum):
    """工作流状态类型枚举"""
    DRAFT = "draft"
    PUBLISHED = "published"


class WorkflowResultStatus(str, Enum):
    """工作流运行结果状态"""
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


# 工作流默认配置信息，默认添加一个空的工作流
DEFAULT_WORKFLOW_CONFIG = {
    "graph": {},
    "draft_graph": {
        "nodes": [],
        "edges": []
    },
}


class MessageStatus(str, Enum):
    """会话状态"""
    NORMAL = "normal"  # 正常
    STOP = "stop"  # 停止
    TIMEOUT = "timeout"  # 超时
    ERROR = "error"  # 出错


class NodeType(str, Enum):
    """节点"""
    START = "start"
    LLM = "llm"
    TOOL = "tool"
    CODE = "code"
    DATASET_RETRIEVAL = "dataset_retrieval"
    HTTP_REQUEST = "http_request"
    TEMPLATE_TRANSFORM = "template_transform"
    END = "end"


class VariableType(str, Enum):
    """变量的类型枚举"""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOLEAN = "boolean"


class VariableValueType(str, Enum):
    """变量内置值类型枚举"""
    REF = "ref"  # 引用类型
    LITERAL = "literal"  # 字面数据/直接输入
    GENERATED = "generated"  # 生成的值，一般用在开始节点或者output中


class NodeStatus(str, Enum):
    """节点状态"""
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"



class MessageType(Enum):
    AI = "ai"

    USER = "user"
