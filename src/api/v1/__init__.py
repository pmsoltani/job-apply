from fastapi import APIRouter

from src import tasks
from src.api.v1.compiler import router as compiler_router
from src.api.v1.generator import router as generator_router
from src.api.v1.parser import router as parser_router
from src.configs import c
from src.schemas import ModelsResponse, TasksResponse, TaskStatus


router = APIRouter()


@router.get("/")
async def root():
    return {
        "name": c.APP_NAME,
        "description": c.APP_DESCRIPTION,
        "version": c.APP_VERSION,
        "docs": "/docs",
    }


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/model", response_model=ModelsResponse)
async def show_model() -> ModelsResponse:
    return ModelsResponse(provider=c.LLM_PROVIDER, model=c.LLM_MODEL)


@router.get("/tasks", response_model=TasksResponse)
async def list_tasks() -> TasksResponse:
    active = tasks.snapshot()
    return TasksResponse(
        running=bool(active),
        count=len(active),
        tasks={k: TaskStatus(**v) for k, v in active.items()},
    )


router.include_router(parser_router, prefix="/parser", tags=["parser"])
router.include_router(generator_router, prefix="/generator", tags=["generator"])
router.include_router(compiler_router, prefix="/compiler", tags=["compiler"])


___all__ = [
    "router",
]
