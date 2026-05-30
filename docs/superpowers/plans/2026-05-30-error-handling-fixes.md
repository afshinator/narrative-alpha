# Error Handling Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken error-handling chain across backend (FastAPI) and frontend (React/Vite) so that error messages include the real error detail from FastAPI's response body, pipeline crashes are caught gracefully, missing env vars return proper HTTP status codes, config endpoint uses Pydantic validation, path traversal is prevented, and all error paths have test coverage.

**Architecture:** Three issues compound: (1) Backend returns 500 with no detail when `_run_pipeline` crashes, or 200 with `{"status":"ERROR"}` for missing env vars; (2) `fetchJson` never reads response body on HTTP errors, discarding FastAPI's `{"detail":"..."}`; (3) SettingsPage silently renders fallback defaults when config fetch fails. Fixes are independent per layer — each task produces testable, deployable changes.

**Tech Stack:** Python 3.12+ / FastAPI / Pydantic / TestClient, TypeScript / React / Vite / Vitest / `@testing-library/react`

---

### Task 1: Fix `fetchJson` to read response body on HTTP errors + include request context

**Files:**
- Modify: `dashboard/src/api.ts:8-10`
- Modify: `dashboard/src/api.test.ts:13-17`

- [ ] **Step 1: Write test for error body reading**

Update the existing "throws on non-ok response" test to verify that the error body's `detail` field is included in the thrown message, AND that the URL/method appear:

```typescript
// api.test.ts — replace the "throws on non-ok response" test
it("includes response body detail in error message", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: false, status: 422, statusText: "Unprocessable Entity",
    json: () => Promise.resolve({ detail: "Missing required field: model" }),
  } as Response);
  const { fetchConfig } = await import("./api");
  await expect(fetchConfig()).rejects.toThrow("GET /api/config failed (422): Missing required field: model");
});

it("falls back to statusText when response body is not JSON", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: false, status: 500, statusText: "Internal Server Error",
    json: () => Promise.reject(new Error("not JSON")),
  } as Response);
  const { fetchReports } = await import("./api");
  await expect(fetchReports()).rejects.toThrow("GET /api/reports failed (500): Internal Server Error");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run dashboard/src/api.test.ts`
Expected: Both new tests fail with "expected to throw/not throw" (current implementation shows `statusText` only, no URL/method).

- [ ] **Step 3: Implement the fix in `fetchJson`**

Replace lines 8-10 in `dashboard/src/api.ts`:

```typescript
if (!res.ok) {
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail ?? JSON.stringify(body);
  } catch {
    // response body wasn't JSON, keep statusText
  }
  const method = init?.method ?? "GET";
  throw new Error(`${method} ${url} failed (${res.status}): ${detail}`);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run dashboard/src/api.test.ts`
Expected: All tests PASS (2 new + existing 3).

---

### Task 2: Add error boundary to `POST /api/pipeline` + fix 200-for-error

**Files:**
- Modify: `narrative/server.py:42-59`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write tests for pipeline error scenarios**

Add to `tests/test_server.py`:

```python
def test_pipeline_rejects_missing_env_vars(client):
    """POST /api/pipeline returns 503 when env vars are missing."""
    from narrative.server import app as _  # ensure app loaded
    resp = client.post("/api/pipeline", json={"keyword": "test", "vertical": "TECHNOLOGY"})
    assert resp.status_code == 503
    data = resp.json()
    assert "detail" in data
    assert "BRIGHTDATA_API_KEY" in data["detail"]


def test_pipeline_returns_500_on_crash(client):
    """POST /api/pipeline returns 500 when _run_pipeline raises."""
    import narrative.server as srv
    original = srv._run_pipeline

    def crashing_run(*args, **kwargs):
        raise RuntimeError("BrightData timeout")

    srv._run_pipeline = crashing_run
    try:
        resp = client.post("/api/pipeline", json={"keyword": "test", "vertical": "TECHNOLOGY"})
        assert resp.status_code == 500
        assert "error" in resp.json()
    finally:
        srv._run_pipeline = original
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_server.py::test_pipeline_rejects_missing_env_vars tests/test_server.py::test_pipeline_returns_500_on_crash -v`
Expected: First test fails (status 200, not 503). Second test fails (status 500 is returned by FastAPI's default handler, but the response body won't match — or the test helper itself fails).

Note: The crash test `test_pipeline_returns_500_on_crash` uses monkey-patching because `_run_pipeline` is imported by name in `server.py` (`from narrative.pipeline import _run_pipeline`). The patching mutates the module directly. An alternative is to use `unittest.mock.patch.object(srv, '_run_pipeline', ...)` — but since `_run_pipeline` is imported at the top level of `server.py`, `srv._run_pipeline` refers to the module attribute, and `patch.object` won't intercept the local reference inside `execute_pipeline`. The monkey-patch approach above is the simplest working solution.

- [ ] **Step 3: Implement the fix in `server.py`**

Replace lines 42-59 in `narrative/server.py`:

```python
@app.post("/api/pipeline")
def execute_pipeline(payload: PipelinePayload) -> dict:
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")

    if not api_key or not unlocker_zone:
        raise HTTPException(
            status_code=503,
            detail="BRIGHTDATA_API_KEY and BRIGHTDATA_UNLOCKER_ZONE environment variables must be set"
        )

    db_path = os.path.join(_narrative_root(), "outlet_reputation.db")

    try:
        report = _run_pipeline(payload.keyword, payload.vertical, api_key, unlocker_zone, db_path)
    except Exception:
        logger.exception("Pipeline execution failed")
        return JSONResponse(
            status_code=500,
            content={"error": "Pipeline execution failed. Check server logs for details."}
        )

    cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
    os.makedirs(_reports_dir(), exist_ok=True)
    report_path = os.path.join(_reports_dir(), f"{cluster_id}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report
```

Add the missing imports at the top of `server.py`:

```python
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_server.py -v`
Expected: All 16+ tests PASS (14 original + 2 new).

---

### Task 3: Fix SettingsPage error state on fetch failure

**Files:**
- Modify: `dashboard/src/components/SettingsPage.tsx`
- Modify: `dashboard/src/components/SettingsPage.test.tsx`

- [ ] **Step 1: Write test for fetch-failure error state**

Add to `dashboard/src/components/SettingsPage.test.tsx`:

```typescript
it("shows error message when fetch fails", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Failed to load config"));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText(/Failed to load config/)).toBeTruthy();
});

it("disables save button when config failed to load", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network error"));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  // Wait for loading to finish
  await screen.findByText(/Network error/);
  // Save button should not be rendered since we show an error page instead
  expect(screen.queryByText("Save Configuration")).toBeNull();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run dashboard/src/components/SettingsPage.test.tsx`
Expected: New tests fail or timeout — current component always renders the settings table and Save button even when `fetchConfig` fails.

- [ ] **Step 3: Implement the fix in `SettingsPage.tsx`**

Replace the `saveStatus` / `loading` / error handling in `SettingsPage.tsx`:

```typescript
import { useState, useEffect } from "react";
import type { LLMConfig, LLMSlotConfig } from "../types";
import { SettingsRow } from "./SettingsRow";
import { fetchConfig, saveConfig } from "../api";

const SLOTS: { key: keyof LLMConfig; name: string; description: string }[] = [
  { key: "call_1_entity_normalization", name: "Call 1", description: "Entity normalization" },
  { key: "call_2_linguistic_neutralization", name: "Call 2", description: "Linguistic neutralization" },
  { key: "call_3_graph_extraction", name: "Call 3", description: "Graph extraction" },
  { key: "call_4_forensic_synthesis", name: "Call 4", description: "Forensic synthesis" },
];

export function SettingsPage() {
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig()
      .then(setConfig)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleUpdate = (key: keyof LLMConfig, updates: Partial<LLMSlotConfig>) => {
    setConfig((prev) => {
      if (!prev) return prev;
      return { ...prev, [key]: { ...prev[key], ...updates } };
    });
  };

  const handleSave = async () => {
    if (!config) return;
    setSaveStatus("Saving…");
    try {
      const result = await saveConfig(config);
      setSaveStatus(result.status === "ok" ? "Saved" : `Error: ${result.status}`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setSaveStatus(`Save failed: ${msg}`);
    }
  };

  if (loading) return <div className="page settings-page"><p className="loading">Loading config…</p></div>;
  if (error) return <div className="page settings-page"><p className="error">Error: {error}</p></div>;
  if (!config) return <div className="page settings-page"><p className="empty">No configuration loaded.</p></div>;

  return (
    <div className="page settings-page">
      <h2 className="section-title">LLM Configuration</h2>
      <p className="section-subtitle">
        Configure per-slot LLM providers and parameters for the forensic pipeline.
        Defaults are loaded from the backend.
      </p>

      <div className="settings-table">
        <div className="settings-header">
          <div>Call Slot</div>
          <div>Provider</div>
          <div>Model</div>
          <div>Temperature</div>
          <div>Thinking</div>
        </div>

        {SLOTS.map(({ key, name, description }) => (
          <SettingsRow
            key={key}
            slotName={name}
            slotDescription={description}
            provider={config[key].provider}
            model={config[key].model}
            thinking={config[key].thinking}
            temperature={config[key].temperature}
            onUpdate={(updates) => handleUpdate(key, updates)}
          />
        ))}
      </div>

      <div className="settings-actions">
        <button className="btn-save" onClick={handleSave}>Save Configuration</button>
        {saveStatus && <span className="save-status">{saveStatus}</span>}
      </div>
    </div>
  );
}
```

The key changes:
- `saveStatus` is no longer used for load errors — a dedicated `error` state is used
- On fetch failure, the component renders an error banner instead of the settings table
- When `!config`, a fall-through guard returns an empty-state message
- The `??` fallbacks are removed since `config` is guaranteed non-null before rendering the table

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run dashboard/src/components/SettingsPage.test.tsx`
Expected: All 6 tests PASS (existing 4 + 2 new).

---

### Task 4: Switch `POST /api/config` to Pydantic `LLMConfig`

**Files:**
- Modify: `narrative/server.py:103-123`
- No test changes needed — existing tests cover the same validation paths

**Ambiguity note:** The existing `test_settings_rejects_invalid_slot_structure` sends `{"provider": "openai"}` for `call_1_entity_normalization`. `LLMSlotConfig` requires only `provider` and `model`, so `model` being absent triggers a `ValidationError`. This test passes as-is with the Pydantic change. No existing test covers extra field rejection; the `_Strict` base with `extra="forbid"` will now additionally reject unknown keys. This is a net improvement.

- [ ] **Step 1: Write test for extra field rejection**

Add to `tests/test_server.py`:

```python
def test_post_config_rejects_unknown_fields(client):
    """POST /api/config returns 422 for extra fields not in LLMConfig."""
    payload = {
        "call_1_entity_normalization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
        "call_2_linguistic_neutralization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
        "call_3_graph_extraction": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
        "call_4_forensic_synthesis": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
        "extra_field": "should_not_be_allowed",
    }
    resp = client.post("/api/config", json=payload)
    assert resp.status_code == 422
```

- [ ] **Step 2: Run the new test to verify it fails (with current `dict` endpoint)**

Run: `python -m pytest tests/test_server.py::test_post_config_rejects_unknown_fields -v`
Expected: FAIL — currently accepts extra fields silently.

- [ ] **Step 3: Modify `update_config` to use `LLMConfig`**

Replace lines 103-123 in `narrative/server.py`:

```python
from pydantic import ValidationError

@app.post("/api/config")
def update_config(payload: LLMConfig) -> dict:
    config = payload.model_dump()
    with open(_config_path(), "w") as f:
        json.dump(config, f, indent=2)
    return {"status": "ok", "config": config}
```

This replaces the manual slot-check loop and the `except Exception` block with FastAPI's built-in Pydantic validation. When `LLMConfig(**payload)` fails (missing slot, invalid slot structure, extra field), FastAPI returns 422 with a detailed error message automatically.

- [ ] **Step 4: Run all config test_server tests**

Run: `python -m pytest tests/test_server.py -v`
Expected: All 19+ tests PASS (14 original + 2 pipeline + 2 settings + 1 extra_field). The existing tests that posted invalid config (`test_post_config_rejects_missing_slot`, `test_settings_rejects_invalid_slot_structure`) now get their 422 from FastAPI's auto-validation rather than the manual loop — same result, same status code.

---

### Task 5: Add path traversal guard on `GET /api/reports/{cluster_id}`

**Files:**
- Modify: `narrative/server.py:89-95`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write test for path traversal rejection**

Add to `tests/test_server.py`:

```python
def test_get_report_rejects_path_traversal(client):
    """GET /api/reports/../../etc/passwd returns 400."""
    resp = client.get("/api/reports/../../etc/passwd")
    assert resp.status_code == 400
    assert "Invalid cluster_id" in resp.json()["detail"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_server.py::test_get_report_rejects_path_traversal -v`
Expected: FAIL — currently accepts the path traversal.

- [ ] **Step 3: Add guard to `get_report`**

Replace lines 89-95 in `narrative/server.py`:

```python
@app.get("/api/reports/{cluster_id}")
def get_report(cluster_id: str) -> dict:
    if "/" in cluster_id or ".." in cluster_id or "\\" in cluster_id:
        raise HTTPException(status_code=400, detail="Invalid cluster_id")
    report_path = os.path.join(_reports_dir(), f"{cluster_id}.json")
    if not os.path.isfile(report_path):
        raise HTTPException(status_code=404, detail={"error": f"Report {cluster_id} not found"})
    with open(report_path) as f:
        return json.load(f)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_server.py -v`
Expected: All tests PASS.

---

## Self-Review

### Spec (review document) coverage:

| Finding | Task |
|---------|------|
| 🔴 `fetchJson` discards response body | Task 1 |
| 🔴 Pipeline has no error handling | Task 2 |
| 🔴 Missing env vars return 200 OK | Task 2 (same endpoint) |
| 🟡 SettingsPage silent defaults | Task 3 |
| 🟡 `POST /api/config` uses bare `dict` | Task 4 |
| 🟡 Over-broad `except Exception` | Task 4 (eliminated by Pydantic switch) |
| 🟡 Path traversal risk | Task 5 |
| 🟡 Error messages lack request context | Task 1 (combined with body fix) |
| No test for pipeline missing env vars | Task 2 |
| No test for pipeline crash | Task 2 |
| No test: fetchJson body on error | Task 1 |
| No test: SettingsPage fetch-failure | Task 3 |
| No test: path traversal rejection | Task 5 |

### Placeholder check:
No "TBD", "TODO", "implement later", or "similar to above" patterns found.

### Type consistency:
- `fetchJson` now returns `Error(`${method} ${url} failed (${status}): ${detail}`)` — all callers catch `e: Error` and use `e.message`. Compatible.
- `POST /api/pipeline` now returns `JSONResponse(status_code=500, content={...})` on error instead of bare dict. Callers already handle non-2xx via `fetchJson`.
- `POST /api/config` now takes `LLMConfig` instead of `dict`. The existing tests send the same JSON structure. Compatible.
- `get_report` now checks cluster_id before file ops. Callers already pass it via `encodeURIComponent`. Compatible.

### Task independence check:
All 5 tasks are independent — they touch different files and functions. They can be executed in any order.
