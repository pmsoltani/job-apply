import logging
from typing import Any, Optional

import aiohttp
from pyairtable import Api
from pyairtable.api.types import RecordDict
from pyairtable.formulas import match

from src.configs import c
from src.schemas import CompanyData, ContactData


logger = logging.getLogger(__name__)


class AirtableService:
    def __init__(self) -> None:
        api = Api(c.AIRTABLE_PAT)
        base = api.base(c.AIRTABLE_BASE_ID)
        self.jobs = base.table(c.tables["jobs"])
        self.companies = base.table(c.tables["companies"])
        self.contacts = base.table(c.tables["contacts"])

    # -------------------------------------------------------------------------
    # Jobs
    # -------------------------------------------------------------------------

    def get_job(self, record_id: str) -> RecordDict:
        return self.jobs.get(record_id)

    def update_job(self, record_id: str, fields: dict[str, Any]) -> RecordDict:
        return self.jobs.update(record_id, fields)

    # -------------------------------------------------------------------------
    # Companies — find-or-create
    # -------------------------------------------------------------------------

    def find_or_create_company(self, data: CompanyData) -> str:
        f = c.fields["companies"]
        existing = self.companies.all(formula=match({f["company"]: data.name}))
        if existing:
            return existing[0]["id"]

        new_fields: dict[str, Any] = {f["company"]: data.name}
        if data.url:
            new_fields[f["url"]] = data.url
        if data.country:
            new_fields[f["country"]] = data.country

        record = self.companies.create(new_fields)
        logger.info("Created company: %s (%s)", data.name, record["id"])
        return record["id"]

    def get_company(self, record_id: str) -> RecordDict:
        return self.companies.get(record_id)

    # -------------------------------------------------------------------------
    # Contacts — find-or-create
    # -------------------------------------------------------------------------

    def find_or_create_contact(
        self, data: ContactData, company_id: Optional[str] = None
    ) -> Optional[str]:
        f = c.fields["contacts"]

        if data.email:
            existing = self.contacts.all(formula=match({f["email"]: data.email}))
        elif data.first and data.last:
            existing = self.contacts.all(
                formula=f'AND({{{f["first"]}}} = "{data.first}", {{{f["last"]}}} = "{data.last}")'
            )
        else:
            return None

        if existing:
            return existing[0]["id"]

        new_fields: dict[str, Any] = {}
        for attr, key in (
            ("title", "title"),
            ("first", "first"),
            ("last", "last"),
            ("role", "role"),
            ("email", "email"),
        ):
            if getattr(data, attr):
                new_fields[f[key]] = getattr(data, attr)
        if company_id:
            new_fields[f["company"]] = [company_id]

        record = self.contacts.create(new_fields)
        logger.info("Created contact: %s %s (%s)", data.first, data.last, record["id"])
        return record["id"]

    # -------------------------------------------------------------------------
    # Attachments
    # -------------------------------------------------------------------------

    async def upload_attachment(
        self,
        record_id: str,
        field_name: str,
        filename: str,
        file_bytes: bytes,
        content_type: str = "application/pdf",
    ) -> None:
        url = (
            f"{c.CONTENT_BASE_URL}/v0"
            f"/{c.AIRTABLE_BASE_ID}"
            f"/{record_id}"
            f"/{field_name}"
            "/uploadAttachment"
        )
        headers = {"Authorization": f"Bearer {c.AIRTABLE_PAT}"}
        form = aiohttp.FormData()
        form.add_field("file", file_bytes, filename=filename, content_type=content_type)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form) as response:
                response.raise_for_status()

        logger.info("Uploaded %s to %s / %s", filename, record_id, field_name)
