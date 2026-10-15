from pydantic import Field, model_validator

from src.configs import ContactTitle
from src.schemas.common import CommonModel, RecordId


class ContactBase(CommonModel):
    title: ContactTitle | None = Field(None, alias="Title")
    first: str | None = Field(None, alias="First")
    last: str | None = Field(None, alias="Last")
    role: str | None = Field(None, alias="Role")
    email: str | None = Field(None, alias="Email")
    url: str | None = Field(None, alias="URL")

    @model_validator(mode="after")
    def ensure_first_or_last(self) -> "ContactBase":
        """Ensure that at least one of first or last name is provided."""
        if not self.first and not self.last:
            raise ValueError("At least one of first or last name must be provided.")
        return self


class Contact(ContactBase):
    id: RecordId
    preferred: str | None = Field(None, alias="Preferred")

    @property
    def name(self) -> str | None:
        """Return the contact's name, if available."""
        if self.preferred:
            return self.preferred
        if self.title and self.last:
            return f"{self.title} {self.last}"
        if self.first and self.last:
            return f"{self.first} {self.last}"
        return self.first


class ContactCreate(ContactBase):
    pass
