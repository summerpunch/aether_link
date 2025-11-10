from pydantic import BaseModel, Field


class ConversationReq(BaseModel):
    app_id: str = Field(..., description="app_id")


class AgentRunReq(BaseModel):
    thread_id: str = Field(default=None, description="thread_id")
