import logging

from src.configs import c
from src.schemas import LetterData
from src.services import AirtableService, GeneratorService, ParserService, TypstService
from src.utils import clean_markdown, fetch_url


logger = logging.getLogger(__name__)


async def run_ingest(
    record_id: str,
    airtable: AirtableService,
    parser: ParserService,
    model: str | None = None,
) -> None:
    f = c.fields
    try:
        record = airtable.get_job(record_id)
        fields = record.get("fields", {})

        ad_url: str = fields.get(f["jobs"]["ad"], "")
        notes: str = fields.get(f["jobs"]["notes"], "")

        if notes.strip():
            source_text = clean_markdown(notes)
        elif ad_url.strip():
            raw = await fetch_url(f"{c.JINA_BASE_URL}/{ad_url}", c.TIMEOUT_SECONDS)
            source_text = clean_markdown(raw)
        else:
            logger.error("[ingest %s] Neither AD URL nor Notes is populated.", record_id)
            return

        job = await parser.extract_job(source_text, model=model)

        company_id = airtable.find_or_create_company(job.company)
        contact_id = None
        if job.contact:
            contact_id = airtable.find_or_create_contact(job.contact, company_id=company_id)

        update: dict = {
            f["jobs"]["job"]: job.job,
            f["jobs"]["notes"]: job.notes,
            f["jobs"]["company"]: [company_id],
        }
        if contact_id:
            update[f["jobs"]["recipient"]] = [contact_id]

        airtable.update_job(record_id, update)
        logger.info("[ingest %s] Done. Job: %s", record_id, job.job)

    except Exception:
        logger.exception("[ingest %s] Pipeline 1 failed.", record_id)


async def run_generate(
    record_id: str,
    airtable: AirtableService,
    generator: GeneratorService,
    typst: TypstService,
    model: str | None = None,
) -> None:
    f = c.fields
    try:
        record = airtable.get_job(record_id)
        fields = record.get("fields", {})

        job_prompt: str = fields.get(f["jobs"]["prompt"], "")
        if not job_prompt.strip():
            logger.error("[generate %s] Prompt field is empty.", record_id)
            return

        job_title: str = fields.get(f["jobs"]["job"], "Position")

        to_address = ""
        company_links: list = fields.get(f["jobs"]["company"], [])
        if company_links:
            company_id = (
                company_links[0]
                if isinstance(company_links[0], str)
                else company_links[0]["id"]
            )
            company_record = airtable.get_company(company_id)
            to_address = company_record.get("fields", {}).get(
                f["companies"]["address"], ""
            )

        to_name = "Hiring Manager"
        recipient_links: list = fields.get(f["jobs"]["recipient"], [])
        if recipient_links:
            contact_id = (
                recipient_links[0]
                if isinstance(recipient_links[0], str)
                else recipient_links[0]["id"]
            )
            contact_record = airtable.contacts.get(contact_id)
            contact_fields = contact_record.get("fields", {})
            cf = f["contacts"]
            parts = [
                contact_fields.get(cf["title"], ""),
                contact_fields.get(cf["first"], ""),
                contact_fields.get(cf["last"], ""),
            ]
            to_name = " ".join(p for p in parts if p).strip() or "Hiring Manager"

        content = await generator.generate_documents(job_prompt, model=model)

        letter_data = LetterData(
            to=to_name,
            to_address=to_address,
            subject=job_title,
            body=content.cover_letter_body,
        )
        letter_pdf = typst.build_cover_letter(letter_data)
        cv_pdf = typst.build_cv(content.profile_intro)

        docs_field = f["jobs"]["docs"]
        await airtable.upload_attachment(record_id, docs_field, "letter.pdf", letter_pdf)
        await airtable.upload_attachment(record_id, docs_field, "cv.pdf", cv_pdf)

        logger.info("[generate %s] Done.", record_id)

    except Exception:
        logger.exception("[generate %s] Pipeline 2 failed.", record_id)
