import logging

import uvicorn
from fastapi import BackgroundTasks, FastAPI

from src import tasks
from src.api.dependencies import AirtableDep, GeneratorDep, ParserDep, TypstDep
from src.configs import CVStyle, c
from src.pipelines import run_compile, run_generate, run_parse
from src.schemas import ModelsResponse, TasksResponse, TaskStatus, WebhookPayload


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="job-apply")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/model", response_model=ModelsResponse)
async def show_model() -> ModelsResponse:
    return ModelsResponse(provider=c.LLM_PROVIDER, model=c.LLM_MODEL)


@app.get("/tasks", response_model=TasksResponse)
async def list_tasks() -> TasksResponse:
    active = tasks.snapshot()
    return TasksResponse(
        running=bool(active),
        count=len(active),
        tasks={k: TaskStatus(**v) for k, v in active.items()},
    )


@app.post("/parse", status_code=202)
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


@app.get("/parse", status_code=202)
async def parse_get(
    record_id: str,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    parser: ParserDep,
    model: str | None = None,
) -> dict:
    return await parse(WebhookPayload(record_id=record_id, model=model), background_tasks, airtable, parser)


@app.post("/generate", status_code=202)
async def generate(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    generator: GeneratorDep,
) -> dict:
    background_tasks.add_task(
        run_generate, payload.record_id, airtable, generator, payload.model
    )
    return {"status": "accepted", "record_id": payload.record_id}


@app.get("/generate", status_code=202)
async def generate_get(
    record_id: str,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    generator: GeneratorDep,
    model: str | None = None,
) -> dict:
    return await generate(WebhookPayload(record_id=record_id, model=model), background_tasks, airtable, generator)


@app.post("/compile", status_code=202)
async def compile_docs(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    typst: TypstDep,
    cv_style: CVStyle = CVStyle.MODERN,
) -> dict:
    background_tasks.add_task(run_compile, payload.record_id, airtable, typst, cv_style)
    return {"status": "accepted", "record_id": payload.record_id}


@app.get("/compile", status_code=202)
async def compile_docs_get(
    record_id: str,
    background_tasks: BackgroundTasks,
    airtable: AirtableDep,
    typst: TypstDep,
    cv_style: CVStyle = CVStyle.MODERN,
) -> dict:
    return await compile_docs(WebhookPayload(record_id=record_id), background_tasks, airtable, typst, cv_style)


def main() -> None:
    uvicorn.run(
        "src.api.server:app", host=c.FASTAPI_HOST, port=c.FASTAPI_PORT, reload=True
    )
