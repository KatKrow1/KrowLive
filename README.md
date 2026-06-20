# KrowLive

B2B lead intelligence platform for **Canada and Australia**, focused on media, marketing, advertising, and PR companies. KrowLive discovers businesses via Google Places, scrapes their websites for contact and social signals, enriches leads with Claude (or rule-based fallback), and stores results in Supabase for review in a Next.js dashboard.

## Tech stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12, FastAPI, Playwright, BeautifulSoup4, httpx, googlemaps, anthropic, supabase-py |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, framer-motion, recharts |
| Database | Supabase (PostgreSQL) |

## Prerequisites

- Python 3.12+
- Node.js 18+
- A Supabase project
- Google Places API key (Places API enabled)
- Anthropic API key (optional — enrichment falls back to rules if unset)

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
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Frontend setup

```powershell
cd frontend
npm install
copy .env.example .env.local
# Edit .env.local if backend is not on localhost:8000
npm run dev
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
| `ANTHROPIC_API_KEY` | No | Claude enrichment (optional) |
| `CORS_ORIGINS` | No | Allowed frontend origins (comma-separated) |
| `DEBUG` | No | Include tracebacks in JSON error responses |

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
.\venv\Scripts\uvicorn app.main:app --port 8000
```

**CORS / "Failed to fetch":** Ensure your frontend origin (e.g. `http://localhost:3000`) is listed in `CORS_ORIGINS` in `backend/.env`.
