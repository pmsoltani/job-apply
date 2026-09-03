import base64
import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
from pyairtable import Api
from pyairtable.api.types import RecordDict
from pyairtable.formulas import match

from src.configs import c
from src.schemas import CompanyData, ContactData


lg = logging.getLogger(c.APP_NAME)


def field_str(fields: Mapping[str, Any], key: str, default: str = "") -> str:
    """Read a text field from a record's `fields`, narrowing the type to `str`."""
    value = fields.get(key, default)
    return value if isinstance(value, str) else default


def first_link_id(fields: Mapping[str, Any], key: str) -> str | None:
    """Return the first record id from a linked-record field, if any.

    Linked records come either as bare id strings or as `{"id": ...}` dicts,
    depending on the API options used to fetch them.
    """
    links = fields.get(key)
    if not isinstance(links, list) or not links:
        return None
    first = links[0]
    if isinstance(first, str):
        return first
    if isinstance(first, dict):
        record_id = first.get("id")
        if isinstance(record_id, str):
            return record_id
    return None


class AirtableService:
    def __init__(self) -> None:
        api = Api(c.AIRTABLE_PAT)
        base = api.base(c.AIRTABLE_BASE_ID)
        self.jobs = base.table(c.tables["jobs"])
        self.companies = base.table(c.tables["companies"])
        self.contacts = base.table(c.tables["contacts"])

    def get_job(self, job_id: str) -> RecordDict:
        return self.jobs.get(job_id)

    def update_job(self, job_id: str, fields: dict[str, Any]) -> RecordDict:
        return self.jobs.update(job_id, fields)

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
        if data.notes:
            new_fields[f["notes"]] = data.notes

        record = self.companies.create(new_fields)
        lg.info("Created company: %s (%s)", data.name, record["id"])
        return record["id"]

    def get_company(self, company_id: str) -> RecordDict:
        return self.companies.get(company_id)

    def find_or_create_contact(self, data: ContactData, job_id: str) -> str | None:
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
            ("url", "url"),
        ):
            if getattr(data, attr):
                new_fields[f[key]] = getattr(data, attr)
        new_fields[f["jobs"]] = [job_id]

        record = self.contacts.create(new_fields)
        lg.info("Created contact: %s %s (%s)", data.first, data.last, record["id"])
        return record["id"]

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
        headers = {
            "Authorization": f"Bearer {c.AIRTABLE_PAT}",
            "Content-Type": "application/json",
        }
        payload = {
            "contentType": content_type,
            "file": base64.b64encode(file_bytes).decode("utf-8"),
            "filename": filename,
        }

        async with (
            aiohttp.ClientSession() as session,
            session.post(url, headers=headers, json=payload) as response,
        ):
            response.raise_for_status()

        lg.info("Uploaded %s to %s / %s", filename, record_id, field_name)
