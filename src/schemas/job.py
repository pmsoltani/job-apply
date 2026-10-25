import datetime as dt
import re
from typing import Any

from pydantic import Field, field_validator

from src.configs import JobType
from src.schemas.common import CommonModel, RecordId, StrippedStr
from src.schemas.company import Company, CompanyBase
from src.schemas.contact import Contact, ContactBase


# Inline code spans on a single line, one or two backticks.
_CODE_SPAN = re.compile(r"`{1,2}([^`\n]+?)`{1,2}")


_DESC_FITNESS = (
    "How well the applicant fits the role, based on the CV and the job posting: "
    "1 poor, 2 fair, 3 good, 4 very good, 5 excellent fit. Null if it cannot be "
    "determined."
)
_DESC_REASONING = (
    "Explanation for the fitness score, as bullet points (at most 4). Null if the "
    "fitness cannot be determined."
)
_DESC_CV_CONTENT = (
    "A tailored 2-3 sentence CV profile paragraph. Plain text (no markdown), third "
    "person. It replaces the default intro on the CV for this application only."
)
_DESC_LETTER_CONTENT = (
    "A tailored cover letter body in CommonMark markdown. No greeting (Dear ...) or "
    "sign-off: the template adds those."
)

_DESC_TITLE = (
    "The **exact** job title as stated in the posting: the title only, not the "
    "description."
)
_DESC_REF = "The job reference number or ID, only if explicitly stated in the posting."
_DESC_TYPE = "The job type, only if explicitly stated in the posting."
_DESC_NOTES = (
    "The job posting body, copied **verbatim**: do NOT summarise, paraphrase, or "
    "condense anything. Only strip navigation menus, cookie notices, image captions, "
    "and other page boilerplate that is not part of the job posting itself. All "
    "substantive content (responsibilities, requirements, qualifications, benefits) "
    "must be reproduced exactly as stated in the posting. Leave out the section that "
    "describes the company as it belongs in the company's notes, not here."
)
_DESC_CONTACT = "The hiring contact, only if explicitly stated in the posting."
_DESC_DATE = "The date the application was submitted."


class GeneratedContent(CommonModel):
    fitness: int | None = Field(
        None, description=_DESC_FITNESS, ge=1, le=5, alias="Fitness"
    )
    reasoning: StrippedStr | None = Field(
        None, description=_DESC_REASONING, alias="Reasoning"
    )
    cv_content: StrippedStr | None = Field(
        None, description=_DESC_CV_CONTENT, alias="CV Content"
    )
    letter_content: StrippedStr | None = Field(
        None, description=_DESC_LETTER_CONTENT, alias="Letter Content"
    )

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
    title: str = Field(..., alias="Job", description=_DESC_TITLE)
    ref: str | None = Field(None, alias="Ref", description=_DESC_REF)
    company: CompanyBase
    type: JobType | None = Field(None, alias="Type", description=_DESC_TYPE)
    notes: str | None = Field(None, alias="Notes", description=_DESC_NOTES)
    contact: ContactBase | None = Field(None, description=_DESC_CONTACT)

    @property
    def subject(self) -> str:
        """The subject line for the cover letter."""
        ref = f" ({self.ref})" if self.ref else ""
        return self.title + ref


class PartialJob(CommonModel):
    id: RecordId
    title: str | None = Field(None, alias="Job")
    url: str | None = Field(None, alias="URL")
    notes: str | None = Field(None, alias="Notes")


class JobLinks(CommonModel):
    """A job's linked-record fields, as Airtable returns them: lists of record IDs."""

    company_ids: list[RecordId] = Field(default_factory=list, alias="Company")
    contact_ids: list[RecordId] = Field(default_factory=list, alias="Recipient")


class Job(GeneratedContent, JobBase, JobLinks):
    id: RecordId
    url: str | None = Field(None, alias="URL")
    company: Company
    address: str | None = Field(None, alias="Address")
    notes: str = Field(..., alias="Notes")
    contact: Contact | None = None
    llm: str | None = Field(None, alias="LLM Notes")
    docs: list[dict[str, Any]] = Field(default_factory=list, alias="Docs")
    date: dt.date | None = Field(None, alias="Date", description=_DESC_DATE)

    def make_prompt(self) -> str:
        """A prompt that can be used to regenerate the job application content."""
        company = self.company.name
        parts = [
            f"# Title: {self.title}",
            f"**Company:** {company}",
            f"**USER INSTRUCTIONS:** {self.llm}" if self.llm else "",
            f"## Description\n\n{self.notes}",
            f"## About {company}\n\n{self.company.notes}" if self.company.notes else "",
        ]
        posting = "\n\n".join(p.strip() for p in parts if p.strip())
        return f"<job_posting>\n{posting}\n</job_posting>"


class AppliedJob(Job):
    """A job that has been applied to, with the application date."""

    date: dt.date = Field(..., alias="Date", description=_DESC_DATE)
