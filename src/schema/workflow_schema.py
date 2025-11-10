from typing import Optional, Any
from pydantic import BaseModel, Field


class CreateWorkflowReq(BaseModel):
    name: Optional[str] = Field(default="")
    tool_call_name: Optional[str] = Field(default="")
    description: Optional[str] = Field(default="")


class DraftGraphReq(BaseModel):
    workflow_id: Optional[str] = Field(default="")
    edges: Optional[list[dict[Any, Any]]] = Field(default_factory=list)
    nodes: Optional[list[dict[Any, Any]]] = Field(default_factory=list)


class DebugWorkflowReq(BaseModel):
    workflow_id: Optional[str] = Field(default="")
    query: Optional[str] = Field(default="")
