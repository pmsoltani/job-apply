import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.configs import JobType, c


# Inline code spans on a single line, one or two backticks. Deliberately does not
# match fenced blocks, which have nothing after the opening backticks.
_CODE_SPAN = re.compile(r"`{1,2}([^`\n]+?)`{1,2}")


_DESC_COUNTRY = "ISO 3166-1 alpha-2 country code"
_DESC_MODEL = "Optional override for the configured LLM model"
_DESC_TITLE = "Contact's title, inferred from first name if not provided"

_DESC_MODEL_URL = "Base URL, or null for the provider default"
_DESC_MODEL_LATENCY_MS = "Round-trip time, if the call completed"
_DESC_MODEL_REPLY = "What the model actually said, when ok"
_DESC_MODEL_ERROR = "Failure detail, when not ok"
_DESC_MODEL_STATUS_CODE = "HTTP status, for provider-side failures"


class WebhookPayload(BaseModel):
    record_id: str
    model: str | None = Field(None, description=_DESC_MODEL)


class CompanyData(BaseModel):
    name: str
    url: str | None = None
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$", description=_DESC_COUNTRY)
    notes: str | None = None

    @field_validator("country", mode="after")
    @classmethod
    def normalize_country_codes(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return c.COUNTRY_CODE_MAPPING.get(v, v)


class ContactData(BaseModel):
    title: Literal["Mr", "Ms", "Dr"] | None = Field(None, description=_DESC_TITLE)
    first: str | None = None
    last: str | None = None
    role: str | None = None
    email: str | None = None
    url: str | None = None


class JobData(BaseModel):
    job: str
    notes: str
    company: CompanyData
    contact: ContactData | None = None
    type: JobType | None = None


class GeneratedContent(BaseModel):
    cover_letter_body: str
    profile_intro: str

    @field_validator("cover_letter_body", mode="after")
    @classmethod
    def italicize_code_spans(cls, v: str) -> str:
        """Turn inline code spans into italics in the cover letter."""
        return _CODE_SPAN.sub(r"_\1_", v)

    @field_validator("profile_intro", mode="after")
    @classmethod
    def strip_code_spans(cls, v: str) -> str:
        """Drop inline code spans: the CV intro is specified as plain text."""
        return _CODE_SPAN.sub(r"\1", v)


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


class TaskStatus(BaseModel):
    description: str
    started_at: str


class TasksResponse(BaseModel):
    running: bool
    count: int
    tasks: dict[str, TaskStatus]


class LetterData(BaseModel):
    """Maps to letter/data.json consumed by the Typst cover letter template."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = ""
    from_name: str = Field(c.full_name, alias="from")
    from_address: str = Field(c.address, alias="from-address")
    to_name: str = Field("Hiring Manager", alias="to")
    to_address: str = Field("", alias="to-address")
    subject: str = ""
    body: str = ""
    closing: str = "Sincerely,"
