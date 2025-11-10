from dotenv import load_dotenv
import logging
from fastapi import APIRouter

from src.core.di_config import injector
from src.core.response import ApiResult
from src.schema.conversation_schema import ConversationReq, AgentRunReq
from src.service.conversation_service import ConversationService
from src.core import auth_context

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["CONVERSATION"])


@router.post("/create", summary="创建会话")
async def create(req: ConversationReq):
    conversation = await injector.get(ConversationService).create_conversation(app_id=req.app_id,
                                                                               account=auth_context.get_current_user_id())
    return ApiResult.success({"thread_id": conversation})


@router.post("/create/agent_run_id", summary="创建agent_run_id")
async def create(req: AgentRunReq):
    agent_run = await injector.get(ConversationService).create_agent_run_id(thread_id=req.thread_id,
                                                                            account=auth_context.get_current_user_id())
    return ApiResult.success({"agent_run_id": agent_run})
