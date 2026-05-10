from fastapi import APIRouter, BackgroundTasks

from src.api.v1.dependencies import AirtableDep, TypstDep
from src.configs import CVStyle
from src.pipelines import run_compile
from src.schemas import WebhookPayload


router = APIRouter()


@router.post("", status_code=202)
async def compile_docs(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    typst: TypstDep,
    cv_style: CVStyle = CVStyle.MODERN,
) -> dict:
    background_tasks.add_task(run_compile, payload.record_id, airtable, typst, cv_style)
    return {"status": "accepted", "record_id": payload.record_id}


@router.get("", status_code=202)
async def compile_docs_get(
    record_id: str,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    typst: TypstDep,
    cv_style: CVStyle = CVStyle.MODERN,
) -> dict:
    return await compile_docs(
        WebhookPayload(record_id=record_id), background_tasks, airtable, typst, cv_style
    )
