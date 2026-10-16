from fastapi import APIRouter

from src import tasks
from src.api.v1.compiler import router as compiler_router
from src.api.v1.dependencies import LLMDep
from src.api.v1.generator import router as generator_router
from src.api.v1.parser import router as parser_router
from src.configs import c
from src.schemas import ModelCheckResponse, ModelsResponse, TasksResponse, TaskStatus


router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    return {
        "name": c.APP_NAME,
        "description": c.APP_DESCRIPTION,
        "version": c.APP_VERSION,
        "docs": "/docs",
    }


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/models", response_model=list[ModelsResponse])
async def show_model() -> list[ModelsResponse]:
    return [
        ModelsResponse(label=label, provider=c.LLM_PROVIDER, model=model)
        for label, model in c.LLM_ALL_MODELS.items()
    ]


@router.get("/models/check", response_model=list[ModelCheckResponse])
async def check_models(llm: LLMDep) -> list[ModelCheckResponse]:
    """Round-trip a tiny prompt to check if the LLM is configured correctly."""
    return await llm.check()


@router.get("/tasks", response_model=TasksResponse)
async def list_tasks() -> TasksResponse:
    active = tasks.snapshot()
    return TasksResponse(
        running=bool(active),
        count=len(active),
        tasks={k: TaskStatus(**v) for k, v in active.items()},
    )


router.include_router(parser_router, prefix="/parse", tags=["parser"])
router.include_router(generator_router, prefix="/generate", tags=["generator"])
router.include_router(compiler_router, prefix="/compile", tags=["compiler"])


__all__ = [
    "router",
]
