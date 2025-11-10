from dotenv import load_dotenv
import logging
from fastapi import APIRouter
from sse_starlette import EventSourceResponse
from src.core.di_config import injector
from src.core.response import ApiResult
from src.schema.app_schema import CreateAppReq, AllRequest, ChatReq, ChatStreamReq
from src.service.app_service import AppService
from src.service.app_config_service import AppConfigService
from src.core import auth_context

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apps", tags=["APP"])


@router.post("/chat", summary="聊天")
async def chat(req: ChatReq):
    response = await injector.get(AppService).chat(req,
                                                   auth_context.get_current_user_id())
    return ApiResult.success({"agent_run_id": response})


@router.get("/stream", summary="读取消息")
async def stream(req: ChatStreamReq):
    return EventSourceResponse(injector.get(AppService).stream(req=req),
                               media_type="text/event-stream",
                               sep="\n")


@router.post("/create", summary="创建APP应用")
async def create(req: CreateAppReq):
    app = await injector.get(AppService).create_app(req=req,
                                                    account=auth_context.get_current_user_id())
    return ApiResult.success({"app_id": app.id})


@router.get("/{app_id}/draft_app_config", summary="查询APP配置")
async def get_draft_app_config(app_id: str):
    app = injector.get(AppConfigService).get_draft_app_config(app_id)
    return ApiResult.success(app)


@router.post("/{app_id}/draft_app_config", summary="更新APP配置")
async def update_draft_app_config(app_id: str, req: AllRequest):
    await injector.get(AppService).update_draft_app_config(app_id,
                                                           req.dict(),
                                                           auth_context.get_current_user_id())
    return ApiResult.success("更新应用草稿配置成功")
