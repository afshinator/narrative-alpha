# Task 9 — Dashboard Implementation Plan (React + Vite)

**Date:** 2026-05-29
**Stack:** React 19, Vite 7, TypeScript, react-router-dom (hash-based), vanilla CSS
**Target:** Local dev only (`npx vite` → `localhost:5173`), no deployment

## Architecture

Single-page app with hash-based routing:

```
/#/                  → ClusterListPage   (list of processed clusters)
/#/event/:clusterId  → EventReportPage   (3-zone forensic report)
/#/settings          → SettingsPage      (LLM provider config)
```

All data embedded as a TypeScript module — no API calls, no backend dependency.

## File Structure

```
dashboard/
├── index.html              Vite entry point (SPA shell)
├── package.json            Dependencies: react, react-dom, react-router-dom
├── tsconfig.json           Strict TypeScript config
├── vite.config.ts          Vite config (port 5173, no build target)
├── src/
│   ├── main.tsx            React root + BrowserRouter → HashRouter
│   ├── App.tsx             Route definitions
│   ├── index.css           Global styles (ported from docs/preview-01.html)
│   ├── data/
│   │   └── sample-data.ts  Embedded ForensicReport[] + cluster list
│   ├── types.ts            TypeScript interfaces matching contracts.py models
│   ├── pages/
│   │   ├── ClusterListPage.tsx   Cluster list view (index)
│   │   ├── EventReportPage.tsx   Single cluster report (3 zones)
│   │   └── SettingsPage.tsx      LLM config form
│   ├── components/
│   │   ├── Header.tsx            Console header with cluster ID, meta
│   │   ├── Nav.tsx               Tab-style navigation
│   │   ├── Zone1.tsx             Consensus Truth Baseline
│   │   ├── Zone2.tsx             Distortion Matrix + Regime Shifts
│   │   ├── Zone3.tsx             Outlier Signals + Divergence + Fractures
│   │   ├── DistortionTable.tsx   Oi/Vf table with camouflage
│   │   ├── RegimeShiftCard.tsx   Narrative regime shift card
│   │   ├── OutlierSignalCard.tsx Single outlier card
│   │   ├── ReputationWarning.tsx Reputation warning banner
│   │   ├── DivergenceBlock.tsx   Reality divergence zone block
│   │   ├── FractureCard.tsx      Reality fracture card
│   │   ├── Badge.tsx             Color-coded label badge (LOW/MED/HIGH)
│   │   ├── Pill.tsx              Node pill for anchor nodes
│   │   └── SettingsRow.tsx       Per-slot settings form row
│   └── utils/
│       └── labels.ts             Status → color mappings, thresholds
```

## Implementation Steps

### Step 1: Scaffold project

```bash
cd dashboard
npm create vite@latest . -- --template react-ts
npm install react-router-dom
rm -rf src/App.css src/App.tsx src/index.css   # we'll write our own
```

### Step 2: Write `index.css` — Global styles

Port all CSS from `docs/preview-01.html` lines 7-271, plus add:

- **Pulsing animation** for UNRESOLVED convergence status (`@keyframes pulse-unresolved`)
- **Temperature slider** styles (`input[type="range"]`) for settings
- **Corpus-capped indicator** style (small amber badge in header)

### Step 3: Write `types.ts` — TypeScript interfaces

Mirror contracts.py models: `ForensicReport`, `EventMeta`, `ConsensusRealityGraph`, `DistortionMatrixEntry`, `OutlierSignal`, `ReputationWarning`, `RealityDivergenceZone`, `RealityFracture`, `NarrativeRegimeShift`, `LLMConfig`, `LLMSlotConfig`, `ClusterSummary`

### Step 4: Write `data/sample-data.ts` — Embedded sample data

One realistic `ForensicReport` matching the preview content (EVT-20260528-TECH-SEMI, Fab 7), plus a `clusterList: ClusterSummary[]` for the index page.

### Step 5: Write utility components

- `Badge.tsx` — `<Badge level="HIGH" label="0.65 HIGH" />` → green/amber/red pill
- `Pill.tsx` — `<Pill>Fab 7</Pill>` → node pill

### Step 6: Write zone components

Build bottom-up, data-driven:

| Component | Data source | Key behavior |
|-----------|-------------|--------------|
| `Zone1.tsx` | `consensus_reality_graph` | Summary text, verified badge, anchor node pills |
| `DistortionTable.tsx` | `distortion_matrix[]` | Table rows with Oi/Vf badges + camouflage pairs |
| `RegimeShiftCard.tsx` | `narrative_regime_shifts[]` | Term arrows, sync badge, source count, note |
| `ReputationWarning.tsx` | `reputation_warnings[]` | Red banner with alert icon, message text |
| `OutlierSignalCard.tsx` | `outlier_signals[]` | Claim text, provenance meta, pending badge |
| `DivergenceBlock.tsx` | `reality_divergence_zones[]` | Topic + stability badges + narrative list |
| `FractureCard.tsx` | `reality_fractures[]` | 2-column claims, classification footer |

### Step 7: Write settings components

`SettingsRow.tsx` — one row per call slot:
- Call slot name + description
- Provider `<select>` (deepseek/openai/google/groq)
- Model `<input type="text">`
- Thinking `<input type="checkbox">` — **visible only when provider === "deepseek"**
- Temperature `<input type="range" min="0" max="2" step="0.1">` — **not in preview, required by spec §9.4**

### Step 8: Write pages

| Page | Route | Contains |
|------|-------|----------|
| `ClusterListPage.tsx` | `/#/` | Header + table of cluster IDs, timestamps, verticals. Click → navigate to event |
| `EventReportPage.tsx` | `/#/event/:clusterId` | Header + `<Zone1>` + `<Zone2>` + `<Zone3>`. Reads from `useParams()` |
| `SettingsPage.tsx` | `/#/settings` | Header + 4 `<SettingsRow>` components + save button. Save logs to console (no Modal POST for demo) |

### Step 9: Write `App.tsx` + `main.tsx`

```tsx
// App.tsx
import { Routes, Route } from "react-router-dom";
import { ClusterListPage } from "./pages/ClusterListPage";
import { EventReportPage } from "./pages/EventReportPage";
import { SettingsPage } from "./pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ClusterListPage />} />
      <Route path="/event/:clusterId" element={<EventReportPage />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Routes>
  );
}
```

```tsx
// main.tsx
import { HashRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import { createRoot } from "react-dom/client";

createRoot(document.getElementById("root")!).render(
  <HashRouter>
    <App />
  </HashRouter>
);
```

### Step 10: Verify

```bash
cd dashboard
npx vite           # opens localhost:5173
# Navigate: /#/ → cluster list, /#/event/EVT-20260528-TECH-SEMI → report, /#/settings → settings
```

## Gap Resolution

| Gap # | Issue | Resolution |
|-------|-------|------------|
| 6 | Temperature slider missing | Added to `SettingsRow` with `<input type="range">` |
| 7 | Thinking toggle visibility | Only renders when `provider === "deepseek"` (JSX conditional) |
| 8 | Corpus-capped indicator | Display in `Zone1` header when `event_meta.corpus_capped === true` |
| 10 | Pulsing animation for UNRESOLVED | `@keyframes pulse-unresolved` in CSS, applied to `.status-unresolved` |
| 14 | No MODAL_ENDPOINT env for settings save | Settings page logs config to console instead of POST (demo mode) |

## What This Plan Does NOT Do

- No Modal deployment wiring (not needed — local demo only)
- No build step for production (Vite dev server only)
- No API integration (sample data is embedded)
- No tests (static UI, verified manually in browser)
