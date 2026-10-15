from pydantic import Field, field_validator

from src.configs import c
from src.schemas.common import CommonModel, RecordId


_DESC_NAME = "The official company name, as it appears in the job posting."
_DESC_URL = (
    "The company website, only if stated in the posting. Otherwise, infer it from an "
    "email domain mentioned in the posting (e.g. '@company.com'), but only if that "
    "domain is clearly the company's."
)
_DESC_COUNTRY = (
    "ISO 3166-1 alpha-2 code of the job location: exactly two uppercase letters "
    "(e.g. 'GB' for Glasgow, 'US' for New York), not a full country name. If the "
    "posting lists several locations, use the first one, preferring locations in the UK."
)
_DESC_NOTES = "The section of the posting that describes the company, if there is one."


class CompanyBase(CommonModel):
    name: str = Field(..., alias="Company", description=_DESC_NAME)
    url: str | None = Field(None, alias="URL", description=_DESC_URL)
    country: str = Field(
        ..., alias="Country", pattern=r"^[A-Z]{2}$", description=_DESC_COUNTRY
    )
    notes: str | None = Field(None, alias="Notes", description=_DESC_NOTES)

    @field_validator("country", mode="after")
    @classmethod
    def normalize_country_codes(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return c.COUNTRY_CODE_MAPPING.get(v, v)


class Company(CompanyBase):
    id: RecordId


class CompanyCreate(CompanyBase):
    pass
