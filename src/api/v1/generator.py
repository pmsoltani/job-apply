from fastapi import APIRouter, BackgroundTasks

from src.api.v1.dependencies import AirtableDep, GeneratorDep
from src.pipelines import run_generate
from src.schemas import RecordId, WebhookPayload


router = APIRouter()


@router.post("", status_code=202)
async def generate(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    generator: GeneratorDep,
) -> dict[str, str]:
    background_tasks.add_task(
        run_generate, payload.record_id, airtable, generator, payload.model
    )
    return {"status": "accepted", "record_id": payload.record_id}


@router.get("", status_code=202)
async def generate_get(
    record_id: RecordId,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    generator: GeneratorDep,
    model: str | None = None,
) -> dict[str, str]:
    return await generate(
        WebhookPayload(record_id=record_id, model=model),
        background_tasks,
        airtable,
        generator,
    )
