# Local API + Dashboard Wire-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace Modal serverless with a local FastAPI backend and wire the React dashboard to live API calls, removing all fake data stubs.

**Architecture:** Drop Modal, run FastAPI + uvicorn locally. Dashboard communicates via Vite proxy with 120s timeout. Backend persists reports as JSON files, serves cluster listing from filesystem scan, and is the sole source of truth for LLM config. No hardcoded model defaults in frontend.

**Tech Stack:** Python, FastAPI, uvicorn, Vite proxy, React, httpx. No Modal.

---

## File Map

| File | Status | Responsibility |
|------|--------|---------------|
| `narrative/pipeline.py` | Create | Core `_run_pipeline()` + `_run_startup_init()` extracted from app.py, no Modal deps |
| `narrative/server.py` | Create | FastAPI app with 5 endpoints, imports from pipeline.py |
| `narrative/app.py` | Delete | Old Modal orchestration |
| `tests/test_server.py` | Create | FastAPI TestClient tests for all 5 endpoints |
| `tests/test_app.py` | Delete | Old Modal mock tests |
| `requirements.txt` | Modify | Remove modal, add fastapi/uvicorn/python-dotenv |
| `dashboard/src/api.ts` | Create | Typed fetch wrapper for all 5 API endpoints |
| `dashboard/src/components/HomePage.tsx` | Create | Cluster list fetched from `/api/reports` |
| `dashboard/src/components/App.tsx` | Modify | Add HomePage route, update nav links |
| `dashboard/src/components/EventPage.tsx` | Rewrite | Fetch from `/api/reports/{id}`, no stub imports |
| `dashboard/src/components/SettingsPage.tsx` | Rewrite | Fetch config from `/api/config` on mount, POST on save |
| `dashboard/src/data/sample-data.ts` | Delete | No longer needed |
| `dashboard/vite.config.ts` | Modify | Add `/api` proxy with 120s timeout |

---

### Task 9: Backend — FastAPI Server

**Files:**
- Create: `narrative/pipeline.py`
- Create: `narrative/server.py`
- Create: `tests/test_server.py`
- Create: `data/reports/.gitkeep`
- Modify: `requirements.txt`
- Delete: `narrative/app.py`
- Delete: `tests/test_app.py`

- [x] **Step 9.1: Update requirements.txt**

Replace contents:

```txt
fastapi>=0.115.0
uvicorn>=0.34.0
python-dotenv>=1.0.0
openai>=1.0.0
requests>=2.31.0
pydantic>=2.0.0
numpy>=1.26.0
trafilatura>=1.12.0
```

- [x] **Step 9.2: Extract pipeline core into `narrative/pipeline.py`**

Copy `_run_pipeline()` and `_run_startup_init()` from `narrative/app.py` into a new file with no Modal imports.

Replace `run_historical_backtest.spawn(domain, vertical)` with `threading.Thread`:

```python
threading.Thread(
    target=execute_historical_backtest,
    args=(doc["source_domain"], vertical),
    daemon=True,
).start()
```

Add `# __init__.py` already exists — no changes needed.

Create `data/reports/` directory with `.gitkeep`.

- [x] **Step 9.3: Write failing tests for server.py**

**File:** `tests/test_server.py`

```python
"""Tests for narrative.server — FastAPI local backend (Task 9)."""

import json
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client():
    """TestClient with clean state."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative"}, clear=True):
        from narrative.server import app
        return TestClient(app)


def test_get_config_returns_defaults(client):
    """GET /api/config returns valid LLMConfig when no file exists."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "call_1_entity_normalization" in data
    assert data["call_1_entity_normalization"]["provider"] == "deepseek"
    assert data["call_1_entity_normalization"]["model"] == "deepseek-v4-flash"


def test_post_config_saves_and_returns(client, tmp_path):
    """POST /api/config writes valid config and returns ok."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        payload = {
            "call_1_entity_normalization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
            "call_2_linguistic_neutralization": {"provider": "openai", "model": "gpt-4", "thinking": False, "temperature": 0.1},
            "call_3_graph_extraction": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
            "call_4_forensic_synthesis": {"provider": "openai", "model": "gpt-4", "thinking": True, "temperature": 0.1},
        }
        resp = tc.post("/api/config", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        config_path = os.path.join(str(tmp_path), "llm_config.json")
        assert os.path.exists(config_path)
        with open(config_path) as f:
            written = json.load(f)
        assert written["call_3_graph_extraction"]["model"] == "gpt-4"


def test_post_config_rejects_missing_slot(client):
    """POST /api/config returns 422 for missing required slot."""
    resp = client.post("/api/config", json={
        "call_1_entity_normalization": {},
        "call_2_linguistic_neutralization": {},
        "call_3_graph_extraction": {},
    })
    assert resp.status_code == 422


def test_get_reports_empty(client):
    """GET /api/reports returns empty list when no reports exist."""
    resp = client.get("/api/reports")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_reports_with_file(client, tmp_path):
    """GET /api/reports lists reports from data/reports/."""
    reports_dir = os.path.join(str(tmp_path), "data", "reports")
    os.makedirs(reports_dir)
    with open(os.path.join(reports_dir, "EVT-001.json"), "w") as f:
        json.dump({
            "event_meta": {
                "cluster_id": "EVT-001", "search_query": "test",
                "industry_vertical": "TECH", "timestamp_utc": "now",
                "corpus_count": 5, "corpus_capped": False,
            }
        }, f)

    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cluster_id"] == "EVT-001"


def test_get_report_by_id(client, tmp_path):
    """GET /api/reports/{cluster_id} returns full ForensicReport."""
    reports_dir = os.path.join(str(tmp_path), "data", "reports")
    os.makedirs(reports_dir)
    report = {
        "event_meta": {
            "cluster_id": "EVT-001", "search_query": "test",
            "industry_vertical": "TECH", "timestamp_utc": "now",
            "corpus_count": 5, "corpus_capped": False,
        },
        "consensus_reality_graph": {"consensus_summary": "none", "verified_anchor_nodes": [], "primary_verifications": []},
        "distortion_matrix": [], "outlier_signals": [], "reputation_warnings": [],
        "reality_divergence_zones": [], "reality_fractures": [], "narrative_regime_shifts": [],
    }
    with open(os.path.join(reports_dir, "EVT-001.json"), "w") as f:
        json.dump(report, f)

    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": str(tmp_path)}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/reports/EVT-001")
        assert resp.status_code == 200
        assert resp.json()["event_meta"]["cluster_id"] == "EVT-001"


def test_get_report_missing_returns_404(client):
    """GET /api/reports/nonexistent returns 404."""
    resp = client.get("/api/reports/NONEXISTENT")
    assert resp.status_code == 404
    assert "error" in resp.json()
```

Run: `pytest tests/test_server.py -v`
Expected: 7 tests, all FAIL (import errors from server.py not existing yet)

- [x] **Step 9.4: Write minimal FastAPI server**

**File:** `narrative/server.py`

```python
"""Local FastAPI backend for Narrative Alpha — replaces Modal orchestration."""

import json
import os
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from narrative.pipeline import _run_pipeline, _run_startup_init
from narrative.backtest import execute_historical_backtest
from narrative.contracts import LLMConfig, LLMSlotConfig
from narrative.llm_client import load_llm_config, DEFAULT_LLM_CONFIG


app = FastAPI(title="Narrative Alpha API")


# ── Config path helper ──

def _narrative_root() -> str:
    return os.environ.get("NARRATIVE_ALPHA_ROOT", os.path.expanduser("~/.narrative_alpha"))


def _config_path() -> str:
    return os.path.join(_narrative_root(), "llm_config.json")


def _reports_dir() -> str:
    return os.path.join(_narrative_root(), "data", "reports")


# ── Startup ──

@app.on_event("startup")
def startup():
    os.makedirs(_reports_dir(), exist_ok=True)
    _run_startup_init()


# ── API endpoints ──

class PipelinePayload(BaseModel):
    keyword: str
    vertical: str = "TECHNOLOGY"


@app.post("/api/pipeline")
def execute_pipeline(payload: PipelinePayload) -> dict:
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")

    if not api_key or not unlocker_zone:
        return {"status": "ERROR", "error": "BRIGHTDATA_API_KEY and BRIGHTDATA_UNLOCKER_ZONE must be set"}

    db_path = os.path.join(_narrative_root(), "outlet_reputation.db")
    report = _run_pipeline(payload.keyword, payload.vertical, api_key, unlocker_zone, db_path)

    cluster_id = report.get("event_meta", {}).get("cluster_id", "unknown")
    os.makedirs(_reports_dir(), exist_ok=True)
    report_path = os.path.join(_reports_dir(), f"{cluster_id}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


@app.get("/api/reports")
def list_reports() -> list[dict]:
    reports_dir = _reports_dir()
    if not os.path.isdir(reports_dir):
        return []

    summaries = []
    for fname in sorted(os.listdir(reports_dir), reverse=True):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(reports_dir, fname)) as f:
                report = json.load(f)
            meta = report.get("event_meta", {})
            summaries.append({
                "cluster_id": meta.get("cluster_id", ""),
                "search_query": meta.get("search_query", ""),
                "industry_vertical": meta.get("industry_vertical", ""),
                "timestamp_utc": meta.get("timestamp_utc", ""),
                "corpus_count": meta.get("corpus_count", 0),
                "corpus_capped": meta.get("corpus_capped", False),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return summaries


@app.get("/api/reports/{cluster_id}")
def get_report(cluster_id: str) -> dict:
    report_path = os.path.join(_reports_dir(), f"{cluster_id}.json")
    if not os.path.isfile(report_path):
        raise HTTPException(status_code=404, detail={"error": f"Report {cluster_id} not found"})
    with open(report_path) as f:
        return json.load(f)


@app.get("/api/config")
def get_config() -> dict:
    return load_llm_config()


@app.post("/api/config")
def update_config(payload: dict) -> dict:
    required_slots = [
        "call_1_entity_normalization",
        "call_2_linguistic_neutralization",
        "call_3_graph_extraction",
        "call_4_forensic_synthesis",
    ]
    for slot in required_slots:
        if slot not in payload:
            raise HTTPException(status_code=422, detail=f"Missing required slot: {slot}")

    try:
        LLMConfig(**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid config: {e}")

    with open(_config_path(), "w") as f:
        json.dump(payload, f, indent=2)

    return {"status": "ok", "config": payload}
```

- [x] **Step 9.5: Extract pipeline core into `narrative/pipeline.py`**

**File:** `narrative/pipeline.py` — copy `_run_pipeline()` and `_run_startup_init()` from `narrative/app.py`, replacing `.spawn()` with threading:

```python
# Replace this block in Step 4 of _run_pipeline:
    if status == "UNRATED":
        run_historical_backtest.spawn(doc["source_domain"], vertical)

# With:
    if status == "UNRATED":
        threading.Thread(
            target=execute_historical_backtest,
            args=(doc["source_domain"], vertical),
            daemon=True,
        ).start()
```

Replace the `import modal` + `modal.Volume` + `modal.Image` + `modal.App` + `modal.Secret` blocks with just `import threading`. Strip all `vol.commit()` calls.

- [x] **Step 9.6: Run server tests to verify**

Run: `pytest tests/test_server.py -v`
Expected: 7+ tests, all PASS

- [x] **Step 9.7: Migrate remaining test_app tests to test_server**

Copy the 10 existing test functions from `tests/test_app.py` that test `_run_pipeline` logic and `_run_startup_init` — these test the core pipeline, not Modal. Add them to `tests/test_server.py` with adjusted imports (`from narrative.pipeline import _run_pipeline, _run_startup_init`).

Run: `pytest tests/ -v`
Expected: 257+ tests, all PASS

- [x] **Step 9.8: Delete app.py and test_app.py**

```bash
rm narrative/app.py tests/test_app.py
```

- [x] **Step 9.9: Final verification**

Run: `pytest tests/ -v`
Expected: 257+ tests (minus 10 deleted, plus ~10 new = roughly same count), all PASS

---

### Task 10: Dashboard — Data Integration

**Files:**
- Create: `dashboard/src/api.ts`
- Create: `dashboard/src/components/HomePage.tsx`
- Create: `dashboard/src/components/HomePage.test.tsx`
- Modify: `dashboard/vite.config.ts`
- Modify: `dashboard/src/components/App.tsx`
- Modify: `dashboard/src/components/App.test.tsx` (or Badge tests) — update if App.tsx tests exist
- Rewrite: `dashboard/src/components/EventPage.tsx`
- Modify: `dashboard/src/components/EventPage.test.tsx` (update EventPage tests)
- Rewrite: `dashboard/src/components/SettingsPage.tsx`
- Modify: `dashboard/src/components/SettingsPage.test.tsx` (update SettingsPage tests)
- Delete: `dashboard/src/data/sample-data.ts`

- [x] **Step 10.1: Add Vite proxy config**

**File:** `dashboard/vite.config.ts`

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        proxyTimeout: 120_000,
        timeout: 120_000,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

- [x] **Step 10.2: Write api.ts with tests**

**File:** `dashboard/src/api.ts`

```ts
import type { ForensicReport, ClusterSummary, LLMConfig } from "./types";

const BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function fetchReports(): Promise<ClusterSummary[]> {
  return fetchJson<ClusterSummary[]>(`${BASE}/reports`);
}

export function fetchReport(clusterId: string): Promise<ForensicReport> {
  return fetchJson<ForensicReport>(`${BASE}/reports/${encodeURIComponent(clusterId)}`);
}

export function fetchConfig(): Promise<LLMConfig> {
  return fetchJson<LLMConfig>(`${BASE}/config`);
}

export function saveConfig(config: LLMConfig): Promise<{ status: string; config: LLMConfig }> {
  return fetchJson(`${BASE}/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
}

export function submitPipeline(keyword: string, vertical: string): Promise<ForensicReport> {
  return fetchJson(`${BASE}/pipeline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword, vertical }),
  });
}
```

**Test file:** `dashboard/src/api.test.ts`

```ts
import { describe, it, expect, vi } from "vitest";

describe("fetchReports", () => {
  it("calls /api/reports and returns cluster list", async () => {
    const fake = [{ cluster_id: "EVT-001", search_query: "test", industry_vertical: "TECH", timestamp_utc: "now", corpus_count: 5, corpus_capped: false }];
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fake) } as Response);
    const { fetchReports } = await import("./api");
    const result = await fetchReports();
    expect(result).toEqual(fake);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/reports");
  });

  it("throws on non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: false, status: 404, statusText: "Not Found" } as Response);
    const { fetchReports } = await import("./api");
    await expect(fetchReports()).rejects.toThrow("API 404: Not Found");
  });
});

describe("fetchReport", () => {
  it("calls /api/reports/{id}", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ event_meta: { cluster_id: "EVT-001" } }) } as Response);
    const { fetchReport } = await import("./api");
    await fetchReport("EVT-001");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/reports/EVT-001");
  });
});

describe("saveConfig", () => {
  it("POSTs config to /api/config", async () => {
    const config = { call_1_entity_normalization: { provider: "deepseek", model: "v4", thinking: false, temperature: 0.1 } } as any;
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ status: "ok", config }) } as Response);
    const { saveConfig } = await import("./api");
    await saveConfig(config);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/config", expect.objectContaining({ method: "POST" }));
  });
});

describe("submitPipeline", () => {
  it("POSTs keyword and vertical", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ event_meta: {} }) } as Response);
    const { submitPipeline } = await import("./api");
    await submitPipeline("test", "TECH");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/pipeline", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ keyword: "test", vertical: "TECH" }),
    }));
  });
});
```

Run: `npx vitest run src/api.test.ts`
Expected: 5+ tests, all PASS

- [x] **Step 10.3: Write HomePage component with tests**

**File:** `dashboard/src/components/HomePage.tsx`

```tsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import type { ClusterSummary } from "../types";
import { fetchReports } from "../api";

export function HomePage() {
  const [reports, setReports] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReports()
      .then(setReports)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page"><p className="loading">Loading reports…</p></div>;
  if (error) return <div className="page"><p className="error">Error: {error}</p></div>;
  if (reports.length === 0) return <div className="page"><p className="empty">No reports yet. Run a pipeline to get started.</p></div>;

  return (
    <div className="page">
      <h1 className="page-title">Forensic Reports</h1>
      <div className="report-list">
        {reports.map((r) => (
          <Link key={r.cluster_id} to={`/event/${r.cluster_id}`} className="report-card">
            <h2>{r.search_query}</h2>
            <p className="report-meta">{r.industry_vertical} · {r.corpus_count} articles · {r.timestamp_utc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

**Test file:** `dashboard/src/components/HomePage.test.tsx`

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { HomePage } from "./HomePage";

beforeEach(() => {
  vi.restoreAllMocks();
});

it("shows loading state initially", () => {
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(screen.getByText("Loading reports…")).toBeTruthy();
});

it("shows error message on fetch failure", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network error"));
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(await screen.findByText(/Network error/)).toBeTruthy();
});

it("shows empty state when no reports", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) } as Response);
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(await screen.findByText(/No reports yet/)).toBeTruthy();
});

it("renders report cards from fetch", async () => {
  const fake = [
    { cluster_id: "EVT-001", search_query: "Test query", industry_vertical: "TECH", timestamp_utc: "2026-05-30T00:00:00Z", corpus_count: 5, corpus_capped: false },
  ];
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fake) } as Response);
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(await screen.findByText("Test query")).toBeTruthy();
  expect(screen.getByText(/5 articles/)).toBeTruthy();
});
```

Run: `npx vitest run src/components/HomePage.test.tsx`
Expected: 4+ tests, all PASS

- [x] **Step 10.4: Update App.tsx — add HomePage route**

**File:** `dashboard/src/components/App.tsx`

```tsx
import { HashRouter, Routes, Route, NavLink } from "react-router-dom";
import { HomePage } from "./HomePage";
import { EventPage } from "./EventPage";
import { SettingsPage } from "./SettingsPage";
import { FontSizeControl } from "./FontSizeControl";

export function App() {
  return (
    <HashRouter>
      <div className="app">
        <header className="app-header">
          <NavLink to="/" className="app-logo">Narrative Alpha</NavLink>
          <nav className="app-nav">
            <NavLink to="/" end className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              Reports
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              Settings
            </NavLink>
            <FontSizeControl />
          </nav>
        </header>

        <main className="app-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/event/:clusterId" element={<EventPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}
```

Update App tests if they exist (check for `App.test.tsx` — if present, update route references). If no App tests exist, skip.

- [x] **Step 10.5: Rewrite EventPage — fetch from API**

**File:** `dashboard/src/components/EventPage.tsx`

```tsx
import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Zone1 } from "./Zone1";
import { Zone2 } from "./Zone2";
import { Zone3 } from "./Zone3";
import { fetchReport } from "../api";
import type { ForensicReport } from "../types";

export function EventPage() {
  const { clusterId } = useParams<{ clusterId: string }>();
  const [report, setReport] = useState<ForensicReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!clusterId) return;
    setLoading(true);
    setError(null);
    fetchReport(clusterId)
      .then(setReport)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [clusterId]);

  if (loading) return <div className="page"><p className="loading">Loading report…</p></div>;
  if (error) return <div className="page"><p className="error">Error: {error}</p></div>;
  if (!report) return <div className="page"><p className="empty">Report not found.</p></div>;

  return (
    <div className="page">
      <h1 className="page-title">{report.event_meta.cluster_id}</h1>
      <p className="page-subtitle">{report.event_meta.search_query}</p>

      <Zone1 report={report} />
      <Zone2 report={report} />
      <Zone3 report={report} />
    </div>
  );
}
```

Update EventPage tests:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { EventPage } from "./EventPage";

beforeEach(() => {
  vi.restoreAllMocks();
});

it("shows loading state initially", () => {
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
  render(
    <MemoryRouter initialEntries={["/event/EVT-001"]}>
      <Routes>
        <Route path="/event/:clusterId" element={<EventPage />} />
      </Routes>
    </MemoryRouter>
  );
  expect(screen.getByText("Loading report…")).toBeTruthy();
});

it("shows error message on fetch failure", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Not found"));
  render(
    <MemoryRouter initialEntries={["/event/EVT-001"]}>
      <Routes>
        <Route path="/event/:clusterId" element={<EventPage />} />
      </Routes>
    </MemoryRouter>
  );
  expect(await screen.findByText(/Not found/)).toBeTruthy();
});

it("renders report from API data", async () => {
  const fakeReport = {
    event_meta: { cluster_id: "EVT-001", search_query: "Fab 7 halt", industry_vertical: "TECH", timestamp_utc: "now", corpus_count: 7, corpus_capped: false },
    consensus_reality_graph: { consensus_summary: "Things happened", verified_anchor_nodes: ["Fab 7"], primary_verifications: [] },
    distortion_matrix: [],
    outlier_signals: [],
    reputation_warnings: [],
    reality_divergence_zones: [],
    reality_fractures: [],
    narrative_regime_shifts: [],
  };
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fakeReport) } as Response);
  render(
    <MemoryRouter initialEntries={["/event/EVT-001"]}>
      <Routes>
        <Route path="/event/:clusterId" element={<EventPage />} />
      </Routes>
    </MemoryRouter>
  );
  expect(await screen.findByText("EVT-001")).toBeTruthy();
  expect(screen.getByText("Fab 7 halt")).toBeTruthy();
});
```

Run: `npx vitest run src/components/EventPage.test.tsx`
Expected: 3+ tests, all PASS

- [x] **Step 10.6: Rewrite SettingsPage — fetch config from backend**

**File:** `dashboard/src/components/SettingsPage.tsx`

```tsx
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
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig()
      .then(setConfig)
      .catch((e: Error) => setSaveStatus(`Failed to load config: ${e.message}`))
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
            provider={config?.[key]?.provider ?? "deepseek"}
            model={config?.[key]?.model ?? ""}
            thinking={config?.[key]?.thinking ?? false}
            temperature={config?.[key]?.temperature ?? 0.1}
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

Update SettingsPage tests — the component now fetches from API. Tests must mock `fetch`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SettingsPage } from "./SettingsPage";

const fakeConfig = {
  call_1_entity_normalization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_2_linguistic_neutralization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_3_graph_extraction: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
  call_4_forensic_synthesis: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
};

beforeEach(() => {
  vi.restoreAllMocks();
});

it("shows loading state initially", () => {
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(screen.getByText("Loading config…")).toBeTruthy();
});

it("renders settings rows after fetch", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fakeConfig) } as Response);
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText("Call 1")).toBeTruthy();
  expect(await screen.findByText("Call 4")).toBeTruthy();
});

it("renders save button after fetch", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fakeConfig) } as Response);
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText("Save Configuration")).toBeTruthy();
});

it("shows Call 3 thinking = true from backend", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fakeConfig) } as Response);
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  const onText = await screen.findAllByText("On");
  expect(onText.length).toBeGreaterThanOrEqual(2);
});
```

Run: `npx vitest run src/components/SettingsPage.test.tsx`
Expected: 4+ tests, all PASS

- [x] **Step 10.7: Delete sample-data.ts**

```bash
rm dashboard/src/data/sample-data.ts
```

- [x] **Step 10.8: Full verification**

```bash
cd dashboard && npx vitest run
```

Expected: 60+ tests, all PASS

```bash
cd dashboard && npx tsc --noEmit
```

Expected: No errors

```bash
cd dashboard && npx vite build
```

Expected: Build succeeds

```bash
cd /project/narrative && uv run pytest tests/ -v
```

Expected: 257+ tests, all PASS

---

## Design Notes

**No hardcoded models:** The frontend `SettingsPage.tsx` fetches LLM config from `GET /api/config` on mount. The backend's `DEFAULT_LLM_CONFIG` in `llm_client.py:32-45` is the sole source of truth. The provider list (`["deepseek", "openai", "google", "groq"]`) remains hardcoded in `SettingsRow.tsx` — it's a stable enumeration of supported providers, not a model choice.

**Backend startup:** `uvicorn narrative.server:app --reload` — runs on port 8000 by default. Creates `data/reports/` on first start.

**Broken state after stub removal:** Until Task 10 is complete, the dashboard will show loading spinners and error messages instead of fake data. This is intentional — the user prefers visible brokenness over silent fakery.
