import base64
import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
from pyairtable import Api
from pyairtable.api.types import RecordDict
from pyairtable.formulas import match

from src.configs import c
from src.schemas import (
    Company,
    CompanyCreate,
    Contact,
    ContactCreate,
    Job,
    PartialJob,
    RecordId,
)


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

    def _add_id(self, record: RecordDict) -> dict[str, Any]:
        """Add the record id to the fields dict for Pydantic validation."""
        return {**record.get("fields", {}), "id": record.get("id")}

    def get_partial_job(self, job_id: RecordId) -> PartialJob:
        rec = self.jobs.get(job_id)
        return PartialJob.model_validate(self._add_id(rec))

    def get_job(self, job_id: RecordId) -> Job:
        rec = self.jobs.get(job_id)
        company_id = first_link_id(rec.get("fields", {}), c.fields["jobs"]["company"])
        company = self.get_company(company_id) if company_id else None
        contact_id = first_link_id(rec.get("fields", {}), c.fields["jobs"]["recipient"])
        contact = self.get_contact(contact_id) if contact_id else None
        fields = self._add_id(rec)
        return Job.model_validate({**fields, "company": company, "contact": contact})

    def update_job(self, job_id: RecordId, fields: dict[str, Any]) -> RecordId:
        rec = self.jobs.update(job_id, fields)
        return rec["id"]

    def find_or_create_company(self, company: CompanyCreate) -> RecordId:
        fields = company.model_dump(
            by_alias=True, include={"name", "country"}, exclude_none=True
        )
        existing = self.companies.all(formula=match(fields))
        if existing:
            return existing[0]["id"]

        rec = self.companies.create(company.model_dump(by_alias=True))
        lg.info("Created company: %s (%s)", company.name, rec["id"])
        return rec["id"]

    def get_company(self, company_id: RecordId) -> Company:
        rec = self.companies.get(company_id)
        return Company.model_validate(self._add_id(rec))

    def find_or_create_contact(self, contact: ContactCreate) -> RecordId | None:
        existing = None
        if contact.email:
            fields = contact.model_dump(include={"email"})
            existing = self.contacts.all(formula=match(fields))

        if not existing and (contact.first and contact.last):
            fields = contact.model_dump(
                by_alias=True, include={"first", "last"}, exclude_none=True
            )
            existing = self.contacts.all(formula=match(fields))

        if existing:
            return existing[0]["id"]

        rec = self.contacts.create(contact.model_dump(by_alias=True))
        lg.info("Created contact: %s %s (%s)", contact.first, contact.last, rec["id"])
        return rec["id"]

    def get_contact(self, contact_id: RecordId) -> Contact:
        rec = self.contacts.get(contact_id)
        return Contact.model_validate(self._add_id(rec))

    async def upload_attachment(
        self,
        record_id: RecordId,
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
