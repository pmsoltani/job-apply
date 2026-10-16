from pydantic import BaseModel, Field

from src.schemas.common import RecordId


_DESC_MODEL = "Optional override for the configured LLM model"
_DESC_QUESTION = "The application form's question, including any length limit"
_DESC_QUESTION_RECORD_ID = "Job to tailor the answer to, if any"
_DESC_ANSWER = "The generated answer to the question"


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


class QuestionPayload(BaseModel):
    question: str = Field(..., min_length=10, description=_DESC_QUESTION)
    record_id: RecordId | None = Field(None, description=_DESC_QUESTION_RECORD_ID)


class QuestionResponse(QuestionPayload):
    answer: str = Field(..., description=_DESC_ANSWER)
