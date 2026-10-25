from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.schemas.common import RecordId


_DESC_MODEL = "Optional override for the configured LLM model"


class TaskStatus(BaseModel):
    description: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TasksResponse(BaseModel):
    running: bool
    count: int
    tasks: dict[str, TaskStatus]


class WebhookPayload(BaseModel):
    record_id: RecordId
    model: str | None = Field(None, description=_DESC_MODEL)
