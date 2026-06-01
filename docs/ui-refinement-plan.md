# UI Refinement Plan

Based on ui-designer review of the Narrative Alpha dashboard. 6 focus areas,
ordered by impact.

**Existing files (no new components):**
- `dashboard/src/index.css` — global styles, CSS custom properties
- `dashboard/src/components/Zone3.tsx` — reputation warnings, outlier signals, gaps
- `dashboard/src/components/Zone2.tsx` — distortion table, regime shifts
- `dashboard/src/components/HomePage.tsx` — pipeline runner, input
- `dashboard/src/components/EventPage.tsx` — 3-zone report layout
- `dashboard/src/components/PipelineRunner.tsx` — SSE progress + article list
- `dashboard/src/components/Badge.tsx` — color-coded label pill
- `dashboard/src/components/SettingsPage.tsx` — settings form
- `dashboard/src/components/SettingsRow.tsx` — per-slot settings row

---

## Task 1: Font System — Proportional + Monospace

**Problem:** Entire app uses `--font-mono` (Courier New). Dense prose
(`consensus_summary`, regime shift notes, warning messages) is harder to read
in monospace.

**Changes:**

| File | Change |
|------|--------|
| `index.css` | Add `--font-sans` custom property; keep `--font-mono` for data |
| `index.css` | Set body default to `--font-sans`; override data-heavy elements to `--font-mono` |
| `index.css` | Adjust line-height for proportional font (1.5 vs 1.3) |

**Affected elements (sans-serif):**
- `.consensus-summary` — Zone 1 prose
- `.regime-note` — narrative shift interpretation
- `.rep-warning-body` — warning descriptions
- `.outlier-claim` — outlier signal text
- `.camouflage` columns — raw/clean text pairs
- `.pipeline-input-section label` — form labels
- Settings descriptions / help text

**Affected elements (keep monospace):**
- `.zone-header` — forensic console headers
- Table cells with scores
- `.badge` label text
- `.outlet-domain` display
- `.phase-name` pipeline steps
- Code-like displays

**Verify:** `npx vitest run`, visual check that prose sections use sans-serif,
data sections use monospace, no regressions in alignment/spacing.

---

## Task 2: Visual Hierarchy — Warning Weight

**Problem:** Reputation warnings and outlier cards share the same background/border
as everything else. Critical signals don't stand out.

**Changes:**

| File | Change |
|------|--------|
| `index.css` | Add `--warning-bg`, `--warning-border` custom properties (darker red bg) |
| `index.css` | `.rep-warning` gets elevated background + slightly thicker border |
| `index.css` | `.outlier-card` gets amber accent left-border instead of full border |
| `index.css` | Zone sub-headers get subtle top-border separator |

**Verify:** `npx vitest run`, visual check that warnings visually pop,
outlier cards are distinct from warning cards, hierarchy reads correctly
without color alone.

---

## Task 3: Accessibility

**Problem:** Badges use color-only for level signaling. No focus indicators on
form elements. Emoji statuses are opaque to screen readers. Camouflage pairs
lack accessible descriptions.

### 3a — Focus indicators

**Changes:**

| File | Change |
|------|--------|
| `index.css` | Add `:focus-visible` outline style for `input`, `select`, `button` |

### 3b — Badge text signaling

**Changes:**

| File | Change |
|------|--------|
| `Badge.tsx` | Add `aria-label` prefixed with level name: `"High: 0.65 HIGH"` |

### 3c — Emoji accessibility in PipelineRunner

**Changes:**

| File | Change |
|------|--------|
| `PipelineRunner.tsx` | Add `aria-hidden="true"` to emoji spans; add `aria-label` to parent wrapping the full status text |

### 3d — Camouflage screen reader context

**Changes:**

| File | Change |
|------|--------|
| `Zone2.tsx` | Add `aria-label` to `.camouflage` cells: `"Raw: {raw} → Neutralized: {clean}"` |

**Verify:** `npx vitest run`, tab through form elements to verify visible
focus ring, inspect with browser DevTools for aria attributes.

---

## Task 4: Zone 3 — Empty State Gracefulness

**Problem:** When `reputation_warnings`, `reality_fractures`, etc. are empty,
sub-headers and sections disappear abruptly. Zone can look bare or jump
when data loads.

**Changes:**

| File | Change |
|------|--------|
| `Zone3.tsx` | Add "No reputation warnings flagged" placeholder when warning list is empty (still show the sub-header) |
| `Zone3.tsx` | Same for fractures and divergence zones (show sub-header + "None detected") |
| `index.css` | Add `.empty-placeholder` style (dimmed, italic, muted color) |

**Verify:** `npx vitest run`, inspect a report with no warnings/fractures
to confirm placeholders render instead of blank space.

---

## Task 5: Distortion Table Responsiveness

**Problem:** Fixed column widths (26/13/13/48%) don't scale well. Multiple
camouflage entries stack vertically and can overflow on narrower viewports.

**Changes:**

| File | Change |
|------|--------|
| `index.css` | Add `overflow-x: auto` to `.distortion-table` wrapper or to `table` itself |
| `index.css` | Collapse camouflage column to readable minimum at `<768px` |
| `index.css` | Add `@media (max-width: 768px)` rule making table horizontal-scroll |

**Verify:** `npx vitest run`, resize browser to 600px width, verify table
scrolls horizontally without breaking layout.

---

## Task 6: Motion Design Tokens

**Problem:** No defined timing scale or easing curve. Pulse animation is hardcoded.
Hover transitions are ad-hoc 0.15s.

**Changes:**

| File | Change |
|------|--------|
| `index.css` | Add `--duration-fast: 150ms`, `--duration-normal: 250ms`, `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)` |
| `index.css` | Replace hardcoded `0.15s` with `var(--duration-fast)` in existing transitions |
| `index.css` | Replace `ease-in-out infinite` in `@keyframes pulse` with `var(--ease-out)` |
| Spot-check existing `.card:hover`, `.zone-header:hover`, `.badge` transitions |

**Verify:** `npx vitest run`, visual check that hover states still feel
responsive and pulse animation is smooth.

---

## Verification Checklist (run after all tasks)

- [ ] `cd dashboard && npx vitest run` — all JS tests pass
- [ ] `cd dashboard && npx tsc --noEmit` — clean TypeScript
- [ ] `cd dashboard && npm run build` — production build succeeds
- [ ] Manual: tab through HomePage inputs → visible focus ring
- [ ] Manual: load a report with no reputation_warnings → placeholder shown
- [ ] Manual: shrink browser to 600px → table scrolls horizontally
- [ ] Manual: prose sections render in sans-serif, data sections in monospace
