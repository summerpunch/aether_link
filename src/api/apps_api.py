from dotenv import load_dotenv
import logging

from fastapi import APIRouter
from src.core.di_config import injector
from src.core.response import ApiResult
from src.schema.app_schema import CreateAppReq, AllRequest, ChatReq
from src.service.app_service import AppService
from src.service.app_config_service import AppConfigService

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apps", tags=["apps"])


@router.post("/chat")
async def chat(req: ChatReq):
    response = injector.get(AppService).chat(req, "system")
    return ApiResult.compact_generate_response(response)


@router.post("/create")
async def create(req: CreateAppReq):
    app = await injector.get(AppService).create_app(req, "system")
    return await ApiResult.success({"app_id": app.id})


@router.get("/{app_id}/draft_app_config")
async def get_draft_app_config(app_id: str):
    app = injector.get(AppConfigService).get_draft_app_config(app_id)
    return await ApiResult.success(app)


@router.post("/{app_id}/draft_app_config")
async def update_draft_app_config(app_id: str, req: AllRequest):
    await injector.get(AppService).update_draft_app_config(app_id, req.dict(), "system")
    return await ApiResult.success("更新应用草稿配置成功")
