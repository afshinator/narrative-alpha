# Adversarial Review — Task 6 (Analysis Layer)

**Review date:** 2026-05-30
**Scope:** `narrative/analysis.py` (376 lines), `tests/test_analysis.py` (661 lines), cross-referenced with `contracts.py`, `processing.py`, `llm_client.py`
**Tests:** 242/242 passing at time of review

---

## 🚨 Critical (1)

### 1. `inject_labels` doesn't populate `ReputationWarning.scatter_shot_label`

**File:** `narrative/analysis.py:160-186`, `narrative/contracts.py:130-137`

`ReputationWarning` defines `scatter_shot_label: str` with **no default value**:

```python
class ReputationWarning(_Strict):
    outlet_name: str
    source_domain: str
    warning_triggered: bool
    historical_origin_validation_rate: float = Field(ge=0.0, le=1.0)
    scatter_shot_anomaly_factor: float = Field(ge=0.0, le=1.0)
    scatter_shot_label: str          # <-- required, no default
    warning_message: str
```

`inject_labels` only sets `scatter_shot_label` inside `outlier_signals[i].outlier_origin_provenance` — it never iterates `reputation_warnings[]`. If the LLM returns `reputation_warnings` entries without this field (and the Contract B prompt schema shows it as `str` with no default hint), validation against `ForensicReport` raises:

```
1 validation error for ForensicReport
reputation_warnings.0.scatter_shot_label
  Field required [type=missing]
```

**Fix:** Add a loop parallel to the existing ones:

```python
for warning in report.get("reputation_warnings", []):
    sa = warning.get("scatter_shot_anomaly_factor", 0)
    warning["scatter_shot_label"] = scatter_shot_label(sa)
```

This mirrors exactly how `outlier_signals` entries get their label from the same numeric field.

---

## ⚠️ Medium (3)

### 2. Dead code block in `compute_pre_synthesis_context`

**File:** `narrative/analysis.py:250-252`

```python
if len(form_counts) < 1:
    continue
```

This is unreachable. `form_counts` is populated only on line 245 when `count > 0`, which guarantees at least one entry. The guard can never fire.

**Fix:** Delete lines 250-252.

### 3. `previous_term` selection is fragile

**File:** `narrative/analysis.py:259`

```python
previous_term = min(alternative_forms, key=lambda f: form_counts.get(f, 0))
```

When multiple alternative forms never appear in the text (all have count=0 in `form_counts`), `min()` falls back to alphabetical sorting. This can produce a semantically meaningless "previous_term" — e.g., `"firm"` even though "firm" never appeared in any article. It was never the "previous" term.

The term-shift detection is heuristic by nature, but this edge case means the LLM (Call 4) must handle nonsensical `previous_term` values gracefully.

**Mitigation could be:** Filter `alternative_forms` to only those that actually appear in `form_counts`, then pick the one with the next-highest count after the dominant form.

### 4. Non-idiomatic `uuid` import

**File:** `narrative/analysis.py:131`

```python
import uuid as _uuid
```

The `_uuid` alias is unusual — stdlib modules don't typically use underscore prefixes. The plan spec uses `import uuid`. Not a bug, but inconsistent with Python conventions. Consider `import uuid` instead.

---

## 🔍 Minor (3)

### 5. Silent truncation on mismatched list lengths

**File:** `narrative/analysis.py:95-97`

```python
zip(raw_texts, neutralized_texts)
```

If `raw_texts` and `neutralized_texts` differ in length, `zip` silently truncates to the shorter one. Consider `zip(..., strict=True)` (Python 3.10+) to raise on mismatch, or add an explicit `assert len(raw_texts) == len(neutralized_texts)` guard.

### 6. Missing edge-case tests

| What's missing | Risk |
|---|---|
| `extract_graph`: LLM returns valid JSON but not a dict (e.g. `"[]"`) | `json.loads` succeeds, downstream expects dict — `KeyError` / `TypeError` |
| `compute_pre_synthesis_context`: graphs with `_parse_error` are skipped | Covered by code path, no explicit test at pre-synthesis level |
| `inject_labels`: `reputation_warnings` section | See critical bug #1 |
| `inject_labels`: all input sections missing from report dict | `report.get(key, [])` handles missing keys, but no explicit test |

### 7. `compute_consensus_stability` return type differs from plan

**File:** `narrative/analysis.py:306-314` vs `docs/superpowers/plans/2026-05-29-narrative-alpha-full.md:1484`

The plan spec shows `-> tuple[float, str]` (score + label inline). Implementation returns `-> float` only, with label deferred to `inject_labels`. This was an intentional user-directed change (absorbed Task 9), but the signature mismatch means anyone reading the plan sees an inconsistency.

---

## ✅ Defensively Correct

These areas were verified and are sound:

- **All 6 plan sanity checks** pass via independent execution
- `resolve_to_canonical` correctly lowercases and strips whitespace
- `compute_consensus_baseline` threshold = `int(0.75*n) + 1` (true ceiling)
- `compute_omission_index` handles empty consensus, all-missing, and canonical overlap
- `extract_all_graphs` catches `Exception` per-graph (not `BaseException` — correct per Section 10 H4)
- `numpy` is listed in `requirements.txt` ✓
- All parallel workers use `max_workers=5` (matches `processing.py` convention)
- `inject_labels` uses `setdefault` on `classification_method` — preserves existing values
- `synthesize_forensic_report` creates a new dict via `{**context_bundle, ...}` — original caller dict not mutated
- `compute_framing_volatility` lazy-imports `numpy` and `get_embedding` — avoids top-level import side effects
