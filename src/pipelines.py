import logging

from src import tasks
from src.configs import CVStyle, LetterStyle, c
from src.schemas import CompanyCreate, ContactCreate, Letter, RecordId
from src.services import AirtableService, GeneratorService, ParserService, TypstService
from src.utils import clean_markdown, fetch_url


lg = logging.getLogger(c.APP_NAME)


async def run_parse(
    job_id: RecordId,
    airtable: AirtableService,
    parser: ParserService,
    model: str | None = None,
) -> None:
    task_id = f"parse:{job_id}"
    tasks.register(task_id, f"Parsing job posting ({job_id})")
    try:
        partial_job = airtable.get_partial_job(job_id)
        notes, url = partial_job.notes, partial_job.url

        if notes and notes.strip():
            source_text = clean_markdown(notes)
        elif url and url.strip():
            raw = await fetch_url(f"{c.JINA_BASE_URL}/{url}", c.TIMEOUT_SECONDS)
            source_text = clean_markdown(raw)
        else:
            lg.error("[parse %s] Neither AD URL nor Notes is populated.", job_id)
            return

        job = await parser.parse(source_text, model=model)
        job.url = job.url or url
        tasks.register(task_id, f"Saving: {job.job} @ {job.company.name}")

        company_id = airtable.find_or_create_company(
            CompanyCreate.model_validate(job.company)
        )
        contact_id = None
        if job.contact:
            contact_id = airtable.find_or_create_contact(
                ContactCreate.model_validate(job.contact)
            )

        update = job.model_dump(
            by_alias=True, exclude={"company", "contact", "prompt"}, exclude_none=True
        )
        update["Company"] = [company_id]
        update["Recipient"] = [contact_id] if contact_id else None

        airtable.update_job(job_id, update)
        lg.info("[parse %s] Done. Job: %s", job_id, job.job)

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("[parse %s] Pipeline 1 failed.", job_id)
    finally:
        tasks.unregister(task_id)


async def run_generate(
    job_id: RecordId,
    airtable: AirtableService,
    generator: GeneratorService,
    model: str | None = None,
) -> None:
    task_id = f"generate:{job_id}"
    tasks.register(task_id, f"Generating content ({job_id})")
    try:
        job = airtable.get_job(job_id)

        job_prompt = job.prompt or ""
        if not job_prompt.strip():
            lg.error("[generate %s] Prompt field is empty.", job_id)
            return

        job_title = job.job or job_id
        tasks.register(task_id, f"Generating content: {job_title}")

        content = await generator.generate(job_prompt, model=model)

        tasks.register(task_id, f"Saving content: {job_title}")
        airtable.update_job(
            job_id, content.model_dump(by_alias=True, exclude_unset=True)
        )

        lg.info("[generate %s] Done.", job_id)

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("[generate %s] Pipeline 2 failed.", job_id)
    finally:
        tasks.unregister(task_id)


async def run_compile(
    job_id: RecordId,
    airtable: AirtableService,
    typst: TypstService,
    cv_style: CVStyle = CVStyle.CLASSIC,
) -> None:
    task_id = f"compile:{job_id}"
    tasks.register(task_id, f"Compiling PDFs ({job_id})")
    try:
        job = airtable.get_job(job_id)

        cv_content = (job.cv_content or "").strip()
        letter_content = (job.letter_content or "").strip()
        if not letter_content:
            lg.error("[compile %s] Empty letter Content! Run /generate first.", job_id)
            return

        job_title = job.job
        tasks.register(task_id, f"Compiling PDFs: {job_title}")

        to_address = job.address or ""
        if not to_address.strip():
            lg.warning(
                "[compile %s] Company '%s' has no address!", job_id, job.company.name
            )

        to_name = "Hiring Manager"
        if job.contact:
            to_name = job.contact.name or to_name

        letter_data = Letter(
            to_name=to_name,
            to_address=to_address,
            subject=job_title,
            body=letter_content,
        )

        letter_style = LetterStyle.get_style(job.company.country)
        letter_pdf = typst.compile_letter(letter_data, style=letter_style)
        cv_pdf = typst.compile_cv(cv_content, cv_style)

        tasks.register(task_id, f"Uploading PDFs: {job_title}")
        await airtable.upload_attachment(job_id, "Docs", "letter.pdf", letter_pdf)
        await airtable.upload_attachment(job_id, "Docs", "cv.pdf", cv_pdf)

        lg.info("[compile %s] Done.", job_id)

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("[compile %s] Pipeline 3 failed.", job_id)
    finally:
        tasks.unregister(task_id)
