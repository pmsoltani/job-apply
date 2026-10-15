import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


_DESC_ID = "Airtable record ID"


class CommonModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


_ID_PATTERN = re.compile(r"^rec[a-zA-Z0-9]{14}$")


RecordId = Annotated[str, Field(..., description=_DESC_ID, pattern=_ID_PATTERN)]
