from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from src.configs import bc


class WebhookPayload(BaseModel):
    record_id: str


class CompanyData(BaseModel):
    name: str
    url: Optional[str] = None
    country: Optional[str] = None


class ContactData(BaseModel):
    title: Optional[str] = None  # Mr | Ms | Dr | Prof
    first: Optional[str] = None
    last: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None


class JobData(BaseModel):
    job_title: str
    job_description: str
    company: CompanyData
    contact: Optional[ContactData] = None


class GeneratedContent(BaseModel):
    cover_letter_body: str
    profile_intro: str


class LetterData(BaseModel):
    """Maps to letter/data.json consumed by the Typst cover letter template."""

    date: str = ""  # empty string → template uses today
    from_name: str = bc.full_name
    from_address: str = bc.address  # empty string → template uses a default address
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


class FieldType(StrEnum):
    """Airtable field types."""

    SINGLE_TEXT = "single_text"
    LONG_TEXT = "long_text"
    ATTACHMENT = "attachment"
    CHECKBOX = "checkbox"
    SINGLE_SELECT = "single_select"
    MULTIPLE_SELECT = "multiple_select"
    DATE = "date"
    PHONE = "phone"
    EMAIL = "email"
    URL = "url"
    NUMBER = "number"
    CURRENCY = "currency"
    FORMULA = "formula"
    LINKED = "linked"
    LOOKUP = "lookup"
    BUTTON = "button"


class Col(BaseModel):
    name: str
    type: FieldType
    note: str = ""


class Table(BaseModel):
    name: str
    fields: dict[str, Col]


_COMPANY = "Linked to Companies table"
_AD = "URL of job ad"
_STATUS = "Applied, Rejected, Interview, Accepted"
_DATE = "Date applied"
_RECIPIENT = "Link to Contacts, used in cover letter"
_LLM = "Special notes for LLM about job to aid in cover letter generation"
_CONTACT = "Formula: title + last"
_TITLE = "Mr, Ms, Dr"
_ADDRESS = "Address in separate lines used in cover letter"
_COUNTRY = "ISO-3166-1 alpha-2 country code"


class JobsTable(Table):
    name: str = "Jobs"
    fields: dict[str, Col] = Field(
        default_factory=lambda: {
            "job": Col(name="Job", type=FieldType.SINGLE_TEXT),
            "company": Col(name="Company", type=FieldType.LINKED, note=_COMPANY),
            "ad": Col(name="AD", type=FieldType.URL, note=_AD),
            "docs": Col(name="Docs", type=FieldType.ATTACHMENT),
            "notes": Col(name="Notes", type=FieldType.LONG_TEXT),
            "status": Col(name="Status", type=FieldType.SINGLE_SELECT, note=_STATUS),
            "apply": Col(name="Apply", type=FieldType.DATE, note=_DATE),
            "recipient": Col(name="Recipient", type=FieldType.LINKED, note=_RECIPIENT),
            "llm": Col(name="LLM Notes", type=FieldType.SINGLE_TEXT, note=_LLM),
            "prompt": Col(name="Prompt", type=FieldType.FORMULA),
        }
    )


class ContactsTable(Table):
    name: str = "Contacts"
    fields: dict[str, Col] = Field(
        default_factory=lambda: {
            "contact": Col(name="Contact", type=FieldType.FORMULA, note=_CONTACT),
            "title": Col(name="Title", type=FieldType.SINGLE_SELECT, note=_TITLE),
            "first": Col(name="First", type=FieldType.SINGLE_TEXT),
            "last": Col(name="Last", type=FieldType.SINGLE_TEXT),
            "role": Col(name="Role", type=FieldType.SINGLE_TEXT),
            "email": Col(name="Email", type=FieldType.EMAIL),
            "phone": Col(name="Phone", type=FieldType.PHONE),
            "url": Col(name="URL", type=FieldType.URL),
            "company": Col(name="Company", type=FieldType.LINKED, note=_COMPANY),
        }
    )


class CompanyTable(Table):
    name: str = "Companies"
    fields: dict[str, Col] = Field(
        default_factory=lambda: {
            "company": Col(name="Company", type=FieldType.SINGLE_TEXT),
            "url": Col(name="URL", type=FieldType.URL),
            "notes": Col(name="Notes", type=FieldType.LONG_TEXT),
            "address": Col(name="Address", type=FieldType.LONG_TEXT, note=_ADDRESS),
            "docs": Col(name="Docs", type=FieldType.ATTACHMENT),
            "country": Col(name="Country", type=FieldType.SINGLE_SELECT, note=_COUNTRY),
        }
    )
