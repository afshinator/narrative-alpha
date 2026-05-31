# Post-Hackathon Fixes — TDD Plan

**Context:** After the hackathon, four actionable issues remain with clear code-level fixes. This plan implements them test-first (red → green → refactor).

---

## Fix A: Wire `tbs` time filter into pipeline SERP queries

**Problem:** `_run_pipeline()` in `narrative/pipeline.py` calls `discover_articles(keyword, serp_zone, api_key)` without the `time_range` parameter. The function supports it (`time_range="m"` → `&tbs=qdr:m`), and `backtest.py` already uses it (`time_range="y"`). Without it, demo runs return stale articles, increasing the floor-gate risk.

**Files:**
| File | Change | TDD step |
|------|--------|----------|
| `narrative/pipeline.py` | Pass `time_range="m"` from `_run_pipeline` to `discover_articles` | Green |
| `narrative/ingestion.py` | No change needed — `discover_articles` already supports `time_range` | — |
| `tests/test_ingestion.py` | Already has `test_appends_time_range_when_set` and `test_omits_time_range_by_default` | Already passing |

**Plan:**
1. **Red: NOT needed** — existing tests cover `time_range` at the `discover_articles` level.
2. **Green (pipeline.py):** Add `time_range="m"` to the `discover_articles` call in `_run_pipeline`:

   Current: `serp_data = discover_articles(keyword, serp_zone, api_key)`
   New:     `serp_data = discover_articles(keyword, serp_zone, api_key, time_range="m")`

3. **Verify:** Run `pytest tests/test_ingestion.py -v -k "time_range"` to confirm existing tests pass.

---

## Fix B: Fix backtest thread timing for first-run reputation

**Problem:** `_run_pipeline()` spawns backtest daemon threads for UNRATED outlets, then immediately reads `reputation_records`. The threads finish after the pipeline, so first-run outlets get `null` SA factor. The second pipeline run picks up the cached value.

**Files:**
| File | Change | TDD step |
|------|--------|----------|
| `narrative/pipeline.py` | Make backtests synchronous; re-read reputation after completion | Green |
| `narrative/backtest.py` | No change needed | — |
| `tests/test_backtest.py` | Add test verifying synchronous execution with reputation update | Red → Green |

**Plan:**

1. **Red (test):** Add a test to `tests/test_backtest.py` that:
   - Spawns `execute_historical_backtest("example.com", "TECHNOLOGY")` synchronously
   - Verifies it returns normally (returns `None` but completes without error)
   - Verifies the DB was updated (via mocked connection)

   (Backtest tests already exist — what's missing is a test proving the reputation read-after-backtest pattern works end-to-end.)

2. **Green (pipeline.py):** Replace the daemon-thread spawn with synchronous execution + re-read:

   ```python
   unrated_domains = []
   for doc in documents:
       status = handle_outlet_registration(doc["source_domain"], vertical, db_conn, ...)
       rep = read_outlet_reputation(doc["source_domain"], vertical, db_conn)
       reputation_records[doc["source_domain"]] = rep or {"rating_status": "UNRATED"}
       if status == "UNRATED":
           unrated_domains.append(doc["source_domain"])

   # Run backtests synchronously for new outlets
   for domain in unrated_domains:
       execute_historical_backtest(domain, vertical)

   # Re-read reputation now that backtests have populated it
   if unrated_domains:
       for domain in unrated_domains:
           rep = read_outlet_reputation(domain, vertical, db_conn)
           if rep:
               reputation_records[domain] = rep
   ```

3. **Verify:** Run `pytest tests/test_backtest.py -v` to confirm all backtest tests still pass.

---

## Fix C: Make consensus threshold configurable

**Problem:** `compute_consensus_baseline()` hardcodes `threshold = int(0.75 * n) + 1`. With 9 diverse sources, this requires 7/9 to agree — rarely met, triggering `_degraded: "INSUFFICIENT_CONSENSUS"`.

**Files:**
| File | Change | TDD step |
|------|--------|----------|
| `narrative/analysis.py` | Add `consensus_ratio` parameter (default 0.75) to `compute_consensus_baseline`; lower default for small corpora or accept caller override | Green |
| `narrative/pipeline.py` | Pass `consensus_ratio=0.60` for small corpora (≤15 docs) | Green |
| `tests/test_analysis.py` | Add tests for custom ratio values and the caller-override pattern | Red → Green |

**Plan:**

1. **Red (test):** Add tests to `tests/test_analysis.py`:
   - `test_custom_threshold_60_percent`: With 5 sources (4/5 agree at 75% threshold, test 3/5 agree at 60%)
   - `test_custom_threshold_returns_more_nodes`: With 9 sources (6/9 fails at 75%, passes at 60%)
   - `test_threshold_passed_through_from_pipeline`: (integration-level, or skip if hard to mock)

2. **Green (analysis.py):** Add optional `consensus_ratio` parameter to `compute_consensus_baseline`:

   ```python
   def compute_consensus_baseline(
       all_graphs: list[dict],
       canonical_map: dict[str, str],
       consensus_ratio: float = 0.60,  # new default
   ) -> set[str]:
       ...
       threshold = int(consensus_ratio * n) + 1
       ...
   ```

3. **Green (pipeline.py):** `_run_pipeline` already calls `compute_consensus_baseline(all_graphs, canonical_map)`. The new default of 0.60 will apply automatically. No change needed unless we want dynamic ratio based on corpus size.

4. **Verify:** Run `pytest tests/test_analysis.py -v -k "consensus_baseline"` to confirm existing tests still pass with the new default.

   **⚠️ Existing-test impact check:** Current tests use `compute_consensus_baseline(graphs, {})` with 5 sources and expect 4/5 threshold. With a 60% default, `int(0.60 * 5) + 1 = 4` — same result. However, the `test_threshold_with_6_sources` test expects threshold = `int(0.75 * 6) + 1 = 5`. With 60%: `int(0.60 * 6) + 1 = 4` — behavior changes! Solution: Use 0.75 in the test explicitly, OR update expectations. Since the test name says "threshold_with_6_sources" and doesn't name a specific value, we should pass `consensus_ratio=0.75` in those existing tests that rely on the old behavior.

---

## Fix D: Pulsing animation for UNRESOLVED convergence status

**Problem:** Spec requires a pulsing CSS animation for `UNRESOLVED` convergence status. The CSS class `.status-unresolved` exists with static styling but no animation.

**Files:**
| File | Change | TDD step |
|------|--------|----------|
| `dashboard/src/index.css` | Add `@keyframes pulse` and apply to `.status-unresolved` and `.pending-badge` | Green |
| `dashboard/src/components/Zone3.tsx` | No change needed — already renders `status-${...}` class names | — |
| `dashboard/src/components/Zone3.test.tsx` | Add test verifying pulsing class is present | Red |

**Plan:**

1. **Red (test):** Add a test to `Zone3.test.tsx`:
   ```tsx
   it("applies pulsing animation to UNRESOLVED convergence status", () => {
     // Create a report with UNRESOLVED convergence
     // Verify the rendered element has the expected animation classes
   });
   ```

2. **Green (index.css):** Add CSS:

   ```css
   @keyframes pulse {
     0%, 100% { opacity: 1; }
     50% { opacity: 0.5; }
   }

   .status-unresolved {
     background: var(--red-bg);
     color: var(--red-text);
     border: 0.5px solid var(--red-border);
     animation: pulse 2s ease-in-out infinite;
   }

   .status-pending {
     animation: pulse 2s ease-in-out infinite;
   }
   ```

3. **Verify:** `cd dashboard && npx vitest run src/components/Zone3.test.tsx && npx tsc --noEmit`

---

## Execution Order

```
Fix A (trivial, no new tests needed)
  └─→ Fix B (backtest sync, core data correctness)
       └─→ Fix C (consensus threshold, core analysis fix)
            └─→ Fix D (CSS polish, isolated from backend)
```

---

## Verification Checklist (run after all fixes)

- [ ] `pytest tests/ -v` — all 289 Python tests pass
- [ ] `cd dashboard && npx vitest run` — all 103 JS tests pass
- [ ] `cd dashboard && npx tsc --noEmit` — no TypeScript errors
- [ ] `cd dashboard && npm run build` — production build succeeds
- [ ] Manual: run `./start-demo.sh` and verify dashboard loads at `http://localhost:5173`
