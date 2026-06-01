# Unknown Cluster ID — Debug & Fix Plan

**Bug symptom:** Pipeline that hits the corpus floor gate (<5 articles) produces a
`unknown.json` report file, sends a "complete" SSE event with `cluster_id: "unknown"`,
navigates the frontend to `/event/unknown`, and the EventPage crashes with a white
screen because the floor gate response lacks `event_meta`.

---

## Verified Root Cause Chain

### 🔍 Finding 1 — Floor gate return lacks cluster_id
**File:** `narrative/ingestion.py` lines 359–365

`build_ingestion_manifest()` computes `cluster_id` at line 315 but the floor gate
return dict (lines 359-365) omits it. The response only has `status` and
`validation_tracking`:

```python
return {
    "status": "INSUFFICIENT_CORPUS_FLOOR",
    "validation_tracking": {
        "current_state": "INSUFFICIENT_CORPUS_FLOOR",
        "minimum_required": 5,
        "current_count": corpus_count,
    },
}
```

No `cluster_id`, no `search_query`, no `event_meta`.

### 🔍 Finding 2 — POST handler doesn't detect floor gates
**File:** `narrative/server.py` lines 98–100

After `_run_pipeline_with_timeout()` returns, the code reads:
```python
cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
```
The floor gate dict has no `event_meta` → `cluster_id = "unknown"`.
Then saves the file as `unknown.json`.

### 🔍 Finding 3 — SSE handler has the same gap
**File:** `narrative/server.py` lines 182–187

Same code pattern:
```python
report = pipeline_future.result()
cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
os.makedirs(_reports_dir(), exist_ok=True)
with open(...) as f:
    json.dump(report, f, indent=2)
yield f"data: {json.dumps({'step': 'complete', ... 'cluster_id': cluster_id})}\n\n"
```

Floor gate → `cluster_id = "unknown"` → writes `unknown.json` → sends `step: "complete"`
with `cluster_id: "unknown"`.

### 🔍 Finding 4 — Frontend EventPage crashes on missing event_meta
**File:** `dashboard/src/components/EventPage.tsx` lines 22–24

```tsx
<h1 className="page-title">{report.event_meta.cluster_id}</h1>
<p className="page-subtitle">{report.event_meta.search_query}</p>
```

When `report` is a floor gate response (no `event_meta`), this throws:
`Cannot read properties of undefined (reading 'cluster_id')` → React crash → white screen.

### 🔍 Finding 5 — PipelineRunner treats "unknown" as valid
**File:** `dashboard/src/components/PipelineRunner.tsx` line 193

```tsx
if (event.cluster_id) {
```
`"unknown"` is truthy, so the block executes — saves to sessionStorage and navigates.

---

## Error UX Audit

Every error state a user could encounter and what they currently see:

| Scenario | Current UX | Verdict |
|----------|-----------|---------|
| Floor gate (<5 articles) | White screen → `/event/unknown` | **Broken** — no feedback at all |
| Pipeline failure (LLM error, etc.) | "Pipeline failed: {traceback detail}" | **Terse** — technical jargon, no guidance |
| Missing env vars | "Server misconfigured: BRIGHTDATA_API_KEY..." | **OK** — clear what's missing |
| Backend unreachable | "Backend unreachable (POST ...). Ensure server on port 3001." | **Good** — specific and actionable |
| Timeout (POST handler only) | "Pipeline execution timed out" | **Terse** — no explanation or suggested retry |
| Timeout (SSE — no timeout at all) | Pipeline silently hangs, no error | **Broken** — user has no feedback |

The root fix (Fixes 1–4) addresses the crash/link bugs. Fixes 5–7 improve the
messages so users understand what happened and what to do next.

---

## Fixes

### Fix 1 — Add cluster_id to floor gate response
**File:** `narrative/ingestion.py` lines 359–365

Add `cluster_id` and `search_query` to the floor gate return dict so downstream
code can identify what query failed.

```python
return {
    "status": "INSUFFICIENT_CORPUS_FLOOR",
    "cluster_id": cluster_id,
    "search_query": keyword,
    "validation_tracking": {
        "current_state": "INSUFFICIENT_CORPUS_FLOOR",
        "minimum_required": 5,
        "current_count": corpus_count,
    },
}
```

### Fix 2 — POST handler returns floor gate as 4xx
**File:** `narrative/server.py` lines 92–97

Detect floor gates before trying to save as reports. Return a 422 with the
floor gate details and a clear message.

```python
report = _run_pipeline_with_timeout(...)

# Floor gate — return as validation error, don't save
if "validation_tracking" in report:
    count = report.get("validation_tracking", {}).get("current_count", 0)
    raise HTTPException(
        status_code=422,
        detail={
            "error": f"Not enough unique news sources — only got {count}, need at least 5. Try a broader keyword.",
            "floor_gate": report,
        },
    )

cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
...
```

### Fix 3 — SSE handler sends error for floor gates (with clear message)
**File:** `narrative/server.py` lines 180–187

After getting the pipeline result, check for floor gate and send an error
event with a user-friendly message instead of saving a report.

```python
report = pipeline_future.result()

# Floor gate — send error, don't save file
if "validation_tracking" in report:
    count = report.get("validation_tracking", {}).get("current_count", 0)
    yield f"data: {json.dumps({
        'step': 'error',
        'message': f'Not enough unique news sources — only got {count}, need at least 5. Try a broader keyword.',
        'detail': report,
    })}\n\n"
    return

cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
...
```

### Fix 4 — Guard EventPage against missing event_meta
**File:** `dashboard/src/components/EventPage.tsx` lines 22–24

Use optional chaining so the page doesn't crash even if a non-report response
reaches the EventPage (defense in depth).

```tsx
<h1 className="page-title">{report.event_meta?.cluster_id ?? "Report"}</h1>
{report.event_meta?.search_query && (
    <p className="page-subtitle">{report.event_meta.search_query}</p>
)}
```

### Fix 5 — Improve pipeline timeout message
**File:** `narrative/server.py` line 84

The timeout message currently says "Pipeline execution timed out" with the
exception as detail. Improve it to explain what happened and that retrying
is fine.

```python
except TimeoutError as e:
    logger.error("Pipeline timed out")
    return JSONResponse(
        status_code=504,
        content={
            "error": "Pipeline took too long to complete.",
            "detail": "This can happen when many outlets need reputations checked for the first time. Try again — subsequent runs are faster once outlet data is cached.",
        },
    )
```

### Fix 6 — Improve generic pipeline failure message in SSE handler
**File:** `narrative/server.py` lines 188–191

The generic exception path sends the raw exception string as the detail.
Wrap it in a user-friendly message while preserving the technical detail
for debugging.

```python
exc = pipeline_future.exception()
if exc:
    logger.exception("Pipeline stream failed", exc_info=exc)
    yield f"data: {json.dumps({
        'step': 'error',
        'message': 'Pipeline failed during processing.',
        'detail': f'Something went wrong while analyzing articles. The server logs have more details. Error: {exc}',
    })}\n\n"
    return
```

---

## Verification Steps

| Step | Command | Expected |
|------|---------|----------|
| 1 | `cd dashboard && npx vitest run` | All JS tests pass |
| 2 | `cd dashboard && npx tsc --noEmit` | Clean TypeScript |
| 3 | `pytest tests/ -v` | All Python tests pass |
| 4 | Manually: trigger pipeline with keyword returning <5 articles | SSE shows error event with plain-English floor message; homepage shows error banner (no link) |
| 5 | Manually: trigger pipeline with keyword returning ≥5 articles | Normal completion, navigates to valid `/event/EVT-...` |
| 6 | Manually: clear sessionStorage, navigate directly to `/event/unknown` | EventPage shows "Report not found" or error, not white screen |
| 7 | Manually: trigger pipeline that times out (if possible) | Error message mentions retry + caching |
| 8 | Manually: trigger pipeline that fails mid-way (kill server) | Error message is plain English, not a raw traceback |
