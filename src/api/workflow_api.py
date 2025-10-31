import logging
from fastapi import APIRouter

from src.core.response import ApiResult
from src.service import workflow_service
from src.core.di_config import injector
from src.schema.workflow_schema import CreateWorkflowReq, DraftGraphReq, AllRequest
from src.service.workflow_service import WorkflowService
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/create")
async def create(req: CreateWorkflowReq):
    workflow = await injector.get(WorkflowService).create_workflow(req, "system")
    return await ApiResult.success({"workflow_id": workflow.id})


@router.post("/draft_graph")
async def draft_graph(req: DraftGraphReq):
    """根据传递的工作流id+请求信息更新工作流草稿图配置"""
    injector.get(WorkflowService).update_draft_graph(req.workflow_id, {
        "nodes": req.nodes or [],
        "edges": req.edges or [],
    }, "system")
    return await ApiResult.success("更新工作流草稿配置成功")


@router.get("/{workflow_id}/draft_graph")
async def draft_graph(workflow_id: str):
    return await ApiResult.success(workflow_service.get_draft_graph(workflow_id, "system"))


from sse_starlette.sse import EventSourceResponse


@router.post("/{workflow_id}/debug")
async def debug(workflow_id: str, req: AllRequest):
    async def event_generator():
        async for event_data in injector.get(WorkflowService).debug_workflow(
                workflow_id, req.dict(), "system"):
            yield event_data

    return EventSourceResponse(event_generator(),
                               media_type="text/event-stream",
                               sep="\n")


@router.post("/update")
async def update():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "aether link api"
    }


@router.get("/get")
async def get():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "aether link api"
    }


@router.post("/with_page")
async def with_page():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "aether link api"
    }


@router.post("/update_draft_graph")
async def update_draft_graph():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "aether link api"
    }


@router.get("/get_draft_graph")
async def get_draft_graph():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "aether link api"
    }


#
#
# @router.post("/debug")
# async def debug():
#     return {
#         "status": "healthy",
#         "version": "0.1.0",
#         "service": "aether link api"
#     }


@router.post("/publish")
async def publish():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "aether link api"
    }


@router.post("/cancel_publish")
async def cancel_cancel():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "aether link api"
    }
