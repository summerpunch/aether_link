from pydantic import Field
from src.engine.workflow.node_entity import BaseNodeData
from src.engine.workflow.variable_entity import VariableEntity


class EndNodeData(BaseNodeData):
    """结束节点数据"""
    outputs: list[VariableEntity] = Field(default_factory=list)
