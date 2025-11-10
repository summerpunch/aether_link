import logging
from fastapi import APIRouter
from src.core import auth_context
from src.core.response import ApiResult
from src.core.di_config import injector
from src.schema.workflow_schema import CreateWorkflowReq, DraftGraphReq, DebugWorkflowReq
from src.service.workflow_service import WorkflowService
from sse_starlette.sse import EventSourceResponse

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["WORKFLOWS"])


@router.post("/debug", summary="调试工作流")
async def debug(req: DebugWorkflowReq):
    async def event_generator():
        async for event_data in injector.get(WorkflowService).debug(
                workflow_id=req.workflow_id,
                inputs={
                    "query": req.query
                },
                account=auth_context.get_current_user_id()
        ):
            yield event_data

    return EventSourceResponse(event_generator(),
                               media_type="text/event-stream",
                               sep="\n")


@router.post("/create", summary="创建工作流")
async def create(req: CreateWorkflowReq):
    workflow = injector.get(WorkflowService).create_workflow(req, auth_context.get_current_user_id())
    return ApiResult.success({"workflow_id": workflow.id})


@router.post("/draft_graph", summary="更新工作流配置")
async def draft_graph(req: DraftGraphReq):
    injector.get(WorkflowService).update_draft_graph(req.workflow_id, {
        "nodes": req.nodes or [],
        "edges": req.edges or [],
    }, auth_context.get_current_user_id())
    return ApiResult.success("更新工作流草稿配置成功")


@router.get("/{workflow_id}/draft_graph", summary="获取工作流配置")
async def draft_graph(workflow_id: str):
    resp = injector.get(WorkflowService).get_draft_graph(workflow_id,
                                                         auth_context.get_current_user_id())
    return ApiResult.success(resp)


@router.delete("/{workflow_id}", summary="删除工作流")
async def draft_graph(workflow_id: str):
    deleted = injector.get(WorkflowService).delete(workflow_id, auth_context.get_current_user_id())
    if deleted:
        return ApiResult.success("工作流删除成功")
    return ApiResult.success("工作流删除失败")
