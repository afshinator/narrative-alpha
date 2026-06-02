# Narrative Alpha — Agent Instructions

## Stack

- **Backend:** FastAPI (Python) — `narrative/server.py`
- **Frontend:** React + Vite — `dashboard/`
- **LLM:** DeepSeek (API keys in `.env`)
- **Scraping:** Bright Data (API keys in `.env`)
- **Storage:** SQLite outlet reputation DB + JSON report files under `NARRATIVE_ALPHA_ROOT`

## Startup

```bash
source .env   # load API keys into shell
.venv/bin/uvicorn narrative.server:app --host 0.0.0.0 --port 8000 &
cd dashboard && VITE_BACKEND_PORT=8000 npm run dev
```

Or use `./start-demo.sh`, which handles venv setup, dependency checks, and both processes.

Port env vars:

| Var | Effect |
|---|---|
| `BACKEND_PORT` | uvicorn listen port (default `8000`) |
| `PORT` | Vite listen port (default `5173`) |
| `VITE_BACKEND_PORT` | Port the frontend proxies `/api` to (defaults to `BACKEND_PORT`) |

If the venv is missing or broken (e.g. after moving the repo), rebuild it:

```bash
uv venv --python 3.11 --clear && uv pip install -r requirements.txt
```

## NARRATIVE_ALPHA_ROOT

Controls where reports, DB, and config are stored. Code default: project root directory (the repo root). Reports land under `data/reports/`. Set in `.env` to override.

## Known traps

- **Kill server:** `kill %<job-id>` or `pkill -f uvicorn`
- **NARRATIVE_ALPHA_ROOT inconsistent:** All components must agree on the path. Check `backtest.py`, `pipeline.py`, and `server.py` if one reads a different directory.
