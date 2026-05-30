# Settings Page Rework — Model-Only Controls + Env Var Status Panel

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Simplify the Settings page by removing the provider selector, temperature slider, and thinking toggle from the UI. Show only one model-name text input per call slot. Add an env var status panel that calls `GET /api/health/env` and shows which required API keys are present or missing, so new users can immediately see what they need to configure.

**Architecture:** The backend `LLMConfig` Pydantic model and `POST /api/config` endpoint are unchanged. `LLMSlotConfig` in `types.ts` retains all four fields (`provider`, `model`, `thinking`, `temperature`) because the backend uses them on the wire. The UI simply stops exposing three of those four fields to the user. The existing `SettingsRow` component is simplified to a slot-label + model-name input only. A new `EnvHealthPanel` component fetches `GET /api/health/env` once on mount and renders a read-only key status list.

**Tech Stack:** React + TypeScript (no new libraries). Vitest + Testing Library for tests. The backend endpoint `GET /api/health/env` already exists in `narrative/server.py`.

---

## File Map

| File | Status | Responsibility |
|------|--------|----------------|
| `dashboard/src/types.ts` | Modify | Add `EnvHealth` interface only — `LLMSlotConfig` and `LLMConfig` stay exactly as-is |
| `dashboard/src/api.ts` | Modify | Add `fetchEnvHealth()` function |
| `dashboard/src/api.test.ts` | Modify | Add `fetchEnvHealth` tests |
| `dashboard/src/components/SettingsRow.tsx` | Modify | Remove provider, temperature, thinking props; keep slotName, slotDescription, model, onChange |
| `dashboard/src/components/SettingsRow.test.tsx` | Modify | Remove all provider/temperature/thinking tests; add simplified model-input tests |
| `dashboard/src/components/EnvHealthPanel.tsx` | Create | New component — calls fetchEnvHealth, renders present/missing key list with Recheck button |
| `dashboard/src/components/EnvHealthPanel.test.tsx` | Create | Tests for loading, all-present, degraded, error, recheck states |
| `dashboard/src/components/SettingsPage.tsx` | Modify | Remove provider/temperature/thinking columns; mount EnvHealthPanel; switch to module-level API mocks |
| `dashboard/src/components/SettingsPage.test.tsx` | Modify | Switch to module-level mocks; remove thinking test; add EnvHealthPanel rendering test |
| `dashboard/src/index.css` | Modify | Update settings grid columns; add env health panel styles |

---

## OPEN DECISIONS AND AMBIGUITIES

**OPEN DECISION 1 — `LLMSlotConfig` type: keep all fields.**

The backend `LLMSlotConfig` Pydantic model has `extra="forbid"`. `POST /api/config` accepts `LLMConfig` as body and calls `payload.model_dump()`. The frontend must still send `provider`, `thinking`, and `temperature` on every save, or the backend will reject with a 422. Decision: `LLMSlotConfig` in `types.ts` stays unchanged — all four fields remain. The UI simply stops rendering three of them as editable controls. Those fields flow through the frontend unchanged (loaded from backend, sent back on save).

**OPEN DECISION 2 — Provider column removal.**

`SettingsRow` drops the `provider` prop entirely. The parent `SettingsPage` holds the full slot config in state (including `provider`) and only passes `model` down. On update, `handleUpdate` merges `{ model }` into the full slot config object — `provider`, `thinking`, and `temperature` remain intact from the last `fetchConfig` response.

**OPEN DECISION 3 — `SettingsRow` survival vs. inlining.**

`SettingsRow` survives as a separate component (not inlined). Four identical rows still benefit from a shared component, and future per-row enhancements (model autocomplete, validation) are easier to add. The simplified row has three display props (`slotName`, `slotDescription`, `model`) and one callback (`onChange: (model: string) => void`). The old `onUpdate: (updates: Partial<{...}>) => void` is replaced.

**OPEN DECISION 4 — `EnvHealthPanel`: separate component.**

Separate component, not inlined into `SettingsPage`. It has its own async lifecycle, is independently testable, and could be reused elsewhere (e.g. a future homepage health indicator). It accepts no props and fetches data itself on mount.

**OPEN DECISION 5 — Auto-refresh of env var status.**

Fetch once on mount, no polling. Env vars are set at server startup and do not change at runtime. A manual "Recheck" button re-runs the fetch for users who have just updated `.env` and restarted the server.

**OPEN DECISION 6 — Mock strategy for `SettingsPage.test.tsx`.**

Switch from `vi.spyOn(globalThis, "fetch")` to module-level `vi.mock("../api", ...)`. This is required because `SettingsPage` now mounts `EnvHealthPanel`, which calls `fetchEnvHealth`. With global fetch spying, the order of fetch calls becomes fragile. Module-level mocks isolate each function cleanly.

**AMBIGUITY 1 — `onUpdate` → `onChange` rename.**

`SettingsRow.onUpdate` becomes `onChange: (model: string) => void`. This is a breaking change to the row interface. The call site in `SettingsPage` becomes `onChange={(model) => handleUpdate(key, { model })}`. Be consistent across the component, its tests, and the page.

**AMBIGUITY 2 — Env panel shows all vars, not just a summary.**

When `status: "ok"`, all present vars are listed with ✓ indicators (not just "All good"). This avoids the silent-success failure mode where a user can't tell which keys are actually loaded.

**AMBIGUITY 3 — `EnvHealthPanel` position in `SettingsPage`.**

Render `EnvHealthPanel` above the LLM config table, below the page subtitle. The user first sees whether the environment is configured correctly, then configures model names.

---

## `GET /api/health/env` Response Shape (Canonical)

From `narrative/server.py` `_check_env()`:

```json
{
  "status": "ok" | "degraded",
  "detail": "<string>",
  "present": ["DEEPSEEK_API_KEY", "..."],
  "missing": ["OPENAI_API_KEY", "..."]
}
```

Required vars (per `_REQUIRED_ENV_VARS` in `server.py`):
`DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `BRIGHTDATA_API_KEY`, `BRIGHTDATA_SERP_ZONE`, `BRIGHTDATA_UNLOCKER_ZONE`

---

## Step-by-Step Implementation

### Step 1: Add `EnvHealth` type to `types.ts`

**File:** `dashboard/src/types.ts`

Append after `PipelineEvent` at the bottom of the file:

```typescript
export interface EnvHealth {
  status: "ok" | "degraded";
  detail: string;
  present: string[];
  missing: string[];
}
```

`LLMSlotConfig` and `LLMConfig` are NOT changed.

- [ ] **Step 1.1:** Append `EnvHealth` interface to `dashboard/src/types.ts`.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx tsc --noEmit
```
Expected: No errors.
```bash
grep -n "LLMSlotConfig\|LLMConfig" /home/afshin/Documents/dev/narrative-alpha/dashboard/src/types.ts
```
Expected: Same lines as before the change — not modified.

---

### Step 2: Add `fetchEnvHealth` to `api.ts`

**File:** `dashboard/src/api.ts`

Update the import line:
```typescript
import type { ForensicReport, ClusterSummary, LLMConfig, PipelineEvent, EnvHealth } from "./types";
```

Add after `saveConfig`, before `submitPipeline`:
```typescript
export function fetchEnvHealth(): Promise<EnvHealth> {
  return fetchJson<EnvHealth>(`${BASE}/health/env`);
}
```

- [ ] **Step 2.1:** Add `EnvHealth` to the import in `dashboard/src/api.ts`.
- [ ] **Step 2.2:** Add `fetchEnvHealth()` function.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx tsc --noEmit
```
Expected: No errors.
```bash
grep "fetchEnvHealth" /home/afshin/Documents/dev/narrative-alpha/dashboard/src/api.ts
```
Expected: Two lines (export declaration + return statement).

---

### Step 3: Add `fetchEnvHealth` tests to `api.test.ts`

**File:** `dashboard/src/api.test.ts`

Append at the bottom:

```typescript
describe("fetchEnvHealth", () => {
  it("calls /api/health/env and returns env health object", async () => {
    const fake = { status: "ok", detail: "All required vars set", present: ["DEEPSEEK_API_KEY"], missing: [] };
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fake) } as Response);
    const { fetchEnvHealth } = await import("./api");
    const result = await fetchEnvHealth();
    expect(result).toEqual(fake);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/health/env");
  });

  it("throws on non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false, status: 500, statusText: "Internal Server Error",
      json: () => Promise.reject(new Error("not JSON")),
    } as Response);
    const { fetchEnvHealth } = await import("./api");
    await expect(fetchEnvHealth()).rejects.toThrow("GET /api/health/env failed (500): Internal Server Error");
  });
});
```

- [ ] **Step 3.1:** Add `fetchEnvHealth` tests to `dashboard/src/api.test.ts`.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx vitest run src/api.test.ts
```
Expected: All previous tests pass + 2 new ones.

---

### Step 4: Simplify `SettingsRow.tsx`

**File:** `dashboard/src/components/SettingsRow.tsx`

Replace entire file content. The new component has three display props and one callback. Remove: `PROVIDERS` constant, `provider` prop, `thinking` prop, `temperature` prop, `<select>` element, `<input type="range">` element, thinking toggle div. Rename `onUpdate` → `onChange: (model: string) => void`.

```typescript
interface SettingsRowProps {
  slotName: string;
  slotDescription: string;
  model: string;
  onChange: (model: string) => void;
}

export function SettingsRow({ slotName, slotDescription, model, onChange }: SettingsRowProps) {
  return (
    <div className="settings-row">
      <div className="settings-slot">
        {slotName}
        <div className="settings-slot-sub">{slotDescription}</div>
      </div>
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

- [ ] **Step 4.1:** Replace `dashboard/src/components/SettingsRow.tsx` with the simplified version.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx tsc --noEmit 2>&1 | grep SettingsRow
```
Expected: TypeScript errors referencing old props will appear in `SettingsPage.tsx`. These are expected — resolved in Step 8. No errors in `SettingsRow.tsx` itself.

---

### Step 5: Rewrite `SettingsRow.test.tsx`

**File:** `dashboard/src/components/SettingsRow.test.tsx`

Replace entire file. Remove all 6 existing tests (they test provider select, temperature slider, thinking checkbox — none of which exist in the new component). Write 6 new tests:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SettingsRow } from "./SettingsRow";

const defaultProps = {
  slotName: "Call 1",
  slotDescription: "Entity normalization",
  model: "deepseek-v4-flash",
  onChange: vi.fn(),
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

  it("does not render a provider select", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(screen.queryByRole("combobox")).toBeNull();
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

- [ ] **Step 5.1:** Replace `dashboard/src/components/SettingsRow.test.tsx`.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx vitest run src/components/SettingsRow.test.tsx
```
Expected: 6 tests pass.

---

### Step 6: Create `EnvHealthPanel.tsx`

**File:** `dashboard/src/components/EnvHealthPanel.tsx` (new)

```typescript
import { useState, useEffect, useCallback } from "react";
import type { EnvHealth } from "../types";
import { fetchEnvHealth } from "../api";

export function EnvHealthPanel() {
  const [health, setHealth] = useState<EnvHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchEnvHealth()
      .then(setHealth)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="env-health-panel">
      <h3 className="env-health-title">Environment Variables</h3>
      {loading && <p className="loading">Checking environment…</p>}
      {error && <p className="error">Could not load env status: {error}</p>}
      {!loading && !error && health && (
        <>
          <ul className="env-var-list">
            {health.present.map((v) => (
              <li key={v} className="env-var env-var--present">
                <span className="env-var-indicator" aria-hidden="true">✓</span>
                <code>{v}</code>
              </li>
            ))}
            {health.missing.map((v) => (
              <li key={v} className="env-var env-var--missing">
                <span className="env-var-indicator" aria-hidden="true">✗</span>
                <code>{v}</code>
                <span className="env-var-hint">Not set — add to .env and restart server</span>
              </li>
            ))}
          </ul>
          {health.status === "ok" && (
            <p className="env-health-ok">All required variables are set.</p>
          )}
        </>
      )}
      <button className="btn-reload-env" onClick={load} disabled={loading}>
        {loading ? "Checking…" : "Recheck"}
      </button>
    </div>
  );
}
```

- [ ] **Step 6.1:** Create `dashboard/src/components/EnvHealthPanel.tsx`.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx tsc --noEmit
```
Expected: No errors (Steps 1 and 2 must be complete first).

---

### Step 7: Create `EnvHealthPanel.test.tsx`

**File:** `dashboard/src/components/EnvHealthPanel.test.tsx` (new)

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return { ...actual, fetchEnvHealth: vi.fn() };
});

import { fetchEnvHealth } from "../api";
import { EnvHealthPanel } from "./EnvHealthPanel";

beforeEach(() => { vi.clearAllMocks(); });

describe("EnvHealthPanel — loading", () => {
  it("shows loading state initially", () => {
    vi.mocked(fetchEnvHealth).mockReturnValue(new Promise(() => {}));
    render(<EnvHealthPanel />);
    expect(screen.getByText(/Checking environment/i)).toBeTruthy();
  });
});

describe("EnvHealthPanel — all present", () => {
  it("renders present vars with check indicator", async () => {
    vi.mocked(fetchEnvHealth).mockResolvedValueOnce({
      status: "ok", detail: "All required vars set",
      present: ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"], missing: [],
    });
    render(<EnvHealthPanel />);
    expect(await screen.findByText("DEEPSEEK_API_KEY")).toBeTruthy();
    expect(await screen.findByText("OPENAI_API_KEY")).toBeTruthy();
    expect(await screen.findByText(/All required variables are set/i)).toBeTruthy();
  });

  it("does not render any missing-var items when all present", async () => {
    vi.mocked(fetchEnvHealth).mockResolvedValueOnce({
      status: "ok", detail: "All required vars set",
      present: ["DEEPSEEK_API_KEY"], missing: [],
    });
    render(<EnvHealthPanel />);
    await screen.findByText("DEEPSEEK_API_KEY");
    expect(document.querySelectorAll(".env-var--missing").length).toBe(0);
  });
});

describe("EnvHealthPanel — degraded", () => {
  it("renders missing vars with hint text", async () => {
    vi.mocked(fetchEnvHealth).mockResolvedValueOnce({
      status: "degraded", detail: "Missing: OPENAI_API_KEY",
      present: ["DEEPSEEK_API_KEY"], missing: ["OPENAI_API_KEY"],
    });
    render(<EnvHealthPanel />);
    expect(await screen.findByText("OPENAI_API_KEY")).toBeTruthy();
    expect(await screen.findByText(/Not set — add to .env/i)).toBeTruthy();
  });

  it("does not show all-ok message when status is degraded", async () => {
    vi.mocked(fetchEnvHealth).mockResolvedValueOnce({
      status: "degraded", detail: "Missing: OPENAI_API_KEY",
      present: ["DEEPSEEK_API_KEY"], missing: ["OPENAI_API_KEY"],
    });
    render(<EnvHealthPanel />);
    await screen.findByText("OPENAI_API_KEY");
    expect(screen.queryByText(/All required variables are set/i)).toBeNull();
  });
});

describe("EnvHealthPanel — error", () => {
  it("shows error message when fetch fails", async () => {
    vi.mocked(fetchEnvHealth).mockRejectedValueOnce(new Error("Network error"));
    render(<EnvHealthPanel />);
    expect(await screen.findByText(/Could not load env status/i)).toBeTruthy();
    expect(await screen.findByText(/Network error/i)).toBeTruthy();
  });
});

describe("EnvHealthPanel — recheck", () => {
  it("re-fetches when Recheck is clicked", async () => {
    vi.mocked(fetchEnvHealth)
      .mockResolvedValueOnce({ status: "ok", detail: "", present: ["DEEPSEEK_API_KEY"], missing: [] })
      .mockResolvedValueOnce({ status: "ok", detail: "", present: ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"], missing: [] });
    render(<EnvHealthPanel />);
    await screen.findByText("DEEPSEEK_API_KEY");
    await userEvent.click(screen.getByRole("button", { name: /Recheck/i }));
    expect(await screen.findByText("OPENAI_API_KEY")).toBeTruthy();
    expect(fetchEnvHealth).toHaveBeenCalledTimes(2);
  });
});
```

- [ ] **Step 7.1:** Create `dashboard/src/components/EnvHealthPanel.test.tsx`.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx vitest run src/components/EnvHealthPanel.test.tsx
```
Expected: All 7 tests pass.

---

### Step 8: Update `SettingsPage.tsx`

**File:** `dashboard/src/components/SettingsPage.tsx`

Changes:
1. Add `import { EnvHealthPanel } from "./EnvHealthPanel";`
2. Remove `provider`, `thinking`, `temperature` from `<SettingsRow>` call sites.
3. Change `onUpdate` → `onChange={(model) => handleUpdate(key, { model })}` on each row. `handleUpdate` signature is unchanged (still takes `Partial<LLMSlotConfig>`); the call site narrows the argument.
4. Update `.settings-header` div to contain only two cells: "Call Slot" and "Model".
5. Mount `<EnvHealthPanel />` between the `<p className="section-subtitle">` and the `<div className="settings-table">`.

**Critical wire-compatibility note:** `handleUpdate` merges `{ model }` into the existing slot state. Since all four fields (`provider`, `thinking`, `temperature`, `model`) were loaded from the backend via `fetchConfig` and stored in state, merging only `{ model }` leaves the other three intact. The `handleSave` function calls `saveConfig(config)` where `config` is the full `LLMConfig` object in state — all four fields per slot are submitted, satisfying the backend's `extra="forbid"` requirement.

- [ ] **Step 8.1:** Add `EnvHealthPanel` import to `SettingsPage.tsx`.
- [ ] **Step 8.2:** Update each `<SettingsRow>` — remove `provider`, `thinking`, `temperature` props; change `onUpdate` to `onChange`.
- [ ] **Step 8.3:** Update `.settings-header` div to two cells only: "Call Slot" and "Model".
- [ ] **Step 8.4:** Mount `<EnvHealthPanel />` above the settings table.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx tsc --noEmit
```
Expected: No errors.

---

### Step 9: Update `SettingsPage.test.tsx`

**File:** `dashboard/src/components/SettingsPage.test.tsx`

Switch from `vi.spyOn(globalThis, "fetch")` to module-level `vi.mock("../api", ...)`. This is required because the page now also calls `fetchEnvHealth`, and two concurrent fetch spies become fragile.

Add at the top of the file (after imports):

```typescript
const fakeConfig = {
  call_1_entity_normalization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_2_linguistic_neutralization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_3_graph_extraction: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
  call_4_forensic_synthesis: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
};

const fakeEnvHealth = {
  status: "ok" as const, detail: "All required vars set",
  present: ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "BRIGHTDATA_API_KEY", "BRIGHTDATA_SERP_ZONE", "BRIGHTDATA_UNLOCKER_ZONE"],
  missing: [],
};

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    fetchConfig: vi.fn().mockResolvedValue(fakeConfig),
    saveConfig: vi.fn().mockResolvedValue({ status: "ok", config: fakeConfig }),
    fetchEnvHealth: vi.fn().mockResolvedValue(fakeEnvHealth),
  };
});
```

Remove `vi.spyOn(globalThis, "fetch")` from all existing test bodies. Each test now relies on the module-level mock. Update `beforeEach` to `vi.clearAllMocks()` only.

Tests to remove:
- `"shows Call 3 thinking = true from backend"` — removed UI element, no longer valid

Tests to keep (adjusted for new mock strategy):
- `"shows loading state initially"` — override `fetchConfig` mock to never resolve: `vi.mocked(fetchConfig).mockReturnValue(new Promise(() => {}))`
- `"renders settings rows after fetch"` — uses module-level mock; asserts on Call 1 / Call 4 labels
- `"renders save button after fetch"` — uses module-level mock
- `"shows error message when fetch fails"` — override `fetchConfig` mock to reject

Test to add:
```typescript
it("renders EnvHealthPanel with env var status", async () => {
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText("Environment Variables")).toBeTruthy();
});
```

- [ ] **Step 9.1:** Add `fakeConfig`, `fakeEnvHealth`, and `vi.mock("../api", ...)` block to `SettingsPage.test.tsx`.
- [ ] **Step 9.2:** Remove `vi.spyOn(globalThis, "fetch")` from all test bodies; adjust tests for module-level mocks.
- [ ] **Step 9.3:** Remove `"shows Call 3 thinking = true from backend"` test.
- [ ] **Step 9.4:** Add `"renders EnvHealthPanel with env var status"` test.

**Verification:**
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx vitest run src/components/SettingsPage.test.tsx
```
Expected: All remaining tests pass.

---

### Step 10: Update `index.css`

**File:** `dashboard/src/index.css`

Two changes:

**Change 1 — Narrow settings grid to 2 columns.**

Find and update `grid-template-columns` for `.settings-header` and `.settings-row`:

Before (5-column): `grid-template-columns: 170px 1fr 1fr 120px 90px;`
After (2-column):  `grid-template-columns: 200px 1fr;`

Also update the `@media (max-width: 640px)` responsive block — the grid already collapses to `1fr` there, which still works.

**Change 2 — Add env health panel styles.**

Add the following CSS block after the existing `.thinking-toggle` rule (or at the end of the settings section):

```css
/* Env health panel */
.env-health-panel {
  background: var(--bg-secondary);
  border: 0.5px solid var(--border-faint);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  margin-bottom: 16px;
}
.env-health-title {
  font-size: var(--fs-md);
  font-weight: bold;
  color: var(--text-secondary);
  letter-spacing: 0.07em;
  margin-bottom: 10px;
}
.env-var-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}
.env-var {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: var(--fs-sm);
}
.env-var code { font-family: var(--font-mono); font-size: var(--fs-xs); }
.env-var--present .env-var-indicator { color: var(--green-text); }
.env-var--missing .env-var-indicator { color: var(--red-text); }
.env-var--missing code { color: var(--red-text); }
.env-var-hint { color: var(--text-tertiary); font-size: var(--fs-xs); }
.env-health-ok { font-size: var(--fs-sm); color: var(--green-text); margin-bottom: 10px; }
.btn-reload-env {
  font-size: var(--fs-xs);
  padding: 4px 12px;
  border-radius: var(--radius-md);
  border: 0.5px solid var(--border-med);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
  font-family: var(--font-mono);
}
.btn-reload-env:hover { color: var(--text-primary); border-color: var(--border-strong); }
.btn-reload-env:disabled { opacity: 0.5; cursor: default; }
```

**Note on CSS variables:** The styles above assume the project uses CSS custom properties (`--bg-secondary`, `--border-faint`, `--green-text`, `--red-text`, etc.). If these variables are not defined in `index.css`, the implementer must substitute appropriate values or define them. **Check the existing variable definitions before applying.**

- [ ] **Step 10.1:** Update `grid-template-columns` for `.settings-header` and `.settings-row` to `200px 1fr`.
- [ ] **Step 10.2:** Add env health panel CSS rules.

**Verification:**
```bash
grep "grid-template-columns" /home/afshin/Documents/dev/narrative-alpha/dashboard/src/index.css
```
Expected: `200px 1fr` for both settings classes.
```bash
grep "env-health\|env-var" /home/afshin/Documents/dev/narrative-alpha/dashboard/src/index.css | wc -l
```
Expected: At least 10 lines.

---

### Step 11: Full verification

- [ ] **Step 11.1:** TypeScript check.
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 11.2:** Full frontend test suite.
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx vitest run
```
Expected: All tests pass. Net change vs. pre-rework: +2 `api.test.ts`, +6 `SettingsRow`, +7 `EnvHealthPanel`, +1 `SettingsPage` added; −6 `SettingsRow`, −1 `SettingsPage` removed.

- [ ] **Step 11.3:** Build check.
```bash
cd /home/afshin/Documents/dev/narrative-alpha/dashboard && npx vite build
```
Expected: Clean build, no unused-import warnings for removed row props.

- [ ] **Step 11.4:** Backend env endpoint smoke test.
```bash
curl -s http://localhost:3001/api/health/env | python3 -m json.tool
```
Expected: JSON with `status`, `detail`, `present`, `missing` fields.

- [ ] **Step 11.5:** Manual UI — env panel.
Open Settings. Verify: env health panel appears above the LLM table; each var shows ✓ or ✗; "Recheck" triggers a visible network request in DevTools.

- [ ] **Step 11.6:** Manual UI — save round-trip.
Change a model name. Click "Save Configuration". Verify "Saved" appears. Check `~/.narrative_alpha/llm_config.json` — `provider`, `thinking`, and `temperature` must be present and unchanged. Confirms the frontend did not strip those fields.

---

## Design Notes

**`LLMSlotConfig` and `LLMConfig` are unchanged** on both frontend and backend. All four fields continue to flow through the system. The UI simply exposes only `model` as editable.

**`SettingsRow` is simplified, not deleted.** Four identical rows still benefit from a shared component.

**`EnvHealthPanel` fetches independently.** It shows env status even if the config fetch fails — a new user needs env feedback even before `llm_config.json` exists.

**No backend changes.** All three endpoints used (`GET /api/health/env`, `GET /api/config`, `POST /api/config`) exist and are unchanged.
