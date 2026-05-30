# Adversarial Review — Task 8 (Orchestration)

**Date:** 2026-05-30 — verified against live code, not assumptions.
**Review scope:** Plan Task 8 (`narrative/app.py` + settings endpoint) cross-referenced against actual function signatures in `ingestion.py`, `processing.py`, `analysis.py`, `reputation.py`, `llm_client.py`, `contracts.py`, `backtest.py`.

**Method:** Every import and every function call in the plan was verified against the actual source code. Parameter names, positional order, optional args, and return types were checked. Edge cases were traced through live execution.

---

## Confirmed Correct (22 call sites verified)

| Call site | Status |
|-----------|--------|
| `discover_articles(keyword, api_key)` — uses default `num=15` | ✓ |
| `handle_outlet_registration(domain, vertical, db_conn, outlet_name=...)` — signature matches | ✓ |
| `read_outlet_reputation(domain, vertical, db_conn)` | ✓ |
| `write_outlier_signal(signal_id, cluster_id, origin_domain, extracted_claim, timestamp, conn=db_conn)` | ✓ |
| `run_entity_normalization(documents, serp_data, llm_config)` | ✓ |
| `run_linguistic_neutralization(documents, llm_config)` | ✓ |
| `extract_all_graphs(documents, neutralized, canonical_map, llm_config)` — 4 positional args match | ✓ |
| `compute_consensus_baseline(all_graphs, canonical_map)` | ✓ |
| `compute_omission_index(consensus_nodes, source_nodes, canonical_map)` | ✓ |
| `omission_label(oi)` | ✓ |
| `framing_volatility_label(vf)` | ✓ |
| `compute_framing_volatility(raw_texts, neutralized)` | ✓ |
| `scatter_shot_label(sa)` | ✓ |
| `compute_sa_for_outlet` — not called in this pipeline (expected — used by backtest) | ✓ (uncalled) |
| `compute_pre_synthesis_context(all_graphs, neutralized, raw_texts, canonical_map, consensus_nodes)` — 5 positional args match | ✓ |
| `synthesize_forensic_report(context_bundle, llm_config)` | ✓ |
| `inject_labels(report)` | ✓ |
| `load_llm_config()` — zero args | ✓ |
| `get_hardened_db_connection(db_path)` | ✓ |
| `init_db(conn)` | ✓ |
| `run_historical_backtest.spawn(domain, vertical)` → `execute_historical_backtest(domain, vertical)` | ✓ |
| `@modal.web_endpoint(method="POST")` on async function returning dict | ✓ |

---

## Finding 1 (High) — Import paths use bare module names

**Plan code** (lines 1755–1781):
```python
from contracts import PipelineInput
from reputation import (...)
from ingestion import discover_articles, build_ingestion_manifest
from processing import (...)
from analysis import (...)
from llm_client import load_llm_config
```

**Verified:** Bare imports DO work in the Modal runtime because Modal sets the working directory to the `narrative/` directory (where `contracts.py`, `reputation.py`, etc. are siblings of `app.py`). So this is NOT a runtime crash in Modal. However:
- Bare imports fail from the project root, making local testing impossible.
- The project convention (`analysis.py:82`, `processing.py:28`) uses `from narrative.xxx import ...`.
- `narrative/__init__.py` exists — this is a proper Python package.

**Fix:** Add the `narrative.` prefix to all 6 import lines:

```python
from narrative.contracts import PipelineInput  # → removed per Finding 3
from narrative.reputation import (...)
from narrative.ingestion import discover_articles, build_ingestion_manifest
from narrative.processing import (...)
from narrative.analysis import (...)
from narrative.llm_client import load_llm_config
```

---

## Finding 2 (High) — `build_ingestion_manifest` called without `logger_func`

**Plan code** (line 1871):
```python
# Comment on line 1868: "Pass db_conn so build_ingestion_manifest logs all fetch attempts (pass+fail)"
manifest = build_ingestion_manifest(keyword, serp_data, unlocker_zone, api_key, db_conn=db_conn)
```

**Verified:** The logging guard at `ingestion.py:317` requires BOTH `db_conn is not None AND logger_func is not None`. The plan passes `db_conn` but `logger_func` defaults to `None` — the guard never fires, no logging happens. The comment says logging should happen, but it won't.

The `write_ingestion_log` callable at `reputation.py:154` has a signature matching the 5 positional arguments that `build_ingestion_manifest` passes to `logger_func`:
```
logger_func(cluster_id, keyword, now_utc, all_attempted, db_conn)
                         ↓         ↓          ↓              ↓
write_ingestion_log(query_id, topic, discovery_timestamp, docs, conn)
```

**Fix:** Add `write_ingestion_log` to the reputation import and wire it:

```python
from narrative.reputation import (
    get_hardened_db_connection,
    init_db,
    handle_outlet_registration,
    read_outlet_reputation,
    write_outlier_signal,
    write_ingestion_log,          # ← added
)

manifest = build_ingestion_manifest(
    keyword, serp_data, unlocker_zone, api_key,
    db_conn=db_conn,
    logger_func=write_ingestion_log,  # ← added
)
```

---

## Finding 3 (High) — `PipelineInput` dead import

**Plan code** (line 1755):
```python
from contracts import PipelineInput
```

**Verified:** `PipelineInput` is imported but never referenced anywhere in the function bodies. The web endpoint signature is `async def execute_forensic_pipeline(payload: dict) -> dict` — no type annotation uses `PipelineInput`. This is dead code and will trigger linting warnings.

**Fix:** Remove the import entirely. (Combined with Finding 1's fix, the `from narrative.contracts` line is simply deleted.)

---

## Finding 4 (Medium) — Empty `consensus_nodes` edge case not handled

**Plan code** (lines 1904–1905):
```python
consensus_nodes = compute_consensus_baseline(all_graphs, canonical_map)
```

**Verified** via live execution: When `n < 5` valid graphs, `compute_consensus_baseline` returns `set()` (`analysis.py:335-336`). The downstream effects are:

| Condition | Result |
|-----------|--------|
| `compute_omission_index(set(), ...)` | Returns `(0.0, [])` — misleading: zero omission when there's nothing to omit |
| `omission_label(0.0)` | Returns `"LOW"` — falsely suggests low distortion |
| `compute_pre_synthesis_context(consensus_nodes=set())` | No narrative clusters, no fracture candidates. `term_shifts` may still populate from `raw_texts`. |
| Final report | Plausible-looking structure with `oi=0.0, omission_label="LOW"` for every source — impossible for caller to distinguish from "no issues found" |

**Proposed fix:** Add a degraded flag to `context_bundle` after computing consensus:

```python
# After line 1905:
if not consensus_nodes:
    context_bundle["_degraded"] = "INSUFFICIENT_CONSENSUS"
```

**Comment:** Should the endpoint return an error response early (before LLM synthesis) instead of proceeding with a degraded report? The current design choice is "continue degraded" (matching the pattern in `run_entity_normalization` which returns empty dict on failure). Returning early saves an LLM call but hides whatever signal `term_shifts` might surface. Either approach is defensible — flagging is the minimum viable signal.

---

## Finding 5 (Low) — Inconsistent guards in `per_source` build

Downgraded from Medium after verification.

**Plan code** (lines 1929–1943):
```python
"per_source": [
    {
        "domain": g.get("_source_domain", ""),
        "name": g.get("_source_name", ""),
        "graph": g,
        "omission_index": omission_results[i][0],               # ← NO guard
        "omission_label": omission_results[i][2],               # ← NO guard
        "missing_nodes": omission_results[i][1],                # ← NO guard
        "framing_volatility": vf_scores[i] if i < len(vf_scores) else 0.0,  # ← HAS guard
        "framing_volatility_label": vf_labels[i] if i < len(vf_labels) else "MED",
        "raw_text": raw_texts[i] if i < len(raw_texts) else "",
        "neutralized_text": neutralized[i] if i < len(neutralized) else "",
    }
    for i, g in enumerate(all_graphs)
],
```

**Verified:** If lengths actually mismatched, `omission_results[i][0]` would raise `IndexError` before any guard on `vf_scores[i]` could help. Since all lists derive from the same `documents` source, the invariant holds naturally. The guards on `vf_scores`/`vf_labels`/`raw_texts`/`neutralized` are inconsistent (half the fields guarded, half not) and effectively dead code.

**Proposed fix:** Either make guards consistent (add them to `omission_results` fields too), or remove them all (fail-fast if the invariant breaks — the crash is the correct behavior since the invariant should never break):

```python
"omission_index": omission_results[i][0] if i < len(omission_results) else 0.0,
"omission_label": omission_results[i][2] if i < len(omission_results) else "LOW",
"missing_nodes": omission_results[i][1] if i < len(omission_results) else [],
```

---

## Finding 6 (Medium) — Missing env-var validation

**Plan code** (lines 1857–1858):
```python
api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")
```

**Verified:** `discover_articles` at `ingestion.py:35` sends `Authorization: f"Bearer {api_key}"` with `raise_for_status()` — empty API key produces an opaque `HTTPError` with no clear message. Same for `fetch_article_body` with the unlocker zone. No try/except wraps the pipeline steps, so this would return a Modal 500.

Note: Modal's `secrets=[modal.Secret.from_dotenv(".env.production")]` means these come from a file — this is defensive validation.

**Fix:**

```python
if not api_key or not unlocker_zone:
    return {"status": "ERROR", "error": "BRIGHTDATA_API_KEY and BRIGHTDATA_UNLOCKER_ZONE must be set"}
```

---

## Finding 7 (Low) — Variable name `unlocker_zone` vs parameter `zone`

**Plan code** (line 1871):
```python
manifest = build_ingestion_manifest(keyword, serp_data, unlocker_zone, api_key, ...)
```

**Verified:** Positional argument — works correctly regardless of names. Cosmetic only.

**Comment:** No fix needed. The variable name `unlocker_zone` is semantically clear (it IS the Bright Data unlocker zone) even though the parameter is named `zone`. Changing the parameter name in `ingestion.py` would be a separate refactor outside Task 8 scope.

---

## Finding 8 (Low) — No retry around LLM/API calls

**Verified:** The pipeline is fully linear with no retry. A single transient LLM or API failure kills the entire run. This is a design tradeoff for the first implementation, not a bug.

**Comment:** Recommend option 3 from original review — document that the pipeline is best-effort. Add tenacity retry to `llm_client.py` (option 1) as a future improvement when the pipeline is stable. Not blocking for Task 8.

---

## Additional items discovered during verification

### A. `compute_pre_synthesis_context` accepts unused `neutralized_texts` parameter

**Not a Task 8 plan bug** — this is pre-existing in `analysis.py:195`. The parameter `neutralized_texts` is accepted but never referenced in the function body (lines 200–273). The plan passes `neutralized` correctly; the function silently ignores it. No action required for Task 8.

### B. `update_llm_config` endpoint has no schema validation

**Plan code** (lines 2000–2005):
```python
required_slots = [
    "call_1_entity_normalization",
    "call_2_linguistic_neutralization",
    "call_3_graph_extraction",
    "call_4_forensic_synthesis",
]
for slot in required_slots:
    if slot not in payload:
        return {"error": f"Missing required slot: {slot}"}
```

**Issue:** The endpoint only checks that slot keys exist — it doesn't validate the structure of each slot (required fields `provider`, `model`, `thinking`, `temperature`). A malformed config written here would silently corrupt the config file, causing the next pipeline run to fail with an opaque error.

**Proposed fix:** Validate the payload against `LLMConfig` before writing:

```python
from narrative.contracts import LLMConfig

try:
    LLMConfig(**payload)
except Exception as e:
    return {"error": f"Invalid config: {e}"}
```

This validates both slot names AND slot field structure. Note: this re-introduces the `LLMConfig` import that Finding 3 removes from the main endpoint — but here it's actually used.

---

## Summary

| # | Severity | Finding | Action |
|---|----------|---------|--------|
| 1 | **High** | Import paths use bare module names | Add `narrative.` prefix to all 6 imports |
| 2 | **High** | Ingestion log not wired | Add `write_ingestion_log` import + pass as `logger_func` |
| 3 | **High** | `PipelineInput` dead import | Remove entirely |
| 4 | **Medium** | Empty `consensus_nodes` edge case | Add `_degraded` flag to context_bundle |
| 5 | **Low** | Inconsistent guards in per_source | Add guards to omission_results fields (consistency) |
| 6 | **Medium** | Missing env-var validation | Validate early, return error |
| 7 | **Low** | Variable name drift | No action (cosmetic, positional arg works) |
| 8 | **Low** | No retry around LLM/API calls | Document as best-effort; future improvement |
| B | **Medium** | `update_llm_config` no schema validation | Validate against `LLMConfig` model |

**Actionable items for plan fix:** 1, 2, 3, 4, 5, 6, B (7 items).
**Deferred / no action:** 7 (cosmetic), 8 (design tradeoff), A (pre-existing, out of scope).
