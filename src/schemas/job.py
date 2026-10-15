import re

from pydantic import Field, field_validator

from src.configs import JobType
from src.schemas.common import CommonModel, RecordId
from src.schemas.company import Company, CompanyBase
from src.schemas.contact import Contact, ContactBase


# Inline code spans on a single line, one or two backticks.
_CODE_SPAN = re.compile(r"`{1,2}([^`\n]+?)`{1,2}")


_DESC_JOB_FITNESS = "Optional score of how well the candidate fits the job, 1-5"
_DESC_JOB_REASONING = "Explanation for the job fitness score"


class GeneratedContent(CommonModel):
    fitness: int | None = Field(
        None, description=_DESC_JOB_FITNESS, ge=1, le=5, alias="Fitness"
    )
    reasoning: str | None = Field(
        None, description=_DESC_JOB_REASONING, alias="Reasoning"
    )
    cv_content: str | None = Field(None, alias="CV Content")
    letter_content: str | None = Field(None, alias="Letter Content")

    @field_validator("letter_content", mode="after")
    @classmethod
    def italicize_code_spans(cls, v: str | None) -> str | None:
        """Turn inline code spans into italics in the cover letter."""
        if v is None:
            return v
        return _CODE_SPAN.sub(r"_\1_", v)

    @field_validator("cv_content", mode="after")
    @classmethod
    def strip_code_spans(cls, v: str | None) -> str | None:
        """Drop inline code spans: the CV intro is specified as plain text."""
        if v is None:
            return v
        return _CODE_SPAN.sub(r"\1", v)


class JobBase(CommonModel):
    title: str = Field(..., alias="Job")
    ref: str | None = Field(None, alias="Ref")
    company: CompanyBase
    type: JobType | None = Field(None, alias="Type")
    notes: str | None = Field(None, alias="Notes")
    contact: ContactBase | None = None


class PartialJob(CommonModel):
    id: RecordId
    title: str | None = Field(None, alias="Job")
    url: str | None = Field(None, alias="URL")
    notes: str | None = Field(None, alias="Notes")


class Job(GeneratedContent, JobBase):
    id: RecordId
    url: str | None = Field(None, alias="URL")
    company: Company
    address: str | None = Field(None, alias="Address")
    contact: Contact | None = None
    llm: str | None = Field(None, alias="LLM Notes")
    prompt: str | None = Field(None, alias="Prompt")
