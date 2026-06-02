# Narrative Alpha — Agent Instructions

## Startup

```bash
cd /project/narrative-alpha
source .venv/bin/activate
source .env
uvicorn narrative.server:app --host 0.0.0.0 --port 3001 &
cd dashboard && npm run dev
```

Backend API: `http://localhost:3001`
Dashboard: `http://localhost:3019`

## NARRATIVE_ALPHA_ROOT

This env var controls where reports, DB, and config are stored.
- Code default: `~/.narrative_alpha`
- This project's `.env` overrides it to `/project/narrative-alpha`
- `.env.example` leaves it commented out — only set it to override the default

If starting without `.env` sourced, data lives under `~/.narrative_alpha`.

## Known traps

- `pipeline.py`'s default was `/root/.narrative_alpha` (fixed — now matches `server.py` using `~/.narrative_alpha`)
- Starting the server without sourcing `.env` writes to a different data directory than previous runs — old reports won't appear
- Kill the server with `kill %<job-id>` or `pkill -f uvicorn`
