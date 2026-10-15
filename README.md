# job-apply

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

## 1. Setup

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

Everything in `context/` is concatenated into the generator's system prompt.

```plaintext
context/
├── cover_letter_style.md    # tracked; themes, target sectors, things to avoid
└── personal/                # gitignored
    ├── cv.md
    └── work_at_cmac.md
```

`context/personal/` is excluded from version control, so a fresh clone has no CV to work from. The generator will still run, but the results will be generic and unusable; populate this directory first.

## 2. Running locally

```powershell
uv run job-apply        # or: uv run main.py
```

You can verify the LLM configuration by visiting `http://localhost:8000/api/v0/model/check`. It performs a real round-trip and reports `ok`, latency, and the provider's own error text if the key, URL or model name is wrong.

If `CLOUDFLARE_TUNNEL` is set, the named tunnel starts with the app and stops with it (no second terminal needed). For an ad-hoc tunnel with a throwaway URL instead:

```powershell
cloudflared tunnel --url http://localhost:8000
```

## 3. API reference

| Method   | Path                  | Description                                            |
| -------- | --------------------- | ------------------------------------------------------ |
| GET      | `/api/v0/`            | App name, version, description                         |
| GET      | `/api/v0/health`      | Liveness — `{"status": "ok"}`                          |
| GET      | `/api/v0/model`       | Configured provider and model                          |
| GET      | `/api/v0/model/check` | Live round-trip to verify provider, model, URL and key |
| GET      | `/api/v0/tasks`       | Background tasks currently running                     |
| GET/POST | `/api/v0/parse`       | Pipeline 1                                             |
| GET/POST | `/api/v0/generate`    | Pipeline 2                                             |
| GET/POST | `/api/v0/compile`     | Pipeline 3                                             |

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

### `GET /api/v0/model/check`

```json
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
```

On failure, `ok` is `false` and `error` carries the provider's message — a wrong model name returns `status_code: 404`, a bad key `401`, an unreachable URL a connection error.

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

## 4. Airtable buttons

Add the following Button fields to the Jobs table, with the action set to _Open URL_ using the formula:

```plaintext
"https://your-host/api/v0/parse?record_id=" & RECORD_ID()
```

Repeat for `/generate` and `/compile`.

> If you use an ad-hoc `trycloudflare.com` tunnel, its URL changes every session and all three buttons need updating. A named tunnel or a deployed host avoids this.

## 5. The `Prompt` field

In the Jobs table, the `Prompt` field should be a Formula field combining all relevant columns. Example:

```plaintext
"--- New Job Application ---" &
"\n\n## Title: " & {Job} &
"\n## Employer: " & {Company} &
IF({LLM Notes}, "\n## LLM special prompt: " & {LLM Notes}) &
"\n## Description:\n" & {Notes} &
IF({Comp. Info}, "\n\n## Employer Description:\n" & {Comp. Info}) &
"\n\n--- End of Job Application ---"
```

Pipeline 2 reads this field directly as the user prompt to LLM.

Anything under a `## LLM special prompt` heading in the posting is treated as high-priority instructions by the generator.

## 6. Workflow

1. Create a new Jobs record; paste the job URL into **AD**, or paste the text into **Notes**.
2. **Parse Job** → wait for the fields to fill in → review **Job**, **Type**, **Company**, **Notes**. Correct anything wrong.
3. **Generate Docs** → review **Letter Content**, **CV Content**, **Fitness**, and **Reasoning**. Edit to taste.
4. **Compile Docs** → two PDFs appear in **Docs**.

Watch `GET /api/v0/tasks` or `logs/app.log` while a pipeline runs.
