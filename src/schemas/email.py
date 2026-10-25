from pydantic import BaseModel, Field

from src.schemas.common import CommonModel, RecordId, StrippedStr


_DESC_SUBJECT = "The email subject line."
_DESC_BODY = "The email body, in plain text."
_DESC_PROMPT = "Optional prompt to customize the email."
_DESC_RECORD_ID = "Job to tailor the email to."


class EmailBase(CommonModel):
    """Job application reminder email."""

    body: StrippedStr = Field(..., description=_DESC_BODY)


class Email(EmailBase):
    to_name: str | None = None
    to_address: str | None = None
    subject: str = Field(..., description=_DESC_SUBJECT)


class EmailPayload(BaseModel):
    prompt: StrippedStr = Field("", description=_DESC_PROMPT)
    record_id: RecordId = Field(..., description=_DESC_RECORD_ID)
