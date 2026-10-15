from pydantic import BaseModel, Field

from src.schemas.common import RecordId


_DESC_MODEL = "Optional override for the configured LLM model"


class TaskStatus(BaseModel):
    description: str
    started_at: str


class TasksResponse(BaseModel):
    running: bool
    count: int
    tasks: dict[str, TaskStatus]


class WebhookPayload(BaseModel):
    record_id: RecordId
    model: str | None = Field(None, description=_DESC_MODEL)
