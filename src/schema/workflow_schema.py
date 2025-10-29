from typing import Optional, Any
from pydantic import BaseModel, Field, constr, HttpUrl, validator

WORKFLOW_CONFIG_NAME_PATTERN = r'^[A-Za-z_][A-Za-z0-9_]*$'


class AllRequest(BaseModel):
    """标签请求 - 接受任意JSON结构"""

    class Config:
        extra = "allow"  # 允许额外字段

    def __init__(self, **data):
        super().__init__(**data)

    def dict(self, **kwargs):
        """返回字典格式，包含所有字段"""
        return super().dict(**kwargs)


class CreateWorkflowReq(BaseModel):
    name: Optional[str] = Field(default="")
    tool_call_name: Optional[str] = Field(default="")
    description: Optional[str] = Field(default="")


class DraftGraphReq(BaseModel):
    workflow_id: Optional[str] = Field(default="")
    edges: Optional[list[dict[Any, Any]]] = Field(default_factory=list)
    nodes: Optional[list[dict[Any, Any]]] = Field(default_factory=list)

#
# class UpdateWorkflowReq(BaseModel):
#     name: constr(strip_whitespace=True, max_length=50)
#     tool_call_name: constr(strip_whitespace=True, max_length=50, regex=WORKFLOW_CONFIG_NAME_PATTERN)
#     icon: HttpUrl
#     description: constr(strip_whitespace=True, max_length=1024)
#
#
# class GetWorkflowsWithPageReq(PaginatorReq):
#     status: Optional[str] = Field(default="")
#     search_word: Optional[str] = Field(default="")
#
#     @validator("status")
#     def validate_status(cls, v):
#         if v and v not in WorkflowStatus.__members__.values():
#             raise ValueError("工作流状态格式错误")
#         return v
#
#
# class GetWorkflowResp(BaseModel):
#     id: UUID
#     name: str
#     tool_call_name: str
#     icon: str
#     description: str
#     status: str
#     is_debug_passed: bool = False
#     node_count: int = 0
#     published_at: int = 0
#     updated_at: int = 0
#     created_at: int = 0
#
#     @classmethod
#     def from_orm_model(cls, data: Workflow, use_draft_graph: bool = True):
#         graph = data.draft_graph if use_draft_graph else data.graph
#         return cls(
#             id=data.id,
#             name=data.name,
#             tool_call_name=data.tool_call_name,
#             icon=data.icon,
#             description=data.description,
#             status=data.status,
#             is_debug_passed=data.is_debug_passed,
#             node_count=len(graph.get("nodes", [])),
#             published_at=datetime_to_timestamp(data.published_at),
#             updated_at=datetime_to_timestamp(data.updated_at),
#             created_at=datetime_to_timestamp(data.created_at),
#         )
