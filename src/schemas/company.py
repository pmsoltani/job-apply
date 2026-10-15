from pydantic import Field, field_validator

from src.configs import c
from src.schemas.common import CommonModel, RecordId


_DESC_COUNTRY = "ISO 3166-1 alpha-2 country code"


class CompanyBase(CommonModel):
    name: str = Field(alias="Company")
    url: str | None = Field(None, alias="URL")
    country: str = Field(
        ..., alias="Country", pattern=r"^[A-Z]{2}$", description=_DESC_COUNTRY
    )
    notes: str | None = Field(None, alias="Notes")

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
