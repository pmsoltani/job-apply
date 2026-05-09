import logging

import uvicorn
from fastapi import BackgroundTasks, FastAPI

from src.api.dependencies import AirtableDep, GeneratorDep, ParserDep, TypstDep
from src.configs import c
from src.pipelines import run_generate, run_ingest
from src.schemas import WebhookPayload


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="job-apply")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest", status_code=202)
async def ingest(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    parser: ParserDep,
) -> dict:
    background_tasks.add_task(run_ingest, payload.record_id, airtable, parser, payload.model)
    return {"status": "accepted", "record_id": payload.record_id}


@app.post("/generate", status_code=202)
async def generate(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    generator: GeneratorDep,
    typst: TypstDep,
) -> dict:
    background_tasks.add_task(
        run_generate, payload.record_id, airtable, generator, typst, payload.model
    )
    return {"status": "accepted", "record_id": payload.record_id}


def main() -> None:
    uvicorn.run("src.api.server:app", host=c.FASTAPI_HOST, port=c.FASTAPI_PORT, reload=True)
