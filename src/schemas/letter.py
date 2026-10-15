from pydantic import Field

from src.configs import c
from src.schemas.common import CommonModel


class Letter(CommonModel):
    """Maps to letter/data.json consumed by the Typst cover letter template."""

    date: str = ""
    from_name: str = Field(c.full_name, alias="from")
    from_address: str = Field(c.address, alias="from-address")
    to_name: str = Field("Hiring Manager", alias="to")
    to_address: str = Field("", alias="to-address")
    subject: str = ""
    body: str = ""
    closing: str = "Sincerely,"
