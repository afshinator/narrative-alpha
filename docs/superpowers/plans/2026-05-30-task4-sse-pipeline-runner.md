# Task 4: SSE Progress Streaming + PipelineRunner UI

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a `PipelineRunner` component to the dashboard's home page with a keyword input, vertical selector, and submit button. The backend exposes a `GET /api/pipeline/stream` SSE endpoint that yields progress events at each pipeline stage. The frontend consumes events via `EventSource` and renders step-by-step progress inline on `HomePage`.

**Architecture:** Option A — no background thread, no pipeline ID. Frontend opens an `EventSource` to `GET /api/pipeline/stream?keyword=...&vertical=...`. The backend handler runs `_run_pipeline` inside `asyncio.get_running_loop().run_in_executor` and yields SSE progress events at each stage boundary using a shared `queue.SimpleQueue`. On `complete`, the client navigates to the new report.

**Tech Stack:** FastAPI `StreamingResponse` + `asyncio` + `queue.SimpleQueue` (Python), TypeScript `EventSource` (browser native), React state machine for progress display.

---

## File Map

| File | Status | Responsibility |
|------|--------|----------------|
| `narrative/server.py` | Modify | Add `GET /api/pipeline/stream` endpoint with `StreamingResponse` |
| `narrative/pipeline.py` | Modify | Add optional `progress_cb` parameter to `_run_pipeline` |
| `dashboard/src/api.ts` | Modify | Add `streamPipeline()` function; keep `submitPipeline` unchanged |
| `dashboard/src/components/PipelineRunner.tsx` | Create | Keyword input + vertical selector + submit + progress display |
| `dashboard/src/components/PipelineRunner.test.tsx` | Create | Component tests for all UI states |
| `dashboard/src/components/HomePage.tsx` | Modify | Mount `PipelineRunner` above the report list |
| `dashboard/src/components/HomePage.test.tsx` | Modify | Add `PipelineRunner` mock so existing tests don't break |
| `dashboard/src/types.ts` | Modify | Add `PipelineEvent` and `PipelineStep` types |
| `dashboard/vite.config.ts` | Modify | Increase proxy timeout from 120s to 900s |
| `tests/test_server.py` | Modify | Add 3 SSE endpoint tests |
| `dashboard/src/api.test.ts` | Modify | Add `streamPipeline` tests |

---

## OPEN DECISIONS AND AMBIGUITIES

**OPEN DECISION 1 — EventSource is GET-only.**
`EventSource` is a browser API that only supports GET requests. The demo plan's Step 3 code snippet uses `new EventSource('/api/pipeline/stream?keyword=...&vertical=...')`, confirming that keyword and vertical must travel as query parameters, not a POST body. This plan follows that approach. The existing `submitPipeline` in `api.ts` sends a POST to `/api/pipeline`; it is a different (non-streaming) call and is **kept unchanged**.

**OPEN DECISION 2 — Async pipeline execution strategy.**
`_run_pipeline` is a long-running synchronous function (up to 10 minutes). The SSE endpoint must be an `async def` handler to yield events without blocking the event loop. This plan uses `asyncio.get_running_loop().run_in_executor(None, ...)` to run `_run_pipeline` in a thread, with a `queue.SimpleQueue` passed as the `progress_cb` channel. The async generator polls the queue with `asyncio.sleep(0.5)` between drains.

Alternative (`asyncio.to_thread`) also works but requires structuring the progress queue the same way — no meaningful difference for this use case.

**OPEN DECISION 3 — Pipeline stage mapping.**
`_run_pipeline` has 7 internal steps but the spec defines 5 SSE checkpoints. The proposed mapping:
- `discovering` → emitted before STEP 1 (discover_articles)
- `ingesting` → emitted before STEP 2 (build_ingestion_manifest)
- `analyzing` → emitted before STEP 4 (entity normalization; covers steps 3–6 internally)
- `synthesizing` → emitted before STEP 7 (forensic synthesis)
- `complete` → emitted by the SSE handler after report is written to disk

STEP 3 (outlet registration, ~instant) folds into `analyzing`. Confirmed — 5 checkpoints are sufficient for the demo.

**OPEN DECISION 4 — `progress_cb` integration approach.**
`_run_pipeline` receives an optional `progress_cb: Optional[Callable[[str, str], None]] = None`. It is called inline at each stage boundary. This is backward-compatible: all existing callers (including the synchronous `POST /api/pipeline` endpoint and all tests) pass no `progress_cb` and are unaffected.

**OPEN DECISION 5 — Where `PipelineRunner` appears in the UI.**
This plan renders `PipelineRunner` at the top of `HomePage` (Option A: no new route, no modal). After `complete`, the component calls `useNavigate` to navigate to `/event/:clusterId`. If a separate nav tab or modal is preferred, `App.tsx` would need a new `Route` and `NavLink` — that is not in scope here.

**AMBIGUITY 1 — Auto-navigation vs. manual click after `complete`.**
This plan auto-navigates via `useNavigate` when `complete` fires. If the user prefers to stay on `HomePage` and click the new report card, the `navigate` call should be removed from `PipelineRunner` and only `onComplete` (which re-fetches the report list) should run. **Decision needed before implementation.**

**AMBIGUITY 2 — Vite proxy timeout.**
The current proxy config sets `proxyTimeout: 120_000` and `timeout: 120_000` (2 minutes). A full pipeline run with Call 3 on DeepSeek Flash takes ~7-8 minutes (was 13.9 min with Pro thinking). This plan increases both to `900_000` (15 minutes) to match the backend `NARRATIVE_PIPELINE_TIMEOUT` default. SSE buffering through Vite's `http-proxy` is not expected to be an issue (it pipes chunks as they arrive), but the implementer must verify in-browser that events appear incrementally, not all at once, using DevTools → Network → EventStream tab.

**AMBIGUITY 3 — `VERTICALS` list.**
The backend accepts any string for `vertical`. This plan hardcodes `["TECHNOLOGY", "FINANCE", "POLITICS", "HEALTH", "ENTERTAINMENT"]` in the dropdown. The implementer should confirm this is the correct set, or fetch it from the backend.

**AMBIGUITY 4 — Error event shape.**
The demo plan mentions `error` as a terminal checkpoint but does not define its fields. This plan uses `{ step: "error", message: string, detail?: string }` where `detail` carries the server-side exception text.

**AMBIGUITY 5 — `serp_zone` env var (RESOLVED).**
The `execute_pipeline` endpoint was updated (pre-Task 4) to now validate `BRIGHTDATA_SERP_ZONE` alongside `api_key` and `unlocker_zone`. The streaming endpoint **must match** — it should read `serp_zone` from `BRIGHTDATA_SERP_ZONE` and include it in the credential check. The error message should also mention `BRIGHTDATA_SERP_ZONE`.

---

## SSE Event Shape (Canonical Definition)

Every SSE `data:` line is a single JSON object:

```json
{ "step": "<PipelineStep>", "message": "<string>", "cluster_id"?: "<string>", "detail"?: "<string>" }
```

| Field | Present on | Type | Description |
|-------|-----------|------|-------------|
| `step` | all events | `PipelineStep` | Machine-readable stage identifier |
| `message` | all events | `string` | Human-readable status string |
| `cluster_id` | `complete` only | `string` | Cluster ID of the new report; used for navigation |
| `detail` | `error` only | `string` | Server exception text |

No `event:` field is used — all events use the default `data:` type, handled by `EventSource.onmessage`.

---

## Step-by-Step Implementation

### Step 1: Add `PipelineEvent` and `PipelineStep` types

**File:** `dashboard/src/types.ts`

Append to the bottom of the file:

```typescript
export type PipelineStep =
  | "discovering"
  | "ingesting"
  | "analyzing"
  | "synthesizing"
  | "complete"
  | "error";

export interface PipelineEvent {
  step: PipelineStep;
  message: string;
  cluster_id?: string;  // present on step === "complete"
  detail?: string;      // present on step === "error"
}
```

- [ ] **Step 1.1:** Add `PipelineStep` and `PipelineEvent` exports to `dashboard/src/types.ts`.

**Verification:** `cd dashboard && npx tsc --noEmit`
Expected: No errors.

---

### Step 2: Add `streamPipeline` to `api.ts`

**File:** `dashboard/src/api.ts`

Import `PipelineEvent` from `./types`. Add the new function after `submitPipeline` (keep `submitPipeline` unchanged):

```typescript
export function streamPipeline(
  keyword: string,
  vertical: string,
  onEvent: (e: PipelineEvent) => void,
  onError: (err: Event) => void,
): EventSource {
  const params = new URLSearchParams({ keyword, vertical });
  const es = new EventSource(`/api/pipeline/stream?${params.toString()}`);
  es.onmessage = (msg: MessageEvent) => {
    try {
      onEvent(JSON.parse(msg.data) as PipelineEvent);
    } catch {
      // malformed event — ignore
    }
  };
  es.onerror = onError;
  return es;
}
```

- [ ] **Step 2.1:** Add `streamPipeline` export to `dashboard/src/api.ts`.
- [ ] **Step 2.2:** Add `streamPipeline` tests to `dashboard/src/api.test.ts`:

```typescript
describe("streamPipeline", () => {
  it("constructs EventSource with correct URL", async () => {
    const fakeEs = { onmessage: null, onerror: null } as unknown as EventSource;
    const MockEs = vi.fn(() => fakeEs);
    vi.stubGlobal("EventSource", MockEs);
    const { streamPipeline } = await import("./api");
    streamPipeline("ai regulation", "TECHNOLOGY", vi.fn(), vi.fn());
    expect(MockEs).toHaveBeenCalledWith(
      "/api/pipeline/stream?keyword=ai+regulation&vertical=TECHNOLOGY"
    );
    vi.unstubAllGlobals();
  });

  it("calls onEvent with parsed JSON when message arrives", async () => {
    const fakeEs: any = { onmessage: null, onerror: null };
    vi.stubGlobal("EventSource", vi.fn(() => fakeEs));
    const onEvent = vi.fn();
    const { streamPipeline } = await import("./api");
    streamPipeline("test", "TECHNOLOGY", onEvent, vi.fn());
    fakeEs.onmessage({ data: '{"step":"discovering","message":"Searching..."}' });
    expect(onEvent).toHaveBeenCalledWith({ step: "discovering", message: "Searching..." });
    vi.unstubAllGlobals();
  });

  it("returns the EventSource so the caller can close it", async () => {
    const fakeEs = { onmessage: null, onerror: null };
    vi.stubGlobal("EventSource", vi.fn(() => fakeEs));
    const { streamPipeline } = await import("./api");
    const es = streamPipeline("test", "TECHNOLOGY", vi.fn(), vi.fn());
    expect(es).toBe(fakeEs);
    vi.unstubAllGlobals();
  });
});
```

**Verification:** `cd dashboard && npx vitest run src/api.test.ts`
Expected: All previous tests pass + 3 new ones.

---

### Step 3: Add `progress_cb` to `_run_pipeline`

**File:** `narrative/pipeline.py`

Add `Optional` and `Callable` to imports:
```python
from typing import Callable, Optional
```

Change the `_run_pipeline` signature:
```python
def _run_pipeline(
    keyword: str,
    vertical: str,
    api_key: str,
    unlocker_zone: str,
    serp_zone: str,
    db_path: str,
    progress_cb: Optional[Callable[[str, str], None]] = None,
) -> dict:
```

Insert calls at stage boundaries (only if `progress_cb` is not None):

- Before STEP 1: `if progress_cb: progress_cb("discovering", "Searching for articles...")`
- Before STEP 2: `if progress_cb: progress_cb("ingesting", "Fetching article content...")`
- Before STEP 4: `if progress_cb: progress_cb("analyzing", "Running entity and graph analysis...")`
- Before STEP 7: `if progress_cb: progress_cb("synthesizing", "Generating forensic report...")`

The `complete` event is emitted by the SSE handler (server.py), not by `_run_pipeline`, since the cluster_id comes from the returned report dict.

- [ ] **Step 3.1:** Add `Optional[Callable[[str, str], None]] = None` parameter `progress_cb` to `_run_pipeline`.
- [ ] **Step 3.2:** Insert four `if progress_cb:` calls at the boundaries above.

**Verification:** `pytest tests/test_server.py -v`
Expected: All existing tests pass unchanged (no `progress_cb` is passed in any existing test mock).

---

### Step 4: Add `GET /api/pipeline/stream` to `server.py`

**File:** `narrative/server.py`

Add imports at the top (if not already present):
```python
import asyncio
import queue
from fastapi.responses import StreamingResponse
```

Add the new endpoint after `execute_pipeline`:

```python
@app.get("/api/pipeline/stream")
async def stream_pipeline(keyword: str, vertical: str = "TECHNOLOGY"):
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")
    serp_zone = os.environ.get("BRIGHTDATA_SERP_ZONE", "")

    if not api_key or not unlocker_zone or not serp_zone:
        async def _error_stream():
            yield f"data: {json.dumps({'step': 'error', 'message': 'Server misconfigured', 'detail': 'Missing BrightData credentials (check API_KEY, SERP_ZONE, UNLOCKER_ZONE)'})}\n\n"
        return StreamingResponse(_error_stream(), media_type="text/event-stream")

    progress_q: queue.SimpleQueue = queue.SimpleQueue()

    def _progress_cb(step: str, message: str) -> None:
        progress_q.put((step, message))

    db_path = os.path.join(_narrative_root(), "outlet_reputation.db")

    async def event_stream():
        yield ": ping\n\n"  # flush headers so proxy doesn't buffer

        loop = asyncio.get_running_loop()
        pipeline_future = loop.run_in_executor(
            None,
            lambda: _run_pipeline(
                keyword, vertical, api_key, unlocker_zone, serp_zone, db_path,
                progress_cb=_progress_cb,
            ),
        )

        done = False
        while not done:
            while True:
                try:
                    step, message = progress_q.get_nowait()
                    yield f"data: {json.dumps({'step': step, 'message': message})}\n\n"
                except queue.Empty:
                    break

            if pipeline_future.done():
                done = True
            else:
                await asyncio.sleep(0.5)

        # drain any events posted before done was detected
        while True:
            try:
                step, message = progress_q.get_nowait()
                yield f"data: {json.dumps({'step': step, 'message': message})}\n\n"
            except queue.Empty:
                break

        exc = pipeline_future.exception()
        if exc:
            logger.exception("Pipeline stream failed", exc_info=exc)
            yield f"data: {json.dumps({'step': 'error', 'message': 'Pipeline failed', 'detail': str(exc)})}\n\n"
            return

        report = pipeline_future.result()
        cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
        os.makedirs(_reports_dir(), exist_ok=True)
        with open(os.path.join(_reports_dir(), f"{cluster_id}.json"), "w") as f:
            json.dump(report, f, indent=2)

        yield f"data: {json.dumps({'step': 'complete', 'message': 'Report ready', 'cluster_id': cluster_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 4.1:** Add `asyncio`, `queue`, `StreamingResponse` imports to `narrative/server.py`.
- [ ] **Step 4.2:** Add `GET /api/pipeline/stream` endpoint as above.
- [ ] **Step 4.3:** Confirm existing `POST /api/pipeline` endpoint is untouched.

**Verification:**
```bash
pytest tests/test_server.py -v
```
Expected: All existing tests pass.

```bash
grep "pipeline/stream" narrative/server.py
```
Expected: Finds the new endpoint decorator.

---

### Step 5: Add SSE endpoint tests to `tests/test_server.py`

**File:** `tests/test_server.py`

Add the following three tests at the bottom. `TestClient` supports streaming with `stream=True`:

```python
def test_stream_pipeline_missing_env_returns_error_event():
    """GET /api/pipeline/stream yields error SSE event when env vars missing."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative"}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        with tc.stream("GET", "/api/pipeline/stream?keyword=test&vertical=TECHNOLOGY") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body = resp.text
    assert "error" in body


def test_stream_pipeline_yields_progress_and_complete():
    """GET /api/pipeline/stream yields all progress events and complete from mocked pipeline."""
    import narrative.server as srv

    fake_report = {
        "event_meta": {
            "cluster_id": "EVT-SSE-001", "search_query": "test",
            "industry_vertical": "TECHNOLOGY", "timestamp_utc": "now",
            "corpus_count": 3, "corpus_capped": False,
        },
        "distortion_matrix": [], "outlier_signals": [],
        "consensus_reality_graph": {"consensus_summary": "", "verified_anchor_nodes": [], "primary_verifications": []},
        "reputation_warnings": [], "reality_divergence_zones": [],
        "reality_fractures": [], "narrative_regime_shifts": [],
    }

    def fake_pipeline(keyword, vertical, api_key, unlocker_zone, serp_zone, db_path, progress_cb=None):
        if progress_cb:
            progress_cb("discovering", "Searching...")
            progress_cb("ingesting", "Fetching...")
            progress_cb("analyzing", "Analyzing...")
            progress_cb("synthesizing", "Synthesizing...")
        return fake_report

    env = {
        "NARRATIVE_ALPHA_ROOT": "/tmp/test_sse",
        "BRIGHTDATA_API_KEY": "key",
        "BRIGHTDATA_UNLOCKER_ZONE": "zone",
        "BRIGHTDATA_SERP_ZONE": "serp",
    }
    original = srv._run_pipeline
    srv._run_pipeline = fake_pipeline
    try:
        with patch.dict(os.environ, env, clear=True):
            from narrative.server import app
            tc = TestClient(app)
            with tc.stream("GET", "/api/pipeline/stream?keyword=test&vertical=TECHNOLOGY") as resp:
                assert resp.status_code == 200
                body = resp.text
        for step in ("discovering", "ingesting", "analyzing", "synthesizing", "complete", "EVT-SSE-001"):
            assert step in body
    finally:
        srv._run_pipeline = original


def test_stream_pipeline_yields_error_on_crash():
    """GET /api/pipeline/stream yields error SSE event when pipeline raises."""
    import narrative.server as srv

    def crashing_pipeline(*args, **kwargs):
        raise RuntimeError("BrightData timeout")

    env = {
        "NARRATIVE_ALPHA_ROOT": "/tmp/test_sse_err",
        "BRIGHTDATA_API_KEY": "key",
        "BRIGHTDATA_UNLOCKER_ZONE": "zone",
        "BRIGHTDATA_SERP_ZONE": "serp",
    }
    original = srv._run_pipeline
    srv._run_pipeline = crashing_pipeline
    try:
        with patch.dict(os.environ, env, clear=True):
            from narrative.server import app
            tc = TestClient(app)
            with tc.stream("GET", "/api/pipeline/stream?keyword=test&vertical=TECHNOLOGY") as resp:
                assert resp.status_code == 200
                body = resp.text
        assert "error" in body
    finally:
        srv._run_pipeline = original
```

- [ ] **Step 5.1:** Add the three SSE tests to `tests/test_server.py`.

**Verification:**
```bash
pytest tests/test_server.py -v -k "stream"
```
Expected: 3 new tests pass.

```bash
pytest tests/test_server.py -v
```
Expected: All tests pass (no regressions).

---

### Step 6: Create `PipelineRunner.tsx`

**File:** `dashboard/src/components/PipelineRunner.tsx`

```typescript
import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import type { PipelineEvent, PipelineStep } from "../types";
import { streamPipeline } from "../api";

const VERTICALS = ["TECHNOLOGY", "FINANCE", "POLITICS", "HEALTH", "ENTERTAINMENT"];

const STEP_LABELS: Record<PipelineStep, string> = {
  discovering: "Discovering articles",
  ingesting:   "Ingesting content",
  analyzing:   "Analyzing narratives",
  synthesizing:"Synthesizing report",
  complete:    "Complete",
  error:       "Error",
};

type RunnerState = "idle" | "running" | "complete" | "error";

export function PipelineRunner({ onComplete }: { onComplete?: () => void }) {
  const [keyword, setKeyword]         = useState("");
  const [vertical, setVertical]       = useState("TECHNOLOGY");
  const [runnerState, setRunnerState] = useState<RunnerState>("idle");
  const [steps, setSteps]             = useState<PipelineEvent[]>([]);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const esRef                         = useRef<EventSource | null>(null);
  const navigate                      = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyword.trim() || runnerState === "running") return;

    setSteps([]);
    setErrorDetail(null);
    setRunnerState("running");

    esRef.current = streamPipeline(
      keyword.trim(),
      vertical,
      (event: PipelineEvent) => {
        setSteps((prev) => [...prev, event]);
        if (event.step === "complete") {
          esRef.current?.close();
          setRunnerState("complete");
          onComplete?.();
          if (event.cluster_id) navigate(`/event/${event.cluster_id}`);
        } else if (event.step === "error") {
          esRef.current?.close();
          setRunnerState("error");
          setErrorDetail(event.detail ?? event.message);
        }
      },
      (_err: Event) => {
        esRef.current?.close();
        setRunnerState("error");
        setErrorDetail("Connection to server lost.");
      },
    );
  };

  return (
    <div className="pipeline-runner">
      <form className="pipeline-form" onSubmit={handleSubmit}>
        <input
          className="pipeline-keyword-input"
          type="text"
          placeholder="Enter keyword (e.g. AI regulation)"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          disabled={runnerState === "running"}
          required
        />
        <select
          className="pipeline-vertical-select"
          value={vertical}
          onChange={(e) => setVertical(e.target.value)}
          disabled={runnerState === "running"}
        >
          {VERTICALS.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <button
          type="submit"
          className="pipeline-submit-btn"
          disabled={runnerState === "running" || !keyword.trim()}
        >
          {runnerState === "running" ? "Running…" : "Run Pipeline"}
        </button>
      </form>

      {steps.length > 0 && (
        <div className="pipeline-progress" role="status" aria-live="polite">
          {steps.map((evt, i) => (
            <div key={i} className={`pipeline-step pipeline-step--${evt.step}`}>
              <span className="step-label">{STEP_LABELS[evt.step] ?? evt.step}</span>
              <span className="step-message">{evt.message}</span>
            </div>
          ))}
        </div>
      )}

      {runnerState === "error" && errorDetail && (
        <p className="pipeline-error">Pipeline failed: {errorDetail}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 6.1:** Create `dashboard/src/components/PipelineRunner.tsx`.

**Verification:** `cd dashboard && npx tsc --noEmit`
Expected: No errors.

---

### Step 7: Create `PipelineRunner.test.tsx`

**File:** `dashboard/src/components/PipelineRunner.test.tsx`

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PipelineRunner } from "./PipelineRunner";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return { ...actual, streamPipeline: vi.fn() };
});

import { streamPipeline } from "../api";

beforeEach(() => { vi.clearAllMocks(); });

function renderRunner(onComplete?: () => void) {
  return render(<MemoryRouter><PipelineRunner onComplete={onComplete} /></MemoryRouter>);
}

describe("PipelineRunner — idle", () => {
  it("renders keyword input, vertical selector, and submit button", () => {
    renderRunner();
    expect(screen.getByPlaceholderText(/Enter keyword/i)).toBeTruthy();
    expect(screen.getByRole("combobox")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Run Pipeline/i })).toBeTruthy();
  });

  it("disables submit when keyword is empty", () => {
    renderRunner();
    const btn = screen.getByRole("button", { name: /Run Pipeline/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("enables submit when keyword is typed", () => {
    renderRunner();
    fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), { target: { value: "AI regulation" } });
    const btn = screen.getByRole("button", { name: /Run Pipeline/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });
});

describe("PipelineRunner — running", () => {
  it("calls streamPipeline with keyword and vertical on submit", () => {
    vi.mocked(streamPipeline).mockReturnValue({ close: vi.fn() } as unknown as EventSource);
    renderRunner();
    fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), { target: { value: "ai" } });
    fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
    expect(streamPipeline).toHaveBeenCalledWith("ai", "TECHNOLOGY", expect.any(Function), expect.any(Function));
  });

  it("shows Running… and disables inputs during run", () => {
    vi.mocked(streamPipeline).mockReturnValue({ close: vi.fn() } as unknown as EventSource);
    renderRunner();
    fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), { target: { value: "ai" } });
    fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
    expect(screen.getByRole("button", { name: /Running/i })).toBeTruthy();
    expect((screen.getByPlaceholderText(/Enter keyword/i) as HTMLInputElement).disabled).toBe(true);
  });

  it("renders progress steps as events arrive", () => {
    let capturedOnEvent: ((e: any) => void) | null = null;
    vi.mocked(streamPipeline).mockImplementation((_kw, _v, onEvent) => {
      capturedOnEvent = onEvent;
      return { close: vi.fn() } as unknown as EventSource;
    });
    renderRunner();
    fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), { target: { value: "ai" } });
    fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
    capturedOnEvent!({ step: "discovering", message: "Searching..." });
    expect(screen.getByText(/Discovering articles/i)).toBeTruthy();
    capturedOnEvent!({ step: "ingesting", message: "Fetching..." });
    expect(screen.getByText(/Ingesting content/i)).toBeTruthy();
  });
});

describe("PipelineRunner — error", () => {
  it("shows error detail from error event", () => {
    let capturedOnEvent: ((e: any) => void) | null = null;
    vi.mocked(streamPipeline).mockImplementation((_kw, _v, onEvent) => {
      capturedOnEvent = onEvent;
      return { close: vi.fn() } as unknown as EventSource;
    });
    renderRunner();
    fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), { target: { value: "ai" } });
    fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
    capturedOnEvent!({ step: "error", message: "Pipeline failed", detail: "BrightData timeout" });
    expect(screen.getByText(/BrightData timeout/i)).toBeTruthy();
  });

  it("shows connection lost on onerror", () => {
    let capturedOnError: ((e: Event) => void) | null = null;
    vi.mocked(streamPipeline).mockImplementation((_kw, _v, _onEvent, onError) => {
      capturedOnError = onError;
      return { close: vi.fn() } as unknown as EventSource;
    });
    renderRunner();
    fireEvent.change(screen.getByPlaceholderText(/Enter keyword/i), { target: { value: "ai" } });
    fireEvent.click(screen.getByRole("button", { name: /Run Pipeline/i }));
    capturedOnError!(new Event("error"));
    expect(screen.getByText(/Connection to server lost/i)).toBeTruthy();
  });
});
```

- [ ] **Step 7.1:** Create `dashboard/src/components/PipelineRunner.test.tsx`.

**Verification:** `cd dashboard && npx vitest run src/components/PipelineRunner.test.tsx`
Expected: All 8 tests pass.

---

### Step 8: Update `HomePage.tsx` to mount `PipelineRunner`

**File:** `dashboard/src/components/HomePage.tsx`

Replace the current content with:

```typescript
import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import type { ClusterSummary } from "../types";
import { fetchReports } from "../api";
import { PipelineRunner } from "./PipelineRunner";

export function HomePage() {
  const [reports, setReports]   = useState<ClusterSummary[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const loadReports = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchReports()
      .then(setReports)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadReports(); }, [loadReports]);

  return (
    <div className="page">
      <PipelineRunner onComplete={loadReports} />

      {loading && <p className="loading">Loading reports…</p>}
      {error && <p className="error">Error: {error}</p>}
      {!loading && !error && reports.length === 0 && (
        <p className="empty">No reports yet. Run a pipeline to get started.</p>
      )}
      {!loading && !error && reports.length > 0 && (
        <>
          <h1 className="page-title">Forensic Reports</h1>
          <div className="report-list">
            {reports.map((r) => (
              <Link key={r.cluster_id} to={`/event/${r.cluster_id}`} className="report-card">
                <h2>{r.search_query}</h2>
                <p className="report-meta">{r.industry_vertical} · {r.corpus_count} articles · {r.timestamp_utc}</p>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 8.1:** Replace `dashboard/src/components/HomePage.tsx` with the above.
- [ ] **Step 8.2:** Add `PipelineRunner` mock to `dashboard/src/components/HomePage.test.tsx` so existing tests don't break:

```typescript
vi.mock("./PipelineRunner", () => ({
  PipelineRunner: (_props: any) => <div data-testid="pipeline-runner-stub" />,
}));
```

Add this at the top of the test file (after imports, before tests). Accepting `_props` ensures the mock won't break if `HomePage` starts passing additional props to `PipelineRunner`.

**Verification:** `cd dashboard && npx vitest run src/components/HomePage.test.tsx`
Expected: All 4 existing tests pass.

---

### Step 9: Increase Vite proxy timeout

**File:** `dashboard/vite.config.ts`

Change `proxyTimeout` and `timeout` from `120_000` to `900_000` (15 minutes — matches backend `NARRATIVE_PIPELINE_TIMEOUT`):

```typescript
proxy: {
  "/api": {
    target: "http://localhost:3001",
    changeOrigin: true,
    proxyTimeout: 900_000,
    timeout: 900_000,
  },
},
```

- [ ] **Step 9.1:** Update both timeout values in `dashboard/vite.config.ts`.

**Verification:**
```bash
grep 'proxyTimeout\|timeout' dashboard/vite.config.ts
```
Expected: Both show `900_000`.

---

### Step 10: Full verification

- [ ] **Step 10.1:** Full Python test suite.

```bash
pytest tests/ -v
```
Expected: All existing tests pass + 3 new SSE tests.

- [ ] **Step 10.2:** Full frontend test suite.

```bash
cd dashboard && npx vitest run
```
Expected: All existing tests pass + 8 new `PipelineRunner` tests + 3 new `streamPipeline` tests.

- [ ] **Step 10.3:** TypeScript check.

```bash
cd dashboard && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 10.4:** Build check.

```bash
cd dashboard && npx vite build
```
Expected: Build succeeds.

- [ ] **Step 10.5:** Manual SSE smoke test (backend only).

```bash
curl -N "http://localhost:3001/api/pipeline/stream?keyword=test&vertical=TECHNOLOGY"
```
Expected when env vars unset: immediately yields `data: {"step": "error", ...}`. Expected when env vars set: yields one event per stage, then `complete`.

- [ ] **Step 10.6:** Manual browser smoke test.

Start via `./start-demo.sh`. Open `http://localhost:5173`. Enter a keyword, select a vertical, click "Run Pipeline". Verify progress steps appear one by one in DevTools → Network → EventStream tab AND in the UI. On completion, browser navigates to `/event/:clusterId`.

---

## Design Notes

**`submitPipeline` is unchanged.** POSTs to `POST /api/pipeline` (synchronous). Not used by any current component. Not removed.

**`GET /api/pipeline/stream` is additive.** Both endpoints call `_run_pipeline`. No existing endpoint is removed or altered.

**`_run_pipeline` change is backward-compatible.** `progress_cb=None` default means all existing callers and test mocks work without modification.

**Report persistence in SSE handler mirrors existing pattern.** Same as `execute_pipeline` in `server.py` — `_run_pipeline` returns the dict, the caller writes it to disk.

**Auto-navigation on `complete`.** `PipelineRunner` calls `useNavigate` to `/event/:clusterId`. `onComplete` (report list re-fetch) also fires but `HomePage` unmounts immediately after navigation — harmless.
