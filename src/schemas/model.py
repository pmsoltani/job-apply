from pydantic import BaseModel, Field


_DESC_MODEL = "Optional override for the configured LLM model"

_DESC_MODEL_URL = "Base URL, or null for the provider default"
_DESC_MODEL_LATENCY_MS = "Round-trip time, if the call completed"
_DESC_MODEL_REPLY = "What the model actually said, when ok"
_DESC_MODEL_ERROR = "Failure detail, when not ok"
_DESC_MODEL_STATUS_CODE = "HTTP status, for provider-side failures"


class ModelsResponse(BaseModel):
    provider: str
    model: str


class ModelCheckResponse(BaseModel):
    """Result of a live round-trip against the configured LLM endpoint."""

    ok: bool
    provider: str
    model: str
    url: str | None = Field(None, description=_DESC_MODEL_URL)
    latency_ms: int | None = Field(None, description=_DESC_MODEL_LATENCY_MS)
    reply: str | None = Field(None, description=_DESC_MODEL_REPLY)
    error: str | None = Field(None, description=_DESC_MODEL_ERROR)
    status_code: int | None = Field(None, description=_DESC_MODEL_STATUS_CODE)
