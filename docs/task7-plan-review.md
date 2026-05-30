# Task 7 Plan Review — Ambiguities & Implementation Blockers

**Review date:** 2026-05-30
**Scope:** `docs/superpowers/plans/2026-05-29-narrative-alpha-full.md` Task 7 + Task 12
**Status:** Task 7 is a stub (`pass`). Full implementation deferred to Task 12 ("Phase 2 infrastructure").
**Design decision (2026-05-30):** Backtest model resolved — uses cross-source persistence, not temporal absorption. See Task 12 spec for full details.

---

## High Severity (3)

### 1. What is the "known-consensus baseline"? — **RESOLVED 2026-05-30**

The backtest now runs **two** SERP queries in parallel:
- Query 1: `site:{domain} {vertical}`, `tbs=qdr:y` → target outlet's historical claims
- Query 2: `{vertical}`, `tbs=qdr:y`, no site filter → multi-source consensus baseline

The consensus baseline is built from the second query's results — Call 1 + Call 3 independently, producing a contemporaneous graph of what the broader ecosystem reported at the same time.

### 2. How are "absorbed vs decayed" nodes classified? — **RESOLVED 2026-05-30**

The backtest does NOT use the Section 5 `absorbed`/`decayed` lifecycle. Those terms belong to the real-time `outlier_tracking` system (30-day observation window). The backtest uses distinct terminology:

- **consensus-supported** — claim appears in the multi-source consensus baseline (other outlets reported it too)
- **consensus-isolated** — claim appears only in the target outlet's graph (single-source scatter)

The 30-day temporal absorption model is exclusive to the online pipeline. The cold-start backtest is a **retrospective snapshot** calibrated to produce the same output metrics (`historical_origin_validation_rate`, `scatter_shot_anomaly_factor`) from a single dual-SERP pass rather than longitudinal observation.

Scoring:
```
historical_origin_validation_rate = consensus_supported / total_claims
scatter_shot_anomaly_factor       = consensus_isolated / total_claims
```

### 3. `discover_articles` doesn't support `site:` queries or date ranges — **RESOLVED 2026-05-30**

The plan now specifies the query shapes (`site:{domain} {vertical}` + `tbs=qdr:y`) and provides implementation guidance: the `q` parameter is a plain string so `discover_articles(f"site:{domain} {vertical}", api_key)` works as-is, and `tbs=qdr:y` requires either (a) adding an optional `tbs` kwarg to `discover_articles` in `ingestion.py`, or (b) constructing the payload manually in `backtest.py`.

---

## Low / Resolved (4)

### 4. No public UPDATE function in `reputation.py` for back-test metrics — **LOW**

File: `narrative/reputation.py`

The backtest needs to write these fields to `outlet_reputation`:
- `scatter_shot_anomaly_factor`
- `historical_origin_validation_rate`
- `back_test_article_count`
- `rating_status = 'RATED'`

Current functions:
| Function | Operation | Target |
|---|---|---|
| `handle_outlet_registration` | INSERT or SELECT | New outlets only |
| `read_outlet_reputation` | SELECT | Read existing |
| `_write_with_retry` | Generic | Any SQL (including UPDATE) |

No named `update_outlet_reputation()` function exists, but `_write_with_retry(conn, sql, params)` handles arbitrary UPDATE statements with retry logic — verified working. The backtest can directly construct `UPDATE outlet_reputation SET ... WHERE domain=? AND industry_vertical=?` without any change to `reputation.py`. A named public function is nice-to-have but not a blocker.

### 5. Vertical role in SERP query not explicit — **LOW**

Task 7 function signature:
```python
def execute_historical_backtest(domain: str, vertical: str) -> None:
```

The plan says the SERP query is `site:{domain}` but `vertical` is accepted as a parameter. The intent is inferable: reputation is keyed by `(domain, vertical)` in every table, registration is `(domain, vertical)` composite, and the backtest receives both values. The query is almost certainly `site:{domain} {vertical}` — the spec just never states it explicitly.

---

## Summary

### 6. Stale Task 12 reference to a `# TBD: spawn` comment — **RESOLVED 2026-05-30**

Task 12 Step 2 was rewritten. The spawn call already exists in Task 8's `execute_forensic_pipeline`. Now a verification checkpoint confirming `from narrative.backtest import execute_historical_backtest` is importable from Modal and argument threading works.

### 7. Import path mismatch (`backtest` vs `narrative.backtest`) — **LOW / RESOLVED**

Task 8's `run_historical_backtest` does:
```python
from backtest import execute_historical_backtest
```

But the file is created at `narrative/backtest.py`. The correct import is:
```python
from narrative.backtest import execute_historical_backtest
```

Use the package import when creating the file — ensures correctness regardless of working directory or Modal packaging context.

---

## Summary

Until issues #1–#3 are resolved with concrete specs, Task 12 cannot produce a working implementation. These are design questions, not coding tasks:

| # | Status |
|---|---|
| 1 | (RESOLVED 2026-05-30) Consensus baseline → dual-SERP query (target + baseline) |
| 2 | (RESOLVED 2026-05-30) Absorbed/decayed → consensus-supported/consensus-isolated |
| 3 | (RESOLVED 2026-05-30) SERP query construction — `q` works as-is, `tbs` needs impl choice |
| 4 | (RESOLVED) Reputation UPDATE — `_write_with_retry` handles it directly, no new function needed |
| 5 | (RESOLVED) Vertical — intent is `site:{domain} {vertical}`, inferable but not explicit |
| 6 | (RESOLVED 2026-05-30) Stale TBD reference — Step 2 rewritten as verification checkpoint |
| 7 | (RESOLVED) Import — use `from narrative.backtest import ...` |
