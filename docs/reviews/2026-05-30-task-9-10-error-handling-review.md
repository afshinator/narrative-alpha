# Adversarial Review — Task 9 & 10 Error Handling

**Date:** 2026-05-30
**Scope:** `narrative/server.py`, `dashboard/src/api.ts`, `dashboard/src/components/HomePage.tsx`,
`dashboard/src/components/EventPage.tsx`, `dashboard/src/components/SettingsPage.tsx`,
`dashboard/src/api.test.ts`, `dashboard/src/components/SettingsPage.test.tsx`

**Reviewer:** opencode

---

## Summary

The "Error: API 500: Internal Server Error" complaint has a single root cause at
`api.ts:9`: `fetchJson` reads `statusText` on HTTP errors but **never reads the
response body**. FastAPI always sends `{"detail": "..."}` with the real
explanation (validation errors, missing env vars, file-not-found, pipeline
crashes). That body is discarded — the user sees the generic HTTP status text
instead.

The problem compounds through all three layers: backend unhandled exceptions,
frontend fetch stripping the body, and components rendering raw HTTP text. Below
are all findings organized by severity.

---

## Blocking Issues

### 🔴 `fetchJson` discards response body — `dashboard/src/api.ts:8-10`

`fetchJson` throws `Error(\`API ${res.status}: ${res.statusText}\`)` but never
calls `res.json()` or `res.text()` on error responses. FastAPI always returns
`{"detail": "human-readable explanation"}` in the body — this is where useful
information lives. `statusText` for a 500 is always the generic `"Internal
Server Error"`.

**Fix:** Attempt to parse the error body and include it:

```typescript
if (!res.ok) {
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail ?? JSON.stringify(body);
  } catch {
    // response body wasn't JSON, keep statusText
  }
  throw new Error(`API ${res.status}: ${detail}`);
}
```

This single change fixes the error messages in **all three consumer components**
(HomePage, EventPage, SettingsPage) at once.

---

### 🔴 `POST /api/pipeline` has no error handling — `narrative/server.py:42-59`

`_run_pipeline()` can crash in many real ways (network timeout from BrightData,
DB connection error, `KeyError` in a malformed report dict, file I/O failure).
None are caught. FastAPI returns a bare 500 with `{"detail": "Internal Server
Error"}` — no log, no context for the user.

```python
@app.post("/api/pipeline")
def execute_pipeline(payload: PipelinePayload) -> dict:
    ...
    try:
        report = _run_pipeline(payload.keyword, payload.vertical, api_key, unlocker_zone, db_path)
    except Exception:
        logger.exception("Pipeline execution failed")
        return JSONResponse(status_code=500, content={"error": "Pipeline execution failed. Check server logs."})
```

---

### 🔴 Missing env vars returns 200 OK — `narrative/server.py:47-48`

When `BRIGHTDATA_API_KEY` or `BRIGHTDATA_UNLOCKER_ZONE` are not set, the
endpoint returns `{"status": "ERROR", "error": "..."}` with **HTTP 200 OK**.
This is semantically wrong — 200 means success. The frontend treats 200 as
success and parses the body as a `ForensicReport`. If a component later
accesses `report.event_meta.cluster_id`, it crashes with a confusing error.

The same problem applies to any other runtime error from `_run_pipeline()`.

**Fix:** Use an appropriate HTTP error status:

```python
if not api_key or not unlocker_zone:
    raise HTTPException(
        status_code=503,
        detail="BRIGHTDATA_API_KEY and BRIGHTDATA_UNLOCKER_ZONE environment variables must be set"
    )
```

---

## Suggestions

### 🟡 SettingsPage silently falls back to defaults on fetch failure — `dashboard/src/components/SettingsPage.tsx:18-22`

When `fetchConfig` fails, the error is stored in `saveStatus` (a state variable
meant for save-confirmation display), but the component still renders the full
settings table populated entirely with fallback defaults (`?? "deepseek"`, `?? ""`,
`?? false`, `?? 0.1`). The user sees what looks like a valid config. If they click
"Save", they silently overwrite the real config on the server with defaults.

The error message is also rendered next to the Save button (line 79), but it's
visually low-prominence and could be missed.

**Fix:** Use a dedicated `error` state (same pattern as HomePage/EventPage).
Show an error banner and disable the Save button until config loads
successfully:

```typescript
if (error) return <div className="page settings-page"><p className="error">{error}</p></div>;
```

---

### 🟡 `POST /api/config` uses bare `dict` instead of Pydantic model — `narrative/server.py:104`

```python
def update_config(payload: dict) -> dict:
```

FastAPI cannot auto-validate the request shape or generate accurate OpenAPI docs
from `dict`. The manual slot-validation loop on lines 111-118 is fragile — if
a new slot is added to `LLMConfig` but not to `required_slots`, the endpoint
silently accepts partial configs.

`LLMConfig` in `contracts.py` is already a Pydantic `BaseModel`, so it can be
used directly:

```python
from narrative.contracts import LLMConfig

@app.post("/api/config")
def update_config(payload: LLMConfig) -> dict:
    with open(_config_path(), "w") as f:
        json.dump(payload.model_dump(), f, indent=2)
    return {"status": "ok", "config": payload.model_dump()}
```

This eliminates the manual validation loop entirely — Pydantic handles required
fields, types, and constraints (`temperature: ge=0.0, le=2.0`).

---

### 🟡 Over-broad `except Exception` — `narrative/server.py:117`

```python
try:
    LLMConfig(**payload)
except Exception as e:
    raise HTTPException(status_code=422, detail=f"Invalid config: {e}")
```

This catches `NameError`, `ImportError`, `KeyError`, and other programming
bugs — anything inheriting from `Exception` — that should never be silently
converted to 422. (Note: `KeyboardInterrupt` and `SystemExit` inherit from
`BaseException` and are NOT caught by `except Exception`, so those are not at
risk.)

**Fix:** Catch only `ValidationError` from Pydantic:

```python
from pydantic import ValidationError

try:
    LLMConfig(**payload)
except ValidationError as e:
    raise HTTPException(status_code=422, detail=f"Invalid config: {e}")
```

---

### 🟡 Path traversal risk on `GET /api/reports/{cluster_id}` — `narrative/server.py:91`

```python
report_path = os.path.join(_reports_dir(), f"{cluster_id}.json")
```

An attacker can pass `cluster_id=../../etc/passwd` to read arbitrary `.json`
files from the filesystem. While the `.json` suffix limits the blast radius,
`smtp.json`, `nginx.json`, or config files could leak.

**Fix:** Reject suspicious paths:

```python
if "/" in cluster_id or ".." in cluster_id or "\\" in cluster_id:
    raise HTTPException(status_code=400, detail="Invalid cluster_id")
```

---

### 🟡 Error messages lack request context — `dashboard/src/api.ts:9`

The error says `"API 500: Internal Server Error"` but doesn't include which
endpoint or HTTP method failed. A user with multiple tabs or API calls in
flight can't tell which request errored.

**Fix** (combined with the body-reading fix above):

```typescript
const method = init?.method ?? "GET";
throw new Error(`${method} ${url} failed (${res.status}): ${detail}`);
```

---

## Missing Test Coverage

| Gap | File | Impact |
|-----|------|--------|
| No test for `POST /api/pipeline` when env vars missing | `test_server.py` | Regression not caught |
| No test for `POST /api/pipeline` when `_run_pipeline` raises | `test_server.py` | Crash not caught |
| No test that `fetchJson` reads response body on HTTP error | `api.test.ts` | Error enrich fix unprotected |
| No test for `SettingsPage` fetch-failure error state | `SettingsPage.test.tsx` | Silent-defaults bug unprotected |
| No test for HTTP 500 response in `HomePage` (network rejection tested) | `HomePage.test.tsx` | HTTP 500 not covered specifically |
| No test for HTTP 500 response in `EventPage` (network rejection tested) | `EventPage.test.tsx` | HTTP 500 not covered specifically |
| No test for path traversal rejection | `test_server.py` | Security gap unprotected |

---

## Positives

- The `fetchJson` abstraction is clean and makes the body-reading fix
  impactful — one change in api.ts propagates to all consumers.
- Components consistently separate `loading` / `error` / `empty` / `data`
  states (though error messages are currently opaque).
- FastAPI lifespan pattern and endpoint structure are well-organized.
- Backend test suite has good coverage of success paths.
- `LLMConfig` is already a proper Pydantic model — switching from `dict` to
  typed parameter is a small, safe change.

---

## Verdict

**Needs significant changes.** The error handling chain has a well-defined
broken link at each layer — backend catches nothing → HTTP 500 with bare
`{"detail":"Internal Server Error"}` → `fetchJson` strips error body →
component shows raw HTTP text. Each layer independently amplifies the problem.

### Recommended fix order

1. **`api.ts` — read response body on error** (highest leverage, fixes all
   three components' error messages at once)
2. **`server.py` — wrap `_run_pipeline()` in try/except** (prevents bare 500s)
3. **`server.py` — return 503 for missing env vars** (fixes semantic contract)
4. **`SettingsPage.tsx` — show error state instead of silent defaults**
5. **`server.py` — switch `POST /api/config` to typed Pydantic parameter**
6. **`server.py` — add path traversal guard on `cluster_id`**
7. **Backfill missing tests** from the coverage table above
