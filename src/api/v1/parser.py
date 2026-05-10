import logging

from fastapi import APIRouter, BackgroundTasks

from src.api.v1.dependencies import AirtableDep, ParserDep
from src.pipelines import run_parse
from src.schemas import WebhookPayload


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", status_code=202)
async def parse(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    parser: ParserDep,
) -> dict:
    background_tasks.add_task(
        run_parse, payload.record_id, airtable, parser, payload.model
    )
    return {"status": "accepted", "record_id": payload.record_id}


@router.get("", status_code=202)
async def parse_get(
    record_id: str,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    parser: ParserDep,
    model: str | None = None,
) -> dict:
    return await parse(
        WebhookPayload(record_id=record_id, model=model),
        background_tasks,
        airtable,
        parser,
    )
