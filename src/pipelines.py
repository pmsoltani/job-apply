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
            lg.error("Neither job URL nor Notes is populated.")
            return

        job = await parser.parse(source_text, model=model)
        tasks.register(task_id, f"Saving: {job.title} @ {job.company.name}")

        company_id = airtable.find_or_create_company(
            CompanyCreate.model_validate(job.company)
        )
        contact_id = None
        if job.contact:
            contact_id = airtable.find_or_create_contact(
                ContactCreate.model_validate(job.contact)
            )

        update = job.model_dump(
            by_alias=True, exclude={"company", "contact"}, exclude_none=True
        )
        update["Company"] = [company_id]
        if contact_id:
            update["Recipient"] = [contact_id]

        airtable.update_job(job_id, update)
        lg.info("Done.")

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("Parser pipeline failed.")
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
            lg.error("Prompt field is empty.")
            return

        tasks.register(task_id, f"Generating content: {job.title}")

        content = await generator.generate(job_prompt, model=model)

        tasks.register(task_id, f"Saving content: {job.title}")
        airtable.update_job(
            job_id, content.model_dump(by_alias=True, exclude_unset=True)
        )
        lg.info("Done.")

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("Generator pipeline failed.")
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
            lg.error("Empty letter Content! Run /generate first.")
            return

        tasks.register(task_id, f"Compiling PDFs: {job.title}")

        to_address = job.address or ""
        if not to_address.strip():
            lg.warning("Job has no address!")

        to_name = "Hiring Manager"
        if job.contact:
            to_name = job.contact.name or to_name

        letter_data = Letter(
            to_name=to_name,
            to_address=to_address,
            subject=job.title,
            body=letter_content,
        )

        letter_style = LetterStyle.get_style(job.company.country)
        letter_pdf = typst.compile_letter(letter_data, style=letter_style)
        cv_pdf = typst.compile_cv(cv_content, cv_style)

        tasks.register(task_id, f"Uploading PDFs: {job.title}")
        await airtable.upload_attachment(job_id, "Docs", "letter.pdf", letter_pdf)
        await airtable.upload_attachment(job_id, "Docs", "cv.pdf", cv_pdf)
        lg.info("Done.")

    except Exception:  # noqa: BLE001 - background-task boundary, traceback is logged
        lg.exception("Compiler pipeline failed.")
    finally:
        tasks.unregister(task_id)
