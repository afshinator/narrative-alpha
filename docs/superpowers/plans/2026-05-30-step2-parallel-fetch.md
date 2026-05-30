# Task: Parallelize STEP 2 Article Fetching via BrightData

**Goal:** Replace the sequential `for`-loop in `build_ingestion_manifest` with parallel `ThreadPoolExecutor` calls to cut STEP 2 wall-clock time from ~128s to ~30s for 8 articles.

**Measured baseline (previous run):**

| Metric | Before | Target After |
|--------|--------|-------------|
| STEP 2 duration | 128.5s (8 docs × ~16s) | ~30s (2 batches × 5 workers) |
| `max_workers` | 1 (sequential) | 5 (matches all other pipeline steps) |
| Total pipeline | 837.5s | ~350-380s with Flash + parallel fetch |

---

## File Map

| File | Status | Responsibility |
|------|--------|---------------|
| `narrative/ingestion.py` | Modify | Parallelize the fetch-extract-validate loop in `build_ingestion_manifest` |

**No other files need changes.** The function signature and return type are unchanged — all existing callers and tests are unaffected.

---

## Verification (do this first)

Confirm the current sequential behavior by measuring how long a single `fetch_article_body` call takes:

```bash
pytest tests/ -x -q -k "test_build_ingestion_manifest"
```

Expected: passes (baseline test). Run `rtk grep 'def test_' tests/test_ingestion.py` to find any existing manifest tests first.

---

## Implementation

### Step 1: Add `concurrent.futures` import to `ingestion.py`

Add to the existing import block at line 6:

```python
from concurrent.futures import ThreadPoolExecutor
```

**Verification:** `python3 -c "from narrative.ingestion import build_ingestion_manifest"` — no import error.

---

### Step 2: Extract per-result processing into a helper

The loop body (lines 216–296) processes one SERP result. Extract this into a closure or helper function:

```python
def _process_one_result(
    idx: int, result: dict, zone: str, api_key: str,
    now_utc: str, keyword: str,
) -> tuple[dict, dict | None]:
    """
    Fetch, extract, and validate one SERP result.
    Returns (attempted_doc, validated_doc_or_None).
    """
    parsed = parse_serp_result(result)
    url = parsed["url"]
    title = parsed["title"]
    source_name = parsed["source_name"]
    domain = parsed["domain"]
    published_at = parsed["published_at"]

    if not url:
        return _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, "", None, 0), None

    fetch_status = None
    raw_text = ""
    try:
        html = fetch_article_body(url, zone, api_key)
        fetch_status = 200
        raw_text = extract_text(html)
    except Exception as e:
        fetch_status = getattr(getattr(e, "response", None), "status_code", 0) or -1
        return _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, "", fetch_status, 0), None

    if len(raw_text) < MIN_BODY_CHARS:
        return _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, raw_text, fetch_status, 0, body_length=len(raw_text)), None

    doc = {
        "doc_id": f"DOC-{idx:03d}",
        "source_name": source_name,
        "source_url": url,
        "title": title,
        "published_at": published_at,
        "scrape_timestamp": now_utc,
        "raw_text_content": raw_text,
        "fetch_status": fetch_status,
    }

    validated = validate_ingestion_payload(doc)
    if validated:
        validated["fetch_status"] = fetch_status
        validated["published_at"] = published_at
        attempted = {**validated}
        return attempted, validated
    else:
        attempted = _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, raw_text, fetch_status, 0)
        return attempted, None
```

Also add the helper to build attempted-doc dicts (avoids repetition):

```python
def _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, raw_text, fetch_status, passed_validation, body_length=None):
    doc = {
        "doc_id": f"DOC-{idx:03d}",
        "source_name": source_name,
        "source_url": url,
        "source_domain": domain,
        "title": title,
        "published_at": published_at,
        "scrape_timestamp": now_utc,
        "raw_text_content": raw_text,
        "fetch_status": fetch_status or 0,
        "passed_validation": passed_validation,
    }
    if body_length is not None:
        doc["body_length"] = body_length
    return doc
```

**Verification:** `python3 -c "from narrative.ingestion import _process_one_result, _attempted_doc"` — no errors. (These are module-level functions, imported for test access if needed.)

---

### Step 3: Replace the loop body with `ThreadPoolExecutor`

Replace lines 216–296 (the `for` loop) with:

```python
organic = serp_data.get("news", serp_data.get("organic", []))
all_attempted: list[dict] = []
validated_docs: list[dict] = []

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(_process_one_result, idx, result, zone, api_key, now_utc, keyword)
        for idx, result in enumerate(organic)
    ]
    for future in futures:
        attempted_doc, validated_doc = future.result()
        all_attempted.append(attempted_doc)
        if validated_doc is not None:
            validated_docs.append(validated_doc)
```

Keep everything after the loop (dedup, corpus floor check, return) exactly as-is.

**Why this pattern instead of `executor.map()`:** The original loop has different code paths for fetch-failure vs. extraction-failure vs. validation-pass, each producing different `all_attempted` entries. Returning tuples `(attempted, validated_or_None)` from each future keeps this distinction clean.

**Why no shared mutable state:** Each future returns its own tuple. The main thread collects results in order (preserving insertion order), appending to `all_attempted` and `validated_docs` without locks.

---

## Config Change (optional)

No config change needed — BrightData doesn't rate-limit Web Unlocker at 5 concurrent requests per account. If rate-limiting is observed, reduce `max_workers` to 3 in the code.

---

## Testing

- [ ] **Unit test:** Verify the helper function processes one result correctly
- [ ] **Integration test:** Time the parallel vs sequential fetch with the same keyword
- [ ] **Regression:** `pytest tests/ -x -q` — all 273 tests pass unchanged (function signature and return type identical)

---

## Which to Run First: Task 4 vs. This

**Recommended order:** Task 4 first (SSE streaming), then this optimization.

| Factor | Task 4 (SSE) | This (parallel fetch) |
|--------|-------------|----------------------|
| Files touched | `pipeline.py`, `server.py`, 6 dashboard files | `ingestion.py` only |
| Merge conflict? | None — different files | None — same file? |
| Demo impact | **Required** — shows progress in UI | Nice-to-have — makes pipeline faster |
| Pipeline correctness | No change to pipeline behavior | No change to pipeline output |
| Risk | Higher (new endpoint, new component) | Low (refactor of one loop) |

**No merge conflict** — Task 4 touches `pipeline.py` and `server.py`. This optimization touches only `ingestion.py`. They can be implemented in either order without conflict.

**Run Task 4 first** because it enables the demo's core user-facing feature (progress visibility). This optimization can follow immediately after with zero rebase cost.

---

## Design Notes

- **`_process_one_result` and `_attempted_doc` are module-level functions**, not nested closures. This makes them testable independently and avoids pickling issues with `executor.submit`.
- **`max_workers=5`** matches the existing pattern used in `analysis.py` and `processing.py` for LLM parallelization.
- **No ordering guarantee needed** — the dedup logic at the end of `build_ingestion_manifest` uses `seen_domains` set on `source_domain`, so SERP position doesn't matter for correctness.
- **Exceptions are caught per-future** — if one article fails, the other futures continue unaffected (same as current `try/except` behavior).
