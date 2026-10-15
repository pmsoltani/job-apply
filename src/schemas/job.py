import re

from pydantic import Field, field_validator

from src.configs import JobType
from src.schemas.common import CommonModel, RecordId
from src.schemas.company import Company
from src.schemas.contact import Contact


# Inline code spans on a single line, one or two backticks.
_CODE_SPAN = re.compile(r"`{1,2}([^`\n]+?)`{1,2}")


_DESC_ID = "Airtable record ID"
_DESC_MODEL = "Optional override for the configured LLM model"
_DESC_TITLE = "Contact's title, inferred from first name if not provided"

_DESC_JOB_FITNESS = "Optional score of how well the candidate fits the job, 1-5"
_DESC_JOB_REASONING = "Explanation for the job fitness score"


class GeneratedContent(CommonModel):
    job_fitness: int | None = Field(
        None, description=_DESC_JOB_FITNESS, ge=1, le=5, alias="Fitness"
    )
    job_fitness_reasoning: str | None = Field(
        None, description=_DESC_JOB_REASONING, alias="Reasoning"
    )
    cv_content: str | None = Field(None, alias="CV Content")
    letter_content: str | None = Field(None, alias="Letter Content")

    @field_validator("cover_letter_body", mode="after", check_fields=False)
    @classmethod
    def italicize_code_spans(cls, v: str) -> str:
        """Turn inline code spans into italics in the cover letter."""
        return _CODE_SPAN.sub(r"_\1_", v)

    @field_validator("profile_intro", mode="after", check_fields=False)
    @classmethod
    def strip_code_spans(cls, v: str) -> str:
        """Drop inline code spans: the CV intro is specified as plain text."""
        return _CODE_SPAN.sub(r"\1", v)


class JobBase(CommonModel):
    job: str = Field(..., alias="Job")
    ref: str | None = Field(None, alias="Ref")
    company: Company
    url: str | None = Field(None, alias="URL")
    type: JobType | None = Field(None, alias="Type")
    address: str | None = Field(None, alias="Address")
    notes: str | None = Field(None, alias="Notes")
    contact: Contact | None = None
    llm: str | None = Field(None, alias="LLM Notes")
    prompt: str | None = Field(None, alias="Prompt")


class PartialJob(CommonModel):
    id: RecordId
    job: str | None = Field(None, alias="Job")
    url: str | None = Field(None, alias="URL")
    notes: str | None = Field(None, alias="Notes")


class Job(GeneratedContent, JobBase):
    id: RecordId
