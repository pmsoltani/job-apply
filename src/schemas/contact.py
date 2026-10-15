from pydantic import Field

from src.configs import ContactTitle
from src.schemas.common import CommonModel, RecordId


_DESC_TITLE = "Contact's title, inferred from first name if not provided"


class ContactBase(CommonModel):
    title: ContactTitle | None = Field(None, description=_DESC_TITLE, alias="Title")
    first: str | None = Field(None, alias="First")
    last: str | None = Field(None, alias="Last")
    role: str | None = Field(None, alias="Role")
    email: str | None = Field(None, alias="Email")
    url: str | None = Field(None, alias="URL")
    preferred: str | None = Field(None, alias="Preferred")

    @property
    def name(self) -> str | None:
        """Return the contact's full name, if available."""
        if self.preferred:
            return self.preferred
        if self.title and self.last:
            return f"{self.title} {self.last}"


class Contact(ContactBase):
    id: RecordId


class ContactCreate(ContactBase):
    last: str = Field(..., alias="Last")
