# Narrative Alpha — Demo Readiness Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Get the full pipeline running end-to-end for a demo — backend on published port 3001, dashboard accessible, progress visible via SSE streaming, one-command start.

**Architecture:** FastAPI backend (port 3001) + React/Vite dashboard (port 5173, proxied to 3001). Pipeline runs synchronously with 4 LLM calls (~5 min). SSE streaming provides progress checkpoints. The `start-demo.sh` script starts both processes.

**Tech Stack:** Python 3.11+ / FastAPI / uvicorn / SSE, TypeScript / React / Vite / EventSource

---

### Task 1: Fix dashboard proxy port

**Files:**
- Modify: `dashboard/vite.config.ts:11`

- [x] **Step 1: Verify current target**

Current: `target: "http://localhost:8000"`
Expected: `target: "http://localhost:3001"`

- [x] **Step 2: Change proxy target**

Change `8000` to `3001` in `dashboard/vite.config.ts`.

**Verification:** `grep 'localhost:3001' dashboard/vite.config.ts`

---

### Task 2: Write `start-demo.sh`

**Files:**
- Create: `start-demo.sh`

- [ ] **Step 1: Create start script**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Narrative Alpha Demo ==="
echo "Starting backend on port 3001 ..."
uvicorn narrative.server:app --host 0.0.0.0 --port 3001 &
BACKEND_PID=$!

sleep 2

echo "Starting dashboard on port 5173 ..."
cd dashboard && npm run dev &
DASHBOARD_PID=$!

echo ""
echo "Backend PID:  $BACKEND_PID  (http://localhost:3001)"
echo "Dashboard PID: $DASHBOARD_PID  (http://localhost:5173)"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $DASHBOARD_PID 2>/dev/null; exit" INT TERM
wait
```

- [ ] **Step 2: Make executable**

Run: `chmod +x start-demo.sh`

**Verification:** `./start-demo.sh` starts both services, Ctrl+C stops both.

---

### Task 3: Run pipeline E2E with low-volume keyword

**Goal:** Verify the full pipeline completes end-to-end with a real Bright Data SERP call.

- [ ] **Step 1: Start backend**

```bash
cd /project/narrative-alpha
source .env
export NARRATIVE_ALPHA_ROOT=/home/afshin/.narrative_alpha
uvicorn narrative.server:app --host 0.0.0.0 --port 3001
```

- [ ] **Step 2: Submit low-volume keyword first**

```bash
curl -X POST http://localhost:3001/api/pipeline \
  -H "Content-Type: application/json" \
  -d '{"keyword": "quantum computing startup funding 2026", "vertical": "TECHNOLOGY"}'
```

This keyword should produce fewer results (faster completion). Wait for response.

- [ ] **Step 3: If floor gate, try medium-volume keyword**

```bash
curl -X POST http://localhost:3001/api/pipeline \
  -H "Content-Type: application/json" \
  -d '{"keyword": "ai regulation", "vertical": "TECHNOLOGY"}'
```

- [ ] **Step 4: Verify report persisted**

```bash
curl http://localhost:3001/api/reports
```

Expected: JSON array with at least one report entry.

- [ ] **Step 5: Fetch report detail**

```bash
curl http://localhost:3001/api/reports/EVT-<ID>
```

Expected: Full ForensicReport with all fields populated.

**Verification:** Pipeline returns within 10 minutes, report has `distortion_matrix`, `outlier_signals`, `consensus_reality_graph`.

---

### Task 4: Add SSE progress streaming

**Files:**
- Modify: `narrative/server.py`
- Modify: `narrative/pipeline.py`
- Modify: `dashboard/src/api.ts`
- Modify: `dashboard/src/components/PipelineRunner.tsx`

**Architecture:**
- Backend: `POST /api/pipeline` returns immediately with a pipeline ID; a new `GET /api/pipeline/{id}/events` SSE endpoint streams progress.
- NOTE: This requires either an async pipeline (background thread + event store) or switching the POST handler to return `StreamingResponse` directly.
- 5 checkpoints: `discovering`, `ingesting`, `analyzing`, `synthesizing`, `complete` (or `error`).

**Decision point (Task 4A vs 4B):**

- **Option A (simpler):** Keep POST synchronous, return `StreamingResponse` with progress yielded inline. No background thread needed. Frontend switches from `fetchJson` to `EventSource` on a new GET endpoint.
- **Option B (proper):** POST returns `202 Accepted` with a `{pipeline_id}`, background thread runs pipeline, SSE endpoint polls event store. More robust but more code.

**Recommended: Option A** — the pipeline is already synchronous; wrapping it in a generator that yields SSE events is minimal work and sufficient for demo.

- [ ] **Step 1: Plan implementation approach**

Confirm Option A with user.

- [ ] **Step 2: Implement backend SSE**

```python
# server.py — new endpoint
from fastapi.responses import StreamingResponse

@app.post("/api/pipeline/stream")
async def run_pipeline_stream(payload: PipelineRequest):
    async def event_stream():
        yield f"data: {json.dumps({'step': 'discovering', 'message': 'Searching for articles...'})}\n\n"
        # ... run pipeline, yield events at each stage ...
        yield f"data: {json.dumps({'step': 'complete', 'cluster_id': ...})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 3: Implement frontend EventSource consumer**

```typescript
// api.ts — add streamPipeline function
export function streamPipeline(keyword: string, vertical: string, onEvent: (e: PipelineEvent) => void): EventSource {
  const params = new URLSearchParams({ keyword, vertical });
  const es = new EventSource(`/api/pipeline/stream?${params}`);
  es.onmessage = (msg) => onEvent(JSON.parse(msg.data));
  return es;
}
```

- [ ] **Step 4: Update PipelineRunner component**

Show progress bar or step indicator based on SSE events.

- [ ] **Step 5: Test with real pipeline run**

**Verification:** Dashboard shows "discovering → ingesting → analyzing → synthesizing → complete" progression.

---

### Task 5: Backtest (Phase 2, optional)

**Files:**
- Modify: `narrative/ingestion.py`
- Modify: `narrative/pipeline.py`

- [ ] **Step 1: Add `tbs` parameter to `discover_articles`**

```python
def discover_articles(keyword: str, api_key: str, serp_zone: str, tbs: str | None = None) -> dict:
    url = f"https://news.google.com/search?q={quote(keyword)}&hl=en-US&gl=US&ceid=US:en"
    if tbs:
        url += f"&tbs={tbs}"
    # ...
```

- [ ] **Step 2: Wire `tbs` through `_run_pipeline`**

`_run_pipeline` accepts optional `tbs` kwarg, passes to `discover_articles`.

- [ ] **Step 3: Add test**

Test that `tbs=qdr:w` (past week) is appended to the URL.

**Verification:** `curl` with `tbs=qdr:w` returns articles from the past week only.

---

## Verification Checklist

- [ ] `start-demo.sh` starts both backend and dashboard
- [ ] Dashboard loads at `http://localhost:5173`
- [ ] Pipeline POST returns a report (not floor gate)
- [ ] Report appears in `/api/reports` listing
- [ ] Dashboard proxy proxies correctly (check browser devtools)
- [ ] (Optional) SSE events visible in dashboard during pipeline run
