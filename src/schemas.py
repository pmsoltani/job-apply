from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from src.configs import c


_DESC_COUNTRY = "ISO 3166-1 alpha-2 country code"


class WebhookPayload(BaseModel):
    record_id: str


class CompanyData(BaseModel):
    name: str
    url: HttpUrl | None = None
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$", description=_DESC_COUNTRY)


class ContactData(BaseModel):
    title: Literal["Mr", "Ms", "Dr", "Prof"] | None = None
    first: str | None = None
    last: str | None = None
    role: str | None = None
    email: str | None = None
    url: HttpUrl | None = None


class JobData(BaseModel):
    job: str
    notes: str
    company: CompanyData
    contact: ContactData | None = None


class GeneratedContent(BaseModel):
    cover_letter_body: str
    profile_intro: str


class LetterData(BaseModel):
    """Maps to letter/data.json consumed by the Typst cover letter template."""

    date: str = ""
    from_name: str = c.full_name
    from_address: str = c.address
    to: str = "Hiring Manager"
    to_address: str = ""
    subject: str = ""
    body: str = ""
    closing: str = "Sincerely,"

    def to_json_dict(self) -> dict:
        return {
            "date": self.date,
            "from": self.from_name,
            "from-address": self.from_address,
            "to": self.to,
            "to-address": self.to_address,
            "subject": self.subject,
            "body": self.body,
            "closing": self.closing,
        }
