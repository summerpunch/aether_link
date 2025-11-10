from dotenv import load_dotenv
import logging

from fastapi import APIRouter
from src.core.di_config import injector
from src.core.response import ApiResult
from src.schema.tool_schema import CreateApiToolReq
from src.service.tool_service import ToolService

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["TOOLS"])


@router.get("/builtin", summary="内置工具")
async def builtin():
    response = await injector.get(ToolService).get_builtin_tools()
    return ApiResult.success(response)


@router.post("/api_tools", summary="自定义工具")
async def api_tools(req: CreateApiToolReq):
    await injector.get(ToolService).create_api_tool(req, "system")
    return ApiResult.success("创建自定义API插件成功")
