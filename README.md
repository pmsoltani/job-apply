# job-apply

<img alt="Project Logo" src="static/logo.svg" width="200">

Parses job postings and generates tailored cover letters and CVs as PDFs, driven from an Airtable base.

Three pipelines, each triggered by a button in Airtable:

| Pipeline     | Reads                               | Writes                                                 |
| ------------ | ----------------------------------- | ------------------------------------------------------ |
| **parse**    | `AD` (URL) or `Notes` (pasted text) | `Job`, `Type`, `Notes`, `Company`, `Recipient`         |
| **generate** | `Prompt`                            | `Letter Content`, `CV Content`, `Fitness`, `Reasoning` |
| **compile**  | `Letter Content`, `CV Content`      | `Docs` (two PDFs)                                      |

`parse` fetches the posting through [Jina Reader](https://jina.ai/reader/) and extracts structured fields with an LLM. `generate` writes the letter from your CV and personal context. `compile` renders both using Typst templates.

At each stage, you can review and edit the results in Airtable before moving on. The final PDFs are stored in Airtable as attachments.

## Requirements

|                                         |                                                                    |
| --------------------------------------- | ------------------------------------------------------------------ |
| Python                                  | 3.13 or newer, with [uv](https://docs.astral.sh/uv/)               |
| [Typst](https://github.com/typst/typst) | on `PATH`, invoked as a subprocess to render PDFs                  |
| Typst templates                         | the sibling **`cv`** repository (see below)                        |
| Airtable                                | a base with Jobs, Companies and Contacts tables                    |
| LLM                                     | an API key for Anthropic, Google or any OpenAI-compatible endpoint |

### The `cv` repository

The Typst templates live **outside this repo**. `CV_DIR` defaults to `../cv`, so the two must sit side by side:

```plaintext
Git/
├── job-apply/          <- this repository
└── cv/
    ├── classic/        <- CV template
    ├── modern/         <- CV template
    ├── letter/         <- cover letter template
    └── shared/         <- constants and helpers
```

Without it, `parse` and `generate` still work but `compile` fails. Set `CV_DIR` in `.env` if you keep the templates elsewhere.

## Setup

```bash
git clone <this repo> job-apply
git clone <cv templates repo> cv     # sibling directory, see above
cd job-apply
uv sync

# Linux, macOS
curl -fsSL https://install.typst.community/install.sh | sh

# Windows (PowerShell)
irm https://install.typst.community/install.ps1 | iex
```

### Environment

Copy `.env.example` to `.env` and fill in your values:

```env
# Personal info (used in cover letter header)
FIRST_NAME=Jane
LAST_NAME=Doe
ADDRESS="123 Example St\nCity, Country"

# LLM settings
LLM_PROVIDER=google            # anthropic | google | openai
LLM_API_KEY=...
LLM_MODEL=gemini-3.5-flash
# LLM_PARSER_MODEL=gemini-3.5-flash-lite  # optional override for parsing
# LLM_GENERATOR_MODEL=gemini-4-argon      # optional override for generation
# LLM_URL=...                  # only for OpenAI-compatible endpoints (vLLM, Ollama, ...)

# Airtable settings
AIRTABLE_PAT=pat...            # airtable.com/create/tokens
AIRTABLE_BASE_ID=app...        # from the URL when viewing your base
# AIRTABLE_JOBS_TABLE=Jobs     # table names or IDs (tbl...)
# AIRTABLE_COMPANIES_TABLE=Companies
# AIRTABLE_CONTACTS_TABLE=Contacts

# Server settings
FASTAPI_HOST=localhost
FASTAPI_PORT=8000
# CLOUDFLARE_TUNNEL=my-tunnel  # named tunnel, started automatically on boot

# Token budgets
MAX_TOKENS_PARSER=8192         # parse echoes the posting verbatim, so this must be generous
MAX_TOKENS_GENERATOR=8192
```

`LLM_PROVIDER` selects which pydantic-ai provider is built; `LLM_URL` is only needed to point the OpenAI provider at a non-OpenAI endpoint.

### Personal context

Everything in `context/` goes into the system prompts for generating content, answering questions, and drafting emails, after each one's instructions and the shared rules in `prompts/writing_rules.md`.

```plaintext
context/
├── cover_letter_style.md    # tracked; themes, target sectors, things to avoid
└── personal/                # gitignored
    ├── cv.md
    └── work_at_cmac.md
```

`context/personal/` is excluded from version control, so a fresh clone has no CV to work from. The generator will still run, but the results will be generic and unusable; populate this directory first.

## Running locally

```powershell
uv run job-apply        # or: uv run main.py
```

You can verify the LLM configuration by visiting `http://localhost:8000/api/v0/models/check`. It performs a real round-trip and reports `ok`, latency, and the provider's own error text if the key, URL or model name is wrong.

If `CLOUDFLARE_TUNNEL` is set, the named tunnel starts with the app and stops with it (no second terminal needed). For an ad-hoc tunnel with a throwaway URL instead:

```powershell
cloudflared tunnel --url http://localhost:8000
```

## API reference

| Method   | Path                      | Description                                  |
| -------- | ------------------------- | -------------------------------------------- |
| GET      | `/api/v0/`                | App name, version, description               |
| GET      | `/api/v0/health`          | Liveness: `{"status": "ok"}`                 |
| GET      | `/api/v0/models`          | Configured provider and models               |
| GET      | `/api/v0/models/check`    | Live round-trip to verify LLM configuration  |
| GET      | `/api/v0/tasks`           | Background tasks currently running           |
| GET/POST | `/api/v0/parse`           | Pipeline 1: Parse job postings               |
| GET/POST | `/api/v0/generate`        | Pipeline 2: Generate CV intro & cover letter |
| GET/POST | `/api/v0/compile`         | Pipeline 3: Compile the PDF files            |
| POST     | `/api/v0/generate/answer` | Answer an application form question          |
| POST     | `/api/v0/generate/email`  | Draft a follow-up email for an application   |

The three pipelines return `202 Accepted` immediately and run in the background.

**POST** takes a JSON body; `parse` and `generate` accept an optional `model` override, `compile` accepts an optional `cv_style`:

```json
{ "record_id": "recXXXXXX", "model": "gemini-3.1-pro-preview" }
```

**GET** takes the same values as query parameters, used by Airtable button fields:

```plaintext
/api/v0/parse?record_id=recXXXXXX&model=gemini-3.5-flash
/api/v0/compile?record_id=recXXXXXX&cv_style=modern
```

`cv_style` is `classic` (default) or `modern`.

### `GET /api/v0/models/check`

```json
[
  {
    "ok": true,
    "provider": "google",
    "model": "gemini-3.5-flash",
    "url": null,
    "latency_ms": 1690,
    "reply": "pong",
    "error": null,
    "status_code": null
  }
]
```

On failure, `ok` is `false` and `error` carries the provider's message — a wrong model name returns `status_code: 404`, a bad key `401`, an unreachable URL a connection error.

### `POST /api/v0/generate/answer`

For the extra questions some application forms ask. Unlike the pipelines, it waits for the answer and returns it, ready to paste into the form. Put any length limit in the question itself; `record_id` is optional and tailors the answer to that job and its cover letter.

```json
{
  "question": "Why do you want to work here? (max 150 words)",
  "record_id": "recXXXXXX"
}
```

```json
{
  "question": "Why do you want to work here? (max 150 words)",
  "record_id": "recXXXXXX",
  "answer": "..."
}
```

If the personal context doesn't cover what the question asks, the answer starts with `NOTE:` and says what is missing instead.

### `POST /api/v0/generate/email`

Drafts a reminder to the job's contact, in case the application has not received an update. Like `answer`, it waits and returns the draft, ready to paste into your email client. The body is written from the job posting, its cover letter, the application `Date`, and the `prompt` (any extra points to make). It offers a short chat online, or in person when the job's `Address` or posting puts it in the same city as your `ADDRESS`. The subject is built from the job title and reference, so recruiters can find the application.

```json
{
  "prompt": "Mention I'm available for an interview from next week.",
  "record_id": "recXXXXXX"
}
```

```json
{
  "to_name": "Dr Smith",
  "to_address": "j.smith@example.com",
  "subject": "Application follow-up: Senior AI Engineer (REF-123) | Pooria Soltani",
  "body": "Dear Dr Smith,\n\n..."
}
```

`to_name` and `to_address` come from the job's linked contact, and are `null` if there isn't one.

### `GET /api/v0/tasks`

```json
{
  "running": true,
  "count": 1,
  "tasks": {
    "generate:recXXXXXX": {
      "description": "Generating content: Senior Data Scientist",
      "started_at": "2026-09-03T10:23:41+00:00"
    }
  }
}
```

## Airtable buttons

Add the following Button fields to the Jobs table, with the action set to _Open URL_ using the formula:

```plaintext
"https://your-host/api/v0/parse?record_id=" & RECORD_ID()
```

Repeat for `/generate` and `/compile`.

> If you use an ad-hoc `trycloudflare.com` tunnel, its URL changes every session and all three buttons need updating. A named tunnel or a deployed host avoids this.

## Workflow

1. Create a new Jobs record; paste the job URL into **AD**, or paste the text into **Notes**.
2. **Parse Job** → wait for the fields to fill in → review **Job**, **Type**, **Company**, **Notes**. Correct anything wrong.
3. **Generate Docs** → review **Letter Content**, **CV Content**, **Fitness**, and **Reasoning**. Edit to taste.
4. **Compile Docs** → two PDFs appear in **Docs**.

Watch `GET /api/v0/tasks` or `logs/app.log` while a pipeline runs.
