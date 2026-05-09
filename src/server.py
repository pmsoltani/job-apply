import logging

import uvicorn
from fastapi import BackgroundTasks, FastAPI

from src.airtable_client import AirtableClient
from src.configs import ac, bc
from src.fetcher import clean_markdown, fetch_url
from src.generator import generate_documents
from src.parser import extract_job
from src.schemas import LetterData, WebhookPayload
from src.typst_builder import build_cover_letter, build_cv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="job-apply")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Pipeline 1 — Ingest
# ---------------------------------------------------------------------------


async def _run_ingest(record_id: str) -> None:
    at = AirtableClient()
    f = ac.fields

    try:
        record = at.get_job(record_id)
        fields = record.get("fields", {})

        ad_url: str = fields.get(f["jobs"]["ad"], "")
        notes: str = fields.get(f["jobs"]["notes"], "")

        if notes.strip():
            # User pasted the description manually — use it directly
            source_text = clean_markdown(notes)
        elif ad_url.strip():
            raw = await fetch_url(ad_url)
            source_text = clean_markdown(raw)
        else:
            logger.error(
                "[ingest %s] Neither AD URL nor Notes is populated.", record_id
            )
            return

        job = await extract_job(source_text)

        # Upsert Company
        company_id = at.find_or_create_company(job.company)

        # Upsert Contact (if found)
        contact_id = None
        if job.contact:
            contact_id = at.find_or_create_contact(job.contact, company_id=company_id)

        # Update the Jobs record
        update: dict = {
            f["jobs"]["title"]: job.job_title,
            f["jobs"]["notes"]: job.job_description,
            f["jobs"]["company"]: [company_id],
        }
        if contact_id:
            update[f["jobs"]["recipient"]] = [contact_id]

        at.update_job(record_id, update)
        logger.info("[ingest %s] Done. Job: %s", record_id, job.job_title)

    except Exception:
        logger.exception("[ingest %s] Pipeline 1 failed.", record_id)


@app.post("/ingest", status_code=202)
async def ingest(payload: WebhookPayload, background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_run_ingest, payload.record_id)
    return {"status": "accepted", "record_id": payload.record_id}


# ---------------------------------------------------------------------------
# Pipeline 2 — Generate
# ---------------------------------------------------------------------------


async def _run_generate(record_id: str) -> None:
    at = AirtableClient()
    f = ac.fields

    try:
        record = at.get_job(record_id)
        fields = record.get("fields", {})

        job_prompt: str = fields.get(f["jobs"]["prompt"], "")
        if not job_prompt.strip():
            logger.error("[generate %s] Prompt field is empty.", record_id)
            return

        job_title: str = fields.get(f["jobs"]["title"], "Position")

        # Resolve company address from the linked Company record
        to_address = ""
        company_links: list = fields.get(f["jobs"]["company"], [])
        if company_links:
            company_id = (
                company_links[0]
                if isinstance(company_links[0], str)
                else company_links[0]["id"]
            )
            company_record = at.get_company(company_id)
            to_address = company_record.get("fields", {}).get(
                f["companies"]["address"], ""
            )

        # Resolve recipient name from the linked Contact record
        to_name = "Hiring Manager"
        recipient_links: list = fields.get(f["jobs"]["recipient"], [])
        if recipient_links:
            contact_id = (
                recipient_links[0]
                if isinstance(recipient_links[0], str)
                else recipient_links[0]["id"]
            )
            contact_record = at.contacts.get(contact_id)
            contact_fields = contact_record.get("fields", {})
            cf = f["contacts"]
            parts = [
                contact_fields.get(cf["title"], ""),
                contact_fields.get(cf["first"], ""),
                contact_fields.get(cf["last"], ""),
            ]
            to_name = " ".join(p for p in parts if p).strip() or "Hiring Manager"

        # LLM generation
        content = await generate_documents(job_prompt)

        # Build cover letter PDF
        letter_data = LetterData(
            to=to_name,
            to_address=to_address,
            subject=job_title,
            body=content.cover_letter_body,
        )
        letter_pdf = build_cover_letter(letter_data)
        cv_pdf = build_cv(content.profile_intro)

        # Upload both PDFs to Airtable
        docs_field = f["jobs"]["docs"]
        await at.upload_attachment(record_id, docs_field, "letter.pdf", letter_pdf)
        await at.upload_attachment(record_id, docs_field, "cv.pdf", cv_pdf)

        logger.info("[generate %s] Done.", record_id)

    except Exception:
        logger.exception("[generate %s] Pipeline 2 failed.", record_id)


@app.post("/generate", status_code=202)
async def generate(payload: WebhookPayload, background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_run_generate, payload.record_id)
    return {"status": "accepted", "record_id": payload.record_id}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    uvicorn.run(
        "src.server:app", host=bc.FASTAPI_HOST, port=bc.FASTAPI_PORT, reload=True
    )
