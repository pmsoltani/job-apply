import datetime as dt

from pydantic import Field, field_validator

from src.configs import c
from src.schemas.common import CommonModel


class Letter(CommonModel):
    """Maps to letter/data.json consumed by the Typst cover letter template."""

    date: dt.date | None = None
    from_name: str = Field(c.full_name, alias="from")
    from_address: str = Field(c.address, alias="from-address")
    to_name: str = Field(c.DEFAULT_RECIPIENT_NAME, alias="to")
    to_address: str = Field("", alias="to-address")
    subject: str = ""
    body: str = ""
    closing: str = "Sincerely,"

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: dt.date | None) -> dt.date:
        return v or dt.datetime.now(dt.UTC).date()
