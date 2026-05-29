# Task 4 Adversarial Review — Findings & Fixes

> **Context:** Review of `reputation.py` and `test_reputation.py` produced 6 substantive findings. This plan researches each for veracity, decides whether to fix, and implements the fix.

**Goal:** Validate or dismiss each adversarial finding, then apply corrective patches.

**Verification:** `uv run pytest -v && python -m py_compile reputation.py test_reputation.py`

---

### Finding 1: `write_ingestion_log` poisons connection on mid-loop failure

**Claim:** On `conn.execute()` failure for doc #2, doc #1 is left in an uncommitted implicit transaction. Exception propagates without `rollback()`, leaving connection in a failed-transaction state. Every subsequent operation on that connection crashes.

- [ ] **Research:** Write a minimal script that:
  1. Creates an in-memory SQLite DB with `init_db`
  2. Inserts one doc successfully
  3. Simulates failure on doc #2 (e.g., violate NOT NULL with `body_length=None`)
  4. Attempts a third unrelated query after the exception propagates
  5. Documents whether the third query succeeds or fails with "cannot start a transaction within a transaction"

- [ ] **Decision & fix:** If verified, fix `write_ingestion_log` to either:
  - Wrap each doc in its own try/except+commit (per-doc resilience), OR
  - Use `_write_with_retry` per doc, OR
  - Use a single transaction with explicit `conn.rollback()` in the exception handler before propagating

---

### Finding 2: `test_ignore_duplicate_signal` doesn't test duplicates

**Claim:** Test at `test_reputation.py:116-127` inserts `sig1` and `sig2` — different signal IDs. Name says "ignore duplicate" but nothing is duplicated. Should insert `sig1` twice and assert count stays 1.

- [ ] **Research:** Read the test and confirm the assertion.

- [ ] **Fix:** Replace the test body to insert the same `signal_id` twice and assert only one row exists. Keep a second assertion that two different signal IDs both persist (that was the original test's actual coverage).

---

### Finding 3: `write_ingestion_log` not using `_write_with_retry`

**Claim:** Debug log is the data source for Phase 2 30-day outlier tracking. Concurrent writes from backtest worker could cause `OperationalError` and silently drop the batch.

- [ ] **Research:** Assess whether the backtest worker writes to the same DB concurrently. If `handle_outlet_registration` and `write_outlier_signal` use `_write_with_retry` but `write_ingestion_log` does not, a concurrent write lock could cause the log write to fail while the backtest write succeeds.

- [ ] **Decision:** Evaluate risk — is this best-effort debug logging (leave as-is) or Phase 2-critical data (wrap in `_write_with_retry`)?

---

### Finding 4: `body_length` double dict lookup

**Claim:** Line 177 calls `doc.get("raw_text_content", "")` twice — once for `body_text` (line 176), once inside `len()` fallback (line 177).

- [ ] **Research:** Read line 176-177 and confirm the double call exists.

- [ ] **Fix:** Assign `raw_text = doc.get("raw_text_content", "")` to a local variable and reuse it.

---

### Finding 5: `_write_with_retry` catches all `OperationalError` unconditionally

**Claim:** Catches every `OperationalError` (including `SQLITE_CORRUPT`, `SQLITE_READONLY`, etc.) — not just "locked" errors as the original plan specified. Non-retriable errors waste retries.

- [ ] **Research:** Check the current implementation at `reputation.py:41` vs the plan's original version. Identify which `OperationalError` subtypes are retriable (locked/busy) vs non-retriable (corrupt, readonly, cantOpen).

- [ ] **Decision:** Decide whether to re-add the "locked" filter or keep the broader catch (simpler, max_retries bounds the damage).

---

### Finding 6: No test for `_write_with_retry` failure behavior

**Claim:** No test verifies that `_write_with_retry` raises after exhausting `max_retries`, or that it calls `conn.rollback()` on failure.

- [ ] **Research:** Audit current test coverage for `_write_with_retry`.

- [ ] **Fix (if decided):** Add tests that:
  1. Mock `conn.execute` to raise `sqlite3.OperationalError("database is locked")` and verify retry happens
  2. Verify the function raises after `max_retries` exhausted
  3. Verify `conn.rollback()` is called at least once

---

### Apply fixes

- [ ] **Stage 1:** Fix Finding 1 — `write_ingestion_log` connection poisoning
- [ ] **Stage 2:** Fix Finding 2 — `test_ignore_duplicate_signal`
- [ ] **Stage 3:** Fix Finding 4 — `body_length` double dict lookup
- [ ] **Stage 4:** Fix Finding 5 — `_write_with_retry` exception filter (if decided)
- [ ] **Stage 5:** Fix Finding 6 — `_write_with_retry` tests (if decided)
- [ ] **Stage 6:** Run full test suite: `uv run pytest -v`
- [ ] **Stage 7:** Run lint: `uv tool run ruff check reputation.py test_reputation.py`
