from contextlib import asynccontextmanager, AsyncExitStack
from dotenv import load_dotenv
from fastapi import FastAPI
from src.api.apps_api import router as apps_api
from src.api.tools_api import router as tools_api
from src.api.workflow_api import router as workflow_api
from fastapi.middleware.cors import CORSMiddleware
import logging
load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialization()
    async with AsyncExitStack() as stack:
        yield


app = FastAPI(
    title="Neuro Ma API",
    description="API for Neuro Ma LangGraph-based agent workflow",
    version="0.1.0",
    lifespan=lifespan
)


async def initialization():
    from src.store import database_manager
    _database_manager = database_manager.init_database_manager()
    _database_manager.create_tables()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(apps_api, prefix="/api")
app.include_router(tools_api, prefix="/api")
app.include_router(workflow_api, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "aether link api"
    }
