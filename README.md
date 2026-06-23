# KrowLive

B2B lead intelligence platform for **Canada and Australia**, focused on media, marketing, advertising, and PR companies. KrowLive discovers businesses via Google Places, scrapes their websites for contact and social signals, enriches leads with rule-based scoring (or an optional custom AI provider), and stores results in Supabase for review in a Next.js dashboard.

## Tech stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12, FastAPI, Playwright, BeautifulSoup4, httpx, googlemaps, supabase-py |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, framer-motion, recharts |
| Database | Supabase (PostgreSQL) |

## Prerequisites

- Python 3.12+
- Node.js 18+
- A Supabase project
- Google Places API key (Places API enabled)
- Optional: custom enrichment API (see `ENRICHMENT_PROVIDER` below)

## Database setup (required before first use)

Run the full schema in Supabase **before** starting the backend:

1. Open your Supabase project → **SQL Editor** → New query
2. Paste and execute the contents of [`backend/app/sql/schema.sql`](backend/app/sql/schema.sql)

This creates `companies`, `executives`, and `jobs` tables with all columns in use (`social_links`, `tech_stack_signals`, `consent_status`, etc.) and seeds a single idle job row for progress tracking.

If you already have an older database, use the migration files in `backend/app/sql/` for incremental column adds.

## Backend setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\playwright install chromium
copy .env.example .env
# Edit .env with your keys
.\scripts\start-backend.ps1
# Or: .\venv\Scripts\uvicorn app.main:app --port 8000
```

API docs: http://localhost:8000/docs

## Frontend setup

```powershell
cd frontend
npm install
copy .env.example .env.local
# Edit .env.local if backend is not on localhost:8000
.\scripts\start-frontend.ps1
# Or: npm run dev
```

Dashboard: http://localhost:3000

Admin CSV upload (internal): http://localhost:3000/admin/upload

## Environment variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase API key |
| `GOOGLE_PLACES_API_KEY` | Yes | Google Places API key |
| `ENRICHMENT_PROVIDER` | No | `none` (default, rule-based), `ollama` (local LLM), or `custom` |
| `ENRICHMENT_API_KEY` | No | Bearer token for custom enrichment API |
| `ENRICHMENT_API_URL` | No | POST endpoint for custom enrichment |
| `OLLAMA_BASE_URL` | No | Ollama server URL (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | No | Live discovery model (default `llama3.1`) |
| `OLLAMA_TIMEOUT_SECONDS` | No | Per-call timeout for live pipeline (default `120`) |
| `OLLAMA_MAX_EXECUTIVE_CALLS` | No | Max Ollama exec refinements per company scrape (default `6`) |
| `OLLAMA_REFINEMENT_MODEL` | No | Model for `refine_existing_companies.py` only (default `qwen3`) |
| `OLLAMA_REFINEMENT_TIMEOUT_SECONDS` | No | Timeout for refinement script (default `420`) |
| `CORS_ORIGINS` | No | Allowed frontend origins (comma-separated) |
| `DEBUG` | No | Include tracebacks in JSON error responses |

### Enrichment providers

- **`none` (default):** Rule-based lead scoring from data completeness (email, phone, named contact, active site, Google rating, social links) plus a templated summary from scraped website text. No external AI call — zero latency, safe fallback if local LLM is too slow.
- **`ollama`:** Uses a local [Ollama](https://ollama.com) server for executive extraction and summary refinement during discovery.
  - **Live discovery** uses `OLLAMA_MODEL` (default **`llama3.1`**) — faster (~70s/call on CPU in testing).
  - **Occasional deep-clean** of existing rows: run `python scripts/refine_existing_companies.py` — uses `OLLAMA_REFINEMENT_MODEL` (default **`qwen3`**, slower but more thorough). Not used during `/discovery/run`.
  - On timeout or error, falls back to rule-based/heuristic results automatically.
  - `start-backend.ps1` checks Ollama is running and starts `ollama serve` if needed.
- **`custom`:** POSTs scraped signals to `ENRICHMENT_API_URL` with `Authorization: Bearer {ENRICHMENT_API_KEY}`. Expects JSON `{"summary": "...", "lead_score": 0-100}`. Falls back to rule-based on any failure.

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | No | Backend URL (default `http://localhost:8000`) |

## Key features

- **Discovery** — Search Google Places by industry and city (CA/AU), scrape websites, enrich, upsert to Supabase
- **Companies** — Paginated table with filters, lead scores, and detail drawer
- **Dashboard** — Stats and province/state chart
- **Admin CSV upload** — Re-upload datasets; upserts on `website` to refresh scraped data (not linked from main nav as a customer feature)

## Compliance note

Scraped contact data includes a `consent_status` field on executives. Verify consent before commercial email outreach under CASL (Canada) and the Spam Act (Australia).

## Troubleshooting

**500 on `/discovery/run` after code changes:** Restart uvicorn completely. On Windows, `--reload` can leave orphaned worker processes holding port 8000 with stale code. Kill all `python.exe` uvicorn workers, then start fresh:

```powershell
cd backend
.\venv\Scripts\uvicorn app.main:app --port 8000
```

Or use the startup script (kills stale port-8000 processes first, cleans up on Ctrl+C):

```powershell
.\scripts\start-backend.ps1              # stable, no reload
.\scripts\start-backend.ps1 -Reload      # auto-reload while editing Python
```

**CORS / "Failed to fetch":** Ensure your frontend origin (e.g. `http://localhost:3000`) is listed in `CORS_ORIGINS` in `backend/.env`.

**Orphaned uvicorn on Windows:** Avoid running the backend in Cursor/agent background shells — they can exit after ~5 minutes and leave the worker running. Use a normal terminal with `.\scripts\start-backend.ps1`. With `--reload`, uvicorn uses `multiprocessing.spawn`; if the parent reloader is killed without a clean shutdown, worker processes can survive detached. Prefer **no `--reload` for testing**; use `-Reload` only during active Python development.
