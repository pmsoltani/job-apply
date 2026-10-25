import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


_DESC_ID = "Airtable record ID"

_ID_PATTERN = re.compile(r"^rec[a-zA-Z0-9]{14}$")


class CommonModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


RecordId = Annotated[str, Field(..., description=_DESC_ID, pattern=_ID_PATTERN)]


def field_alias(model: type[BaseModel], field: str) -> str:
    """Return the Airtable name of a model field, which is its alias."""
    alias = model.model_fields[field].alias
    if not isinstance(alias, str):  # Narrows pydantic's untyped `alias` for ty.
        raise ValueError(f"{model.__name__}.{field} has no Airtable alias")  # noqa: TRY004
    return alias


StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True)]
