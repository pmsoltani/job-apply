import logging

from src import tasks
from src.configs import CVStyle, LetterStyle, c
from src.schemas import CompanyCreate, ContactCreate, Job, Letter, RecordId, field_alias
from src.services import AirtableService, GeneratorService, ParserService, TypstService
from src.utils import clean_markdown, fetch_url


lg = logging.getLogger(c.APP_NAME)


async def run_parse(
    job_id: RecordId,
    airtable: AirtableService,
    parser: ParserService,
    model: str | None = None,
) -> None:
    with tasks.background(f"parse:{job_id}", "Loading the job posting"):
        partial_job = await airtable.get_partial_job(job_id)
        notes, url = partial_job.notes, partial_job.url

        if notes and notes.strip():
            source_text = clean_markdown(notes)
        elif url and url.strip():
            raw = await fetch_url(f"{c.JINA_BASE_URL}/{url}", c.TIMEOUT_SECONDS)
            source_text = clean_markdown(raw)
        else:
            lg.error("Neither job URL nor Notes is populated.")
            return

        tasks.update("Parsing the job posting")
        job = await parser.parse(source_text, model=model)
        tasks.update(f"Saving: {job.title} @ {job.company.name}")

        company_id = await airtable.find_or_create_company(
            CompanyCreate.model_validate(job.company)
        )
        contact_id = None
        if job.contact:
            contact_id = await airtable.find_or_create_contact(
                ContactCreate.model_validate(job.contact)
            )

        update = job.model_dump(
            by_alias=True, exclude={"company", "contact"}, exclude_none=True
        )
        update[field_alias(Job, "company_ids")] = [company_id]
        if contact_id:
            update[field_alias(Job, "contact_ids")] = [contact_id]

        await airtable.update_job(job_id, update)
        lg.info("Done.")


async def run_generate(
    job_id: RecordId,
    airtable: AirtableService,
    generator: GeneratorService,
    model: str | None = None,
) -> None:
    with tasks.background(f"generate:{job_id}", "Loading the job"):
        job = await airtable.get_job(job_id)
        tasks.update(f"Generating content: {job.title}")
        content = await generator.generate(job.make_prompt(), model=model)

        tasks.update("Saving content")
        await airtable.update_job(
            job_id, content.model_dump(by_alias=True, exclude_unset=True)
        )
        lg.info("Done.")


async def run_answer(
    question: str,
    airtable: AirtableService,
    generator: GeneratorService,
    job_id: RecordId | None = None,
) -> str:
    first_status = "Loading the job" if job_id else "Answering a question"
    with tasks.track(f"answer:{job_id or 'general'}", first_status):
        job = await airtable.get_job(job_id) if job_id else None
        parts = []
        if job:
            tasks.update(f"Answering a question: {job.title}")
            parts.append(job.make_prompt())
            if job.letter_content:
                parts.append(f"<cover_letter>\n{job.letter_content}\n</cover_letter>")
        parts.append(f"<question>\n{question}\n</question>")
        answer = await generator.answer("\n\n".join(parts))
        lg.info("Done.")
        return answer


async def run_compile(
    job_id: RecordId,
    airtable: AirtableService,
    typst: TypstService,
    cv_style: CVStyle = CVStyle.CLASSIC,
) -> None:
    with tasks.background(f"compile:{job_id}", "Loading the job"):
        job = await airtable.get_job(job_id)

        cv_content = (job.cv_content or "").strip()
        letter_content = (job.letter_content or "").strip()
        if not letter_content:
            lg.error("Empty letter Content! Run /generate first.")
            return

        tasks.update(f"Compiling PDFs: {job.title}")

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
        letter_pdf = await typst.compile_letter(letter_data, style=letter_style)
        cv_pdf = await typst.compile_cv(cv_content, cv_style)

        tasks.update("Uploading PDFs")
        docs = field_alias(Job, "docs")
        await airtable.upload_attachment(job_id, docs, "letter.pdf", letter_pdf)
        await airtable.upload_attachment(job_id, docs, "cv.pdf", cv_pdf)
        lg.info("Done.")
