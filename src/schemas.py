from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.configs import c


_DESC_COUNTRY = "ISO 3166-1 alpha-2 country code"
_DESC_MODEL = "Optional override for the configured LLM model"
_DESC_TITLE = "Contact's title, inferred from first name if not provided"


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
    def normalize_country_codes(cls, v) -> str | None:
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


class GeneratedContent(BaseModel):
    cover_letter_body: str
    profile_intro: str


class ModelsResponse(BaseModel):
    provider: str
    model: str


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
