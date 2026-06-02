# Narrative Alpha — Agent Instructions

## Stack

- **Backend:** FastAPI (Python) — `narrative/server.py`
- **Frontend:** React + Vite — `dashboard/`
- **LLM:** DeepSeek (API keys in `.env`)
- **Scraping:** Bright Data (API keys in `.env`)
- **Storage:** SQLite outlet reputation DB + JSON report files under `NARRATIVE_ALPHA_ROOT`

## Startup

```bash
source .venv/bin/activate
source .env
uvicorn narrative.server:app --host 0.0.0.0 &
cd dashboard && npm run dev
```

Backend port is printed on startup; Vite picks dashboard port dynamically.

## NARRATIVE_ALPHA_ROOT

Controls where reports, DB, and config are stored. Code default: `~/.narrative_alpha`. Set in `.env` to override. `.env.example` leaves it commented out — only set to override.

If starting without `.env` sourced, data lives under `~/.narrative_alpha`.

## Known traps

- **Data directory mismatch:** Starting server without `.env` sourced writes to a different directory than previous runs — old reports won't appear. Always `source .env` first.
- **Kill server:** `kill %<job-id>` or `pkill -f uvicorn`
- **NARRATIVE_ALPHA_ROOT inconsistent:** All components must agree on the path. Check `backtest.py`, `pipeline.py`, and `server.py` if one reads a different directory.
