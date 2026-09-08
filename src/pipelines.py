import logging
from typing import Any

from src import tasks
from src.configs import CVStyle, c
from src.schemas import LetterData
from src.services import (
    AirtableService,
    GeneratorService,
    ParserService,
    TypstService,
    field_str,
    first_link_id,
)
from src.utils import clean_markdown, fetch_url


lg = logging.getLogger(c.APP_NAME)


async def run_parse(
    job_id: str,
    airtable: AirtableService,
    parser: ParserService,
    model: str | None = None,
) -> None:
    task_id = f"parse:{job_id}"
    tasks.register(task_id, f"Parsing job posting ({job_id})")
    f = c.fields
    try:
        record = airtable.get_job(job_id)
        fields = record.get("fields", {})

        ad_url = field_str(fields, f["jobs"]["ad"])
        notes = field_str(fields, f["jobs"]["notes"])

        if notes.strip():
            source_text = clean_markdown(notes)
        elif ad_url.strip():
            raw = await fetch_url(f"{c.JINA_BASE_URL}/{ad_url}", c.TIMEOUT_SECONDS)
            source_text = clean_markdown(raw)
        else:
            lg.error("[parse %s] Neither AD URL nor Notes is populated.", job_id)
            return

        job = await parser.extract_job_data(source_text, model=model)
        tasks.register(task_id, f"Saving: {job.job} @ {job.company.name}")

        company_id = airtable.find_or_create_company(job.company)
        contact_id = None
        if job.contact:
            contact_id = airtable.find_or_create_contact(job.contact, job_id=job_id)

        update: dict[str, Any] = {
            f["jobs"]["job"]: job.job,
            f["jobs"]["notes"]: job.notes,
            f["jobs"]["company"]: [company_id],
        }
        if job.type:
            update[f["jobs"]["type"]] = job.type
        if contact_id:
            update[f["jobs"]["recipient"]] = [contact_id]

        airtable.update_job(job_id, update)
        lg.info("[parse %s] Done. Job: %s", job_id, job.job)

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("[parse %s] Pipeline 1 failed.", job_id)
    finally:
        tasks.unregister(task_id)


async def run_generate(
    job_id: str,
    airtable: AirtableService,
    generator: GeneratorService,
    model: str | None = None,
) -> None:
    task_id = f"generate:{job_id}"
    tasks.register(task_id, f"Generating content ({job_id})")
    f = c.fields
    try:
        record = airtable.get_job(job_id)
        fields = record.get("fields", {})

        job_prompt = field_str(fields, f["jobs"]["prompt"])
        if not job_prompt.strip():
            lg.error("[generate %s] Prompt field is empty.", job_id)
            return

        job_title = field_str(fields, f["jobs"]["job"], job_id)
        tasks.register(task_id, f"Generating content: {job_title}")

        content = await generator.generate_documents(job_prompt, model=model)

        tasks.register(task_id, f"Saving content: {job_title}")
        airtable.update_job(
            job_id,
            {
                f["jobs"]["letter_content"]: content.cover_letter_body,
                f["jobs"]["cv_content"]: content.profile_intro,
            },
        )

        lg.info("[generate %s] Done.", job_id)

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("[generate %s] Pipeline 2 failed.", job_id)
    finally:
        tasks.unregister(task_id)


async def run_compile(
    job_id: str,
    airtable: AirtableService,
    typst: TypstService,
    cv_style: CVStyle = CVStyle.CLASSIC,
) -> None:
    task_id = f"compile:{job_id}"
    tasks.register(task_id, f"Compiling PDFs ({job_id})")
    f = c.fields
    try:
        record = airtable.get_job(job_id)
        fields = record.get("fields", {})

        cv_content = field_str(fields, f["jobs"]["cv_content"]).strip()
        letter_content = field_str(fields, f["jobs"]["letter_content"]).strip()
        if not letter_content:
            lg.error("[compile %s] Empty letter Content! Run /generate first.", job_id)
            return

        job_title = field_str(fields, f["jobs"]["job"])
        tasks.register(task_id, f"Compiling PDFs: {job_title}")

        to_address = ""
        company_id = first_link_id(fields, f["jobs"]["company"])
        if company_id:
            company_data = airtable.get_company(company_id).get("fields", {})
            to_address = field_str(company_data, f["companies"]["address"])
            if not to_address.strip():
                c_name = field_str(company_data, f["companies"]["company"])
                lg.warning("[compile %s] Company '%s' has no address!", job_id, c_name)

        to_name = "Hiring Manager"
        contact_id = first_link_id(fields, f["jobs"]["recipient"])
        if contact_id:
            contact_data = airtable.contacts.get(contact_id).get("fields", {})
            contact_title = field_str(contact_data, f["contacts"]["title"])
            contact_last = field_str(contact_data, f["contacts"]["last"])
            if contact_title and contact_last:
                to_name = f"{contact_title} {contact_last}"

        letter_data = LetterData(
            to_name=to_name,
            to_address=to_address,
            subject=job_title,
            body=letter_content,
        )
        letter_pdf = typst.build_cover_letter(letter_data)
        cv_pdf = typst.build_cv(cv_content, cv_style)

        tasks.register(task_id, f"Uploading PDFs: {job_title}")
        docs_field = f["jobs"]["docs"]
        await airtable.upload_attachment(job_id, docs_field, "letter.pdf", letter_pdf)
        await airtable.upload_attachment(job_id, docs_field, "cv.pdf", cv_pdf)

        lg.info("[compile %s] Done.", job_id)

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("[compile %s] Pipeline 3 failed.", job_id)
    finally:
        tasks.unregister(task_id)
