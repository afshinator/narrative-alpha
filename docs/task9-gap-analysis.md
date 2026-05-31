> **Historical design document.** The architecture decisions discussed here were resolved during
> implementation: the dashboard became a React/Vite SPA fetching from local FastAPI REST endpoints
> (`GET /api/reports`, `GET /api/reports/{cluster_id}`). Reports are stored as JSON files under
> `~/.narrative_alpha/data/reports/` and served via the FastAPI server.

# Task 9 — Dashboard Gap Analysis

**Date:** 2026-05-30

## Architectural Gaps

### 1. How does the dashboard get its JSON data?

The spec says data should be "stored as static `.json` files in a `/data/{cluster_id}.json` path."
But nothing in the plan creates or serves these files, and the original Modal endpoint writes
reports to a volume, not a served directory.

*Resolution: FastAPI serves reports via `/api/reports` and `/api/reports/{cluster_id}` REST endpoints.*

**Options:**
- **A.** Fetch from Modal endpoint URL directly (needs CORS + hardcoded URL)
- **B.** Hard-code sample JSON in the HTML/JS (no backend dependency)
- **C.** Generate `data/clusters.json` + `data/{id}.json` from sample data alongside `index.html`

### 2. Static files vs dynamic routing

Plan specifies `index.html` (cluster list) and `event.html` (per-cluster report). As plain
static files, `event.html` can't display a specific cluster without JS extracting
`?cluster_id=` from the URL.

The existing `docs/preview-01.html` (539 lines) uses a single-page SPA with tab navigation.
This avoids routing and page reloads.

**Options:**
- **A.** SPA model (single `index.html`, hash-based routing) — matches preview
- **B.** Multi-file approach (3 HTML pages, full page reloads) — matches plan

### 3. Settings page POST URL

Settings form needs to POST to the Modal endpoint. A static file doesn't know its
deployment URL. For demo: must be hardcoded (e.g., `https://app.modal.run`).

---

## Plan Inconsistencies

| # | Issue |
|---|-------|
| 4 | File count wrong: plan says "4 files" but lists 5 (style.css, index.html, event.html, settings.html, app.js) |
| 5 | Steps 2-6 are all TBD with parenthetical descriptions but no concrete code |
| 6 | Temperature slider missing: spec §9.4 requires temperature slider per slot; preview has none |
| 7 | Thinking toggle visibility: spec says "only renders for DeepSeek"; preview doesn't implement show/hide |
| 8 | Corpus-capped indicator: app.py injects `event_meta.corpus_capped` but dashboard spec §11 and preview don't display it |
| 9 | Preview file `docs/preview-01.html` not referenced as a starting point |

---

## Spec Compliance Gaps

| # | Gap |
|---|-----|
| 10 | No pulsing CSS animation for UNRESOLVED convergence status (spec requires it) |
| 11 | Temperature slider absent from settings form (spec §9.4) |
| 12 | Thinking toggle visibility not linked to provider dropdown (spec §9.4) |

---

## Implementation Constraints

| # | Constraint |
|---|-----------|
| 13 | No build step, no frameworks — vanilla JS + CSS only |
| 14 | CORS: current `app.py` `fastapi_endpoint` doesn't set CORS headers |
| 15 | Preview has no corpus-capped indicator — needs to be surfaced in Zone 1 event meta |
