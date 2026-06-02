# LLM Provider Flexibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two gaps in LLM provider flexibility: make the health check report only the API keys that the active config actually needs, and make the provider field editable per slot in the Settings UI.

**Architecture:** Gap 3 (health check) is a pure backend change — replace the static `_REQUIRED_ENV_VARS` list in `server.py` with a function that reads `load_llm_config()` and maps configured providers to their env vars. Gap 2 (UI) is a pure frontend change — `SettingsRow` gets a `<select>` for provider; `SettingsPage` passes provider + handler down.

**Tech Stack:** Python 3.11 / FastAPI / pytest (backend); React 18 / TypeScript / Vitest / testing-library (frontend)

---

## Context you must know before touching code

- `narrative/llm_client.py` has two maps: `PROVIDER_BASE_URLS` and `PROVIDER_API_KEY_ENV`. Both are keyed by provider name string (`"deepseek"`, `"openai"`, `"google"`, `"groq"`). These are the authoritative lists of valid providers and their required env vars.
- `load_llm_config()` (in `narrative/llm_client.py`) returns a `dict` matching the `LLMConfig` schema. Each of the four slot keys maps to a sub-dict with `provider`, `model`, `thinking`, `temperature`.
- `_check_env()` in `narrative/server.py` currently iterates over `_REQUIRED_ENV_VARS`, a hardcoded list. We will replace this list with a function call.
- `SettingsRow.tsx` currently accepts only `model` and `onChange`. Provider is not passed to it at all — that's the gap. The backend `POST /api/config` already accepts full `LLMSlotConfig` including provider, so **no backend change is needed for Gap 2**.
- Run backend tests with: `uv run pytest tests/test_server.py -v` (from project root `/project/narrative-alpha`)
- Run frontend tests with: `cd dashboard && npm test -- --run` (from project root)

---

## Task 1: Dynamic health check (Gap 3 — backend)

**Files:**
- Modify: `narrative/server.py` (replace `_REQUIRED_ENV_VARS` list + update `_check_env`)
- Modify: `tests/test_server.py` (new test + update two existing tests that hardcode the provider key list)

---

- [ ] **Step 1: Write a failing test that captures the new behaviour**

Add this test to the bottom of `tests/test_server.py` (before the last closing line, after all existing tests):

```python
def test_health_env_only_requires_keys_for_configured_providers(tmp_path):
    """GET /api/health/env only flags missing keys for providers in active llm_config."""
    import json as _json
    config = {
        "call_1_entity_normalization": {"provider": "groq", "model": "llama3-70b", "thinking": False, "temperature": 0.1},
        "call_2_linguistic_neutralization": {"provider": "groq", "model": "llama3-70b", "thinking": False, "temperature": 0.1},
        "call_3_graph_extraction": {"provider": "groq", "model": "llama3-70b", "thinking": False, "temperature": 0.1},
        "call_4_forensic_synthesis": {"provider": "groq", "model": "llama3-70b", "thinking": False, "temperature": 0.1},
    }
    config_path = os.path.join(str(tmp_path), "llm_config.json")
    with open(config_path, "w") as f:
        _json.dump(config, f)

    env = {
        "NARRATIVE_ALPHA_ROOT": str(tmp_path),
        "GROQ_API_KEY": "sk-test-groq",
        "BRIGHTDATA_API_KEY": "bd-key",
        "BRIGHTDATA_SERP_ZONE": "serp",
        "BRIGHTDATA_UNLOCKER_ZONE": "unlocker",
    }
    with patch.dict(os.environ, env, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/health/env")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok", f"Expected ok, got: {data}"
    assert "GROQ_API_KEY" in data["present"]
    assert "DEEPSEEK_API_KEY" not in data["present"]
    assert "DEEPSEEK_API_KEY" not in data["missing"]
    assert "OPENAI_API_KEY" not in data["missing"]
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
uv run pytest tests/test_server.py::test_health_env_only_requires_keys_for_configured_providers -v
```

Expected: `FAILED` — `data["status"]` is `"degraded"` because `DEEPSEEK_API_KEY` and `OPENAI_API_KEY` are flagged missing even though they're not configured.

- [ ] **Step 3: Replace the static list with a dynamic function in `narrative/server.py`**

Find this block (around line 267):

```python
_REQUIRED_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_SERP_ZONE",
    "BRIGHTDATA_UNLOCKER_ZONE",
]


def _check_env() -> dict:
    present_list = []
    missing_list = []
    for var in _REQUIRED_ENV_VARS:
        if os.environ.get(var):
            present_list.append(var)
        else:
            missing_list.append(var)
    status = "ok" if not missing_list else "degraded"
    detail = "All required vars set" if not missing_list else f"Missing: {', '.join(missing_list)}"
    return {"status": status, "detail": detail, "present": present_list, "missing": missing_list}
```

Replace it with:

```python
_INFRA_ENV_VARS = [
    "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_SERP_ZONE",
    "BRIGHTDATA_UNLOCKER_ZONE",
]


def _required_env_vars() -> list[str]:
    """Return env vars required by the active llm_config + fixed infra vars."""
    config = load_llm_config()
    providers_in_use: set[str] = {
        slot["provider"]
        for slot in config.values()
        if isinstance(slot, dict) and "provider" in slot
    }
    llm_keys = [
        PROVIDER_API_KEY_ENV[p]
        for p in providers_in_use
        if p in PROVIDER_API_KEY_ENV
    ]
    return sorted(set(llm_keys + _INFRA_ENV_VARS))


def _check_env() -> dict:
    required = _required_env_vars()
    present_list = [v for v in required if os.environ.get(v)]
    missing_list = [v for v in required if not os.environ.get(v)]
    status = "ok" if not missing_list else "degraded"
    detail = "All required vars set" if not missing_list else f"Missing: {', '.join(missing_list)}"
    return {"status": status, "detail": detail, "present": present_list, "missing": missing_list}
```

You also need to add the import of `PROVIDER_API_KEY_ENV` and `load_llm_config` at the top of `server.py`. Check whether they are already imported — search for `from narrative.llm_client import`. Add `PROVIDER_API_KEY_ENV` and `load_llm_config` to that import line if they're not already there.

- [ ] **Step 4: Run the new test to confirm it passes**

```bash
uv run pytest tests/test_server.py::test_health_env_only_requires_keys_for_configured_providers -v
```

Expected: `PASSED`

- [ ] **Step 5: Fix the two existing tests that hardcode the static key list**

In `tests/test_server.py`, find this block:

```python
_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_SERP_ZONE",
    "BRIGHTDATA_UNLOCKER_ZONE",
]


def test_health_env_shows_present_when_set():
    """GET /api/health/env marks set vars as present."""
    env = {v: f"test_{v}" for v in _ENV_VARS}
    env["NARRATIVE_ALPHA_ROOT"] = "/tmp/test_narrative"
    with patch.dict(os.environ, env, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/health/env")
        assert resp.status_code == 200
        data = resp.json()
        assert sorted(data["present"]) == sorted(_ENV_VARS)
        assert data["missing"] == []
        assert data["status"] == "ok"


def test_health_env_shows_all_missing_when_unset():
    """GET /api/health/env marks all vars missing when none set."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative"}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/health/env")
        assert resp.status_code == 200
        data = resp.json()
        assert data["present"] == []
        assert sorted(data["missing"]) == sorted(_ENV_VARS)
        assert data["status"] == "degraded"
```

Replace with (the default config uses deepseek for all slots, so DEEPSEEK_API_KEY is required; OPENAI_API_KEY is not required unless configured):

```python
# Default config uses deepseek for all 4 slots — only DEEPSEEK_API_KEY + infra required
_DEFAULT_REQUIRED_VARS = [
    "DEEPSEEK_API_KEY",
    "BRIGHTDATA_API_KEY",
    "BRIGHTDATA_SERP_ZONE",
    "BRIGHTDATA_UNLOCKER_ZONE",
]


def test_health_env_shows_present_when_set():
    """GET /api/health/env marks set vars as present (default config = deepseek)."""
    env = {v: f"test_{v}" for v in _DEFAULT_REQUIRED_VARS}
    env["NARRATIVE_ALPHA_ROOT"] = "/tmp/test_narrative"
    with patch.dict(os.environ, env, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/health/env")
        assert resp.status_code == 200
        data = resp.json()
        assert sorted(data["present"]) == sorted(_DEFAULT_REQUIRED_VARS)
        assert data["missing"] == []
        assert data["status"] == "ok"


def test_health_env_shows_all_missing_when_unset():
    """GET /api/health/env marks all vars missing when none set."""
    with patch.dict(os.environ, {"NARRATIVE_ALPHA_ROOT": "/tmp/test_narrative"}, clear=True):
        from narrative.server import app
        tc = TestClient(app)
        resp = tc.get("/api/health/env")
        assert resp.status_code == 200
        data = resp.json()
        assert data["present"] == []
        assert sorted(data["missing"]) == sorted(_DEFAULT_REQUIRED_VARS)
        assert data["status"] == "degraded"
```

Also update the `_TEST_ENV` dict used by the deep health tests — it currently includes `OPENAI_API_KEY` which will still work (extra env vars don't cause failures), so leave `_TEST_ENV` unchanged.

- [ ] **Step 6: Run the full server test suite**

```bash
uv run pytest tests/test_server.py -v
```

Expected: all tests pass (the count should match or exceed what was there before).

- [ ] **Step 7: Commit**

```bash
git add narrative/server.py tests/test_server.py
git commit -m "fix: health check derives required API keys from active llm_config

Was hardcoded to deepseek + openai regardless of what providers
are configured. Now reads load_llm_config() at check time and
requires only the keys for providers actually in use."
```

---

## Task 2: Provider editable in Settings UI (Gap 2 — frontend)

**Files:**
- Modify: `dashboard/src/components/SettingsRow.tsx` (add `provider` + `onProviderChange` props; render `<select>`)
- Modify: `dashboard/src/components/SettingsRow.test.tsx` (update for new props; replace "no combobox" test)
- Modify: `dashboard/src/components/SettingsPage.tsx` (pass provider + handler; add Provider column header)
- Modify: `dashboard/src/components/SettingsPage.test.tsx` (add test that provider renders in select)

Valid providers (from `llm_client.py`): `"deepseek"`, `"openai"`, `"google"`, `"groq"`. Hardcode these in the frontend — they mirror the backend registry and won't change without a backend change too.

---

- [ ] **Step 1: Write a failing test in `SettingsRow.test.tsx`**

Replace the `defaultProps` block and the "does not render a provider select" test. The full updated file:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SettingsRow } from "./SettingsRow";

const defaultProps = {
  slotName: "Call 1",
  slotDescription: "Entity normalization",
  provider: "deepseek",
  model: "deepseek-v4-flash",
  onChange: vi.fn(),
  onProviderChange: vi.fn(),
};

describe("SettingsRow", () => {
  it("renders slot name and description", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(screen.getByText("Call 1")).toBeInTheDocument();
    expect(screen.getByText("Entity normalization")).toBeInTheDocument();
  });

  it("renders model input with current value", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(screen.getByDisplayValue("deepseek-v4-flash")).toBeInTheDocument();
  });

  it("calls onChange with new value when model input changes", () => {
    const onChange = vi.fn();
    render(<SettingsRow {...defaultProps} onChange={onChange} />);
    fireEvent.change(screen.getByDisplayValue("deepseek-v4-flash"), { target: { value: "deepseek-v4-pro" } });
    expect(onChange).toHaveBeenCalledWith("deepseek-v4-pro");
  });

  it("renders a provider select with the current provider selected", () => {
    render(<SettingsRow {...defaultProps} provider="groq" />);
    const select = screen.getByRole("combobox", { name: /provider for call 1/i });
    expect(select).toBeInTheDocument();
    expect((select as HTMLSelectElement).value).toBe("groq");
  });

  it("calls onProviderChange when provider select changes", () => {
    const onProviderChange = vi.fn();
    render(<SettingsRow {...defaultProps} onProviderChange={onProviderChange} />);
    const select = screen.getByRole("combobox", { name: /provider for call 1/i });
    fireEvent.change(select, { target: { value: "openai" } });
    expect(onProviderChange).toHaveBeenCalledWith("openai");
  });

  it("renders all four provider options", () => {
    render(<SettingsRow {...defaultProps} />);
    const select = screen.getByRole("combobox", { name: /provider for call 1/i });
    const options = Array.from((select as HTMLSelectElement).options).map((o) => o.value);
    expect(options).toEqual(expect.arrayContaining(["deepseek", "openai", "google", "groq"]));
  });

  it("does not render a temperature range slider", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(document.querySelector('input[type="range"]')).toBeNull();
  });

  it("does not render a thinking checkbox", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(document.querySelector('input[type="checkbox"]')).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /project/narrative-alpha/dashboard && npm test -- --run SettingsRow
```

Expected: `FAILED` — `SettingsRow` doesn't accept `provider`/`onProviderChange` yet and has no `<select>`.

- [ ] **Step 3: Update `SettingsRow.tsx` to add provider select**

Replace the entire file:

```tsx
const PROVIDERS = ["deepseek", "openai", "google", "groq"] as const;

interface SettingsRowProps {
  slotName: string;
  slotDescription: string;
  provider: string;
  model: string;
  onChange: (model: string) => void;
  onProviderChange: (provider: string) => void;
}

export function SettingsRow({
  slotName,
  slotDescription,
  provider,
  model,
  onChange,
  onProviderChange,
}: SettingsRowProps) {
  return (
    <div className="settings-row">
      <div className="settings-slot">
        {slotName}
        <div className="settings-slot-sub">{slotDescription}</div>
      </div>
      <select
        value={provider}
        onChange={(e) => onProviderChange(e.target.value)}
        aria-label={`Provider for ${slotName}`}
      >
        {PROVIDERS.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>
      <input
        type="text"
        value={model}
        onChange={(e) => onChange(e.target.value)}
        aria-label={`Model for ${slotName}`}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run the SettingsRow tests to confirm they pass**

```bash
cd /project/narrative-alpha/dashboard && npm test -- --run SettingsRow
```

Expected: all SettingsRow tests `PASSED`.

- [ ] **Step 5: Update `SettingsPage.tsx` to pass provider props and add column header**

Replace the entire file:

```tsx
import { useState, useEffect } from "react";
import type { LLMConfig, LLMSlotConfig } from "../types";
import { SettingsRow } from "./SettingsRow";
import { EnvHealthPanel } from "./EnvHealthPanel";
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
        Configure the provider and model for each pipeline call slot.
      </p>

      <EnvHealthPanel />

      <div className="settings-table">
        <div className="settings-header">
          <div>Call Slot</div>
          <div>Provider</div>
          <div>Model</div>
        </div>

        {SLOTS.map(({ key, name, description }) => (
          <SettingsRow
            key={key}
            slotName={name}
            slotDescription={description}
            provider={config[key].provider}
            model={config[key].model}
            onChange={(model) => handleUpdate(key, { model })}
            onProviderChange={(provider) => handleUpdate(key, { provider })}
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

- [ ] **Step 6: Add a test to `SettingsPage.test.tsx` that verifies provider renders**

Add this test after the last existing test in `SettingsPage.test.tsx`:

```tsx
it("renders provider select with value from config", async () => {
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  const selects = await screen.findAllByRole("combobox");
  // 4 slots, each with a provider select
  expect(selects.length).toBe(4);
  // Default mock config has provider "deepseek" for all slots
  expect((selects[0] as HTMLSelectElement).value).toBe("deepseek");
});
```

- [ ] **Step 7: Run the full frontend test suite**

```bash
cd /project/narrative-alpha/dashboard && npm test -- --run
```

Expected: all tests pass. The count should be ≥ the previous count (new tests added, none removed except the replaced "no combobox" test).

- [ ] **Step 8: Type-check**

```bash
cd /project/narrative-alpha/dashboard && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add dashboard/src/components/SettingsRow.tsx \
        dashboard/src/components/SettingsRow.test.tsx \
        dashboard/src/components/SettingsPage.tsx \
        dashboard/src/components/SettingsPage.test.tsx
git commit -m "feat: make LLM provider selectable per slot in Settings UI

Provider field was read-only. Now renders a <select> with all
four supported providers. Saving pushes the full slot config
(provider + model) to POST /api/config, which already accepted it."
```

---

## Self-review

**Spec coverage:**
- Gap 3 (dynamic health check) — covered by Task 1 ✓
- Gap 2 (UI provider editable) — covered by Task 2 ✓

**Placeholder scan:** None found.

**Type consistency:**
- `onProviderChange` defined in Task 2 Step 1 (test), implemented in Step 3 (`SettingsRow.tsx`), consumed in Step 5 (`SettingsPage.tsx`) — consistent throughout.
- `_required_env_vars()` defined and called in `_check_env()` in same file — no cross-task type drift.

**Known limitation not addressed:** `get_embedding()` in `llm_client.py` is hardcoded to the `openai` provider, so pipelines always need `OPENAI_API_KEY` even when no slots are configured to use OpenAI. This is Gap 1 (medium complexity) and is out of scope for this plan.
