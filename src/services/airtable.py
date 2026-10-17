import base64
import logging
from typing import Any

import httpx2
from pyairtable import Api
from pyairtable.api.types import RecordDict
from pyairtable.formulas import match
from pydantic import BaseModel
from requests import HTTPError

from src.configs import c
from src.schemas import (
    Company,
    CompanyCreate,
    Contact,
    ContactCreate,
    Job,
    JobLinks,
    PartialJob,
    RecordId,
)


lg = logging.getLogger(c.APP_NAME)


def _aliases(*models: type[BaseModel]) -> set[str]:
    """Return the Airtable field names the models map to, i.e. their aliases."""
    return {f.alias for m in models for f in m.model_fields.values() if f.alias}


class AirtableService:
    def __init__(self) -> None:
        api = Api(c.AIRTABLE_PAT)
        base = api.base(c.AIRTABLE_BASE_ID)
        self.jobs = base.table(c.AIRTABLE_JOBS_TABLE)
        self.companies = base.table(c.AIRTABLE_COMPANIES_TABLE)
        self.contacts = base.table(c.AIRTABLE_CONTACTS_TABLE)

    def check_schema(self) -> None:
        """Raise if a table or field the models map to is missing from the base."""
        expected = [
            (self.jobs, _aliases(Job, PartialJob)),
            (self.companies, _aliases(Company)),
            (self.contacts, _aliases(Contact)),
        ]
        missing: list[str] = []
        for table, names in expected:
            try:
                actual = {f.name for f in table.schema().fields}
            except KeyError:
                missing.append(f"table '{table.name}'")
                continue
            except HTTPError as exc:
                # Most likely the token lacks the `schema.bases:read` scope.
                lg.warning("Skipped the Airtable schema check: %s", exc)
                return
            missing += [f"'{table.name}.{name}'" for name in sorted(names - actual)]

        if missing:
            raise RuntimeError(f"Airtable base is missing {', '.join(missing)}")
        lg.info("Airtable schema check passed.")

    def _add_id(self, record: RecordDict) -> dict[str, Any]:
        """Add the record id to the fields dict for Pydantic validation."""
        return {**record.get("fields", {}), "id": record.get("id")}

    def get_partial_job(self, job_id: RecordId) -> PartialJob:
        rec = self.jobs.get(job_id)
        return PartialJob.model_validate(self._add_id(rec))

    def get_job(self, job_id: RecordId) -> Job:
        fields = self._add_id(self.jobs.get(job_id))
        links = JobLinks.model_validate(fields)
        if not links.company_ids:
            raise ValueError(f"Job record {job_id} has no linked company.")
        company = self.get_company(links.company_ids[0])
        contact_ids = links.contact_ids
        contact = self.get_contact(contact_ids[0]) if contact_ids else None
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

    def find_or_create_contact(self, contact: ContactCreate) -> RecordId:
        existing = None
        if contact.email:
            fields = contact.model_dump(by_alias=True, include={"email"})
            existing = self.contacts.all(formula=match(fields))

        if not existing and (contact.first and contact.last):
            fields = contact.model_dump(
                by_alias=True, include={"first", "last"}, exclude_none=True
            )
            existing = self.contacts.all(formula=match(fields))

        if existing:
            return existing[0]["id"]

        rec = self.contacts.create(contact.model_dump(by_alias=True))
        lg.info("Created contact: %s (%s)", contact.name, rec["id"])
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

        async with httpx2.AsyncClient(timeout=c.TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

        lg.info("Uploaded %s to %s", filename, field_name)
