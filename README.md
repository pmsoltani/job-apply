# Airtable + Cloudflare Tunnel Setup

## 1. One-time environment setup

Copy `.env.example` to `.env` and fill in your keys:

```env
ANTHROPIC_API_KEY=sk-ant-...
AIRTABLE_PAT=pat...         # Personal Access Token from airtable.com/create/tokens
AIRTABLE_BASE_ID=app...         # From the URL when viewing your base
```

Install [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-local-tunnel/) (one-time):

```powershell
winget install Cloudflare.cloudflared
```

---

## 2. Starting the server (every session)

Open two terminals:

### Terminal 1 — API server

```powershell
cd path\to\job-apply
uv run job-apply
# or: uv run main.py
```

### Terminal 2 — Public tunnel

```powershell
cloudflared tunnel --url http://localhost:8000
```

Note the `https://xxxx.trycloudflare.com` URL printed by cloudflared.

---

## 3. Add two Button fields to the Jobs table

In Airtable → your base → Jobs table → **+** → Button:

| Setting | "Parse Job" button | "Generate Docs" button |
| --- | --- | --- |
| Label | Parse Job | Generate Docs |
| Action | Run automation | Run automation |
| Automation | (see step 4) | (see step 4) |

---

## 4. Create two Airtable Automations

Go to **Automations** (top right) → **+ New automation** for each:

### Automation A — "Parse Job"

| Step | Config |
| --- | --- |
| Trigger | **Button clicked** → select the "Parse Job" button field |
| Action | **Send a webhook** |
| URL | `https://xxxx.trycloudflare.com/ingest` |
| Method | POST |
| Body (JSON) | `{ "record_id": "{{ record.id }}" }` |

### Automation B — "Generate Docs"

Same as above but:

- Trigger: **Button clicked** → "Generate Docs" button
- URL: `https://xxxx.trycloudflare.com/generate`

> **Note**: update the tunnel URL in both automations each session (unless you configure a named tunnel with a fixed subdomain — see Cloudflare docs for persistent tunnels).

---

## 5. Update the Prompt formula (if not already set)

In the Jobs table, the `Prompt` field should be a Formula field combining all relevant columns. Example:

```plaintext
"--- New Job Application ---"&"\n\n"&
"Title: "&{Job}&"\n"&
"Company: "&{Company}&"\n"&
"AD: "&{AD}&"\n"&
"Notes to Gemini: "&{Gemini}&"\n"&
"Description:"&"\n"&
{Notes}&"\n\n"&
"--- End of Job Application ---"
```

Pipeline 2 reads this field directly as the user message to Claude.

---

## 6. Workflow

1. Create a new Jobs record; paste the job URL into **AD** (and/or paste the description into **Notes**).
2. Click **Parse Job** → wait ~10 seconds → review the populated fields (Job, Company, Notes). Edit anything incorrect.
3. Click **Generate Docs** → wait ~30 seconds → two PDFs appear in the **Docs** attachment field.
4. Download and review the PDFs, then apply.
