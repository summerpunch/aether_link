from pydantic import Field
from src.engine.workflow.node_entity import BaseNodeData
from src.engine.workflow.variable_entity import VariableEntity


class StartNodeData(BaseNodeData):
    """开始节点数据"""
    inputs: list[VariableEntity] = Field(default_factory=list)
