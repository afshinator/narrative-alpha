# Mock & TS Pre-Existing Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 7 `test_ingestion.py` failures (missing `.ok` on FakeResp mocks) and 1 TS error in `PipelineRunner.tsx` (dead code accessing `error_detail` on a literal type).

**Architecture:** Two independent fixes — test mocks need `.ok` attribute added to match production code's `response.ok` check; frontend dead code branch is unreachable and should be removed rather than extending the type.

**Tech Stack:** Python 3.11 + pytest (test mock fix); React + TypeScript (frontend fix)

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `tests/test_ingestion.py` | Modify 7 inline FakeResp classes | Add `.ok` attribute matching what `ingestion.py` expects |
| `dashboard/src/components/PipelineRunner.tsx` | Remove dead `else` branch + simplify `PipelineStorageEntry` | Eliminate TS error from unreachable code |

---

### Task 1: Fix `test_ingestion.py` — add `.ok` to all 7 FakeResp mocks

**Files:**
- Modify: `tests/test_ingestion.py` (7 inline classes, lines 253-386)

This task touches 7 inline `FakeResp` classes inside `fake_post` closures. The production code in `ingestion.py:48` and `ingestion.py:73` checks `response.ok` and no longer calls `raise_for_status()`.

**Success-path mocks** (#1, #2, #4, #5, #6) — only need the single line `ok = True` added. They already have the other attributes needed for the success path.

**Error-path mocks** (#3, #7) — need `ok = False`, `status_code = NNN`, `text = ""` replacing the old `raise_for_status()` method. The `pytest.raises` match pattern also needs updating since the error message changed from `raise_for_status()` output to the `RuntimeError` format in production.

- [ ] **Step 1: Fix FakeResp #1 — `test_sends_correct_payload` (success path)**

In `tests/test_ingestion.py`, lines 253-255, change:
```python
class FakeResp:
    def raise_for_status(self): pass
    def json(self): return {"body": _json.dumps({"news": []})}
```
to:
```python
class FakeResp:
    ok = True
    def json(self): return {"body": _json.dumps({"news": []})}
```

- [ ] **Step 2: Fix FakeResp #2 — `test_defaults_to_15_results` (success path)**

Lines 278-280, change:
```python
class FakeResp:
    def raise_for_status(self): pass
    def json(self): return {"body": "{}"}
```
to:
```python
class FakeResp:
    ok = True
    def json(self): return {"body": "{}"}
```

- [ ] **Step 3: Fix FakeResp #3 — `test_raises_on_http_error` (error path)**

Lines 291-294 + line 298, change the class:
```python
class FakeResp:
    def raise_for_status(self):
        raise Exception("HTTP 403")
    def json(self): return {}
```
to:
```python
class FakeResp:
    ok = False
    status_code = 403
    text = ""
```

And change the match pattern on line 298:
```python
with pytest.raises(Exception, match="HTTP 403"):
```
to:
```python
with pytest.raises(Exception, match="Bright Data SERP 403"):
```

- [ ] **Step 4: Fix FakeResp #4 — `test_appends_time_range_when_set` (success path)**

Lines 311-313, change:
```python
class FakeResp:
    def raise_for_status(self): pass
    def json(self): return {"body": _json.dumps({"news": []})}
```
to:
```python
class FakeResp:
    ok = True
    def json(self): return {"body": _json.dumps({"news": []})}
```

- [ ] **Step 5: Fix FakeResp #5 — `test_omits_time_range_by_default` (success path)**

Lines 332-334, change:
```python
class FakeResp:
    def raise_for_status(self): pass
    def json(self): return {"body": _json.dumps({"news": []})}
```
to:
```python
class FakeResp:
    ok = True
    def json(self): return {"body": _json.dumps({"news": []})}
```

- [ ] **Step 6: Fix FakeResp #6 — `test_sends_correct_payload` in `FetchArticleBody` (success path)**

Lines 363-365, change:
```python
class FakeResp:
    def raise_for_status(self): pass
    text = "<html><body><p>Article body.</p></body></html>"
```
to:
```python
class FakeResp:
    ok = True
    text = "<html><body><p>Article body.</p></body></html>"
```

- [ ] **Step 7: Fix FakeResp #7 — `test_raises_on_http_error` in `FetchArticleBody` (error path)**

Lines 384-386 + line 390:
```python
class FakeResp:
    def raise_for_status(self):
        raise Exception("HTTP 500")
```
to:
```python
class FakeResp:
    ok = False
    status_code = 500
    text = ""
```

And change the match pattern on line 390:
```python
with pytest.raises(Exception, match="HTTP 500"):
```
to:
```python
with pytest.raises(Exception, match="Bright Data Unlocker 500"):
```

- [ ] **Step 8: Run all ingestion tests to verify**

Run:
```bash
source .venv/bin/activate && python -m pytest tests/test_ingestion.py -v
```
Expected: All tests PASS (previously 7 failed, now all pass)

- [ ] **Step 9: Run full backend test suite to check for regressions**

Run:
```bash
source .venv/bin/activate && python -m pytest tests/ -v 2>&1 | tail -20
```
Expected: Same or better pass rate (pre-existing failures unrelated to ingestion should remain unchanged)

- [ ] **Step 10: Commit**

```bash
git add tests/test_ingestion.py
git commit -m "fix: add .ok to FakeResp mocks in test_ingestion.py"
```

---

### Task 2: Fix `PipelineRunner.tsx` — remove dead else branch

**Files:**
- Modify: `dashboard/src/components/PipelineRunner.tsx` (lines 253-281)

The `else` branch at line 271 is unreachable dead code: `PipelineStorageEntry.status` is a literal type `"complete"`, the storage logic only writes on the `"complete"` SSE event (line 184-191), and the restoration guard deletes any entry where `status !== "complete"` (line 74). The TS error is `Property 'error_detail' does not exist on type 'PipelineStorageEntry'`.

- [ ] **Step 1: Replace the stored-result banner with a simplified version**

In `dashboard/src/components/PipelineRunner.tsx`, replace lines 253-281:
```tsx
			{/* Stored result banner (from sessionStorage) */}
			{storedResult && runnerState === "idle" && (
				<div className="stored-result-banner stored-result-banner--complete">
					<span>
						Report ready —{" "}
						<a
							href={`/event/${storedResult.cluster_id}`}
							onClick={(e) => {
								e.preventDefault();
								navigate(`/event/${storedResult.cluster_id}`);
							}}
						>
							{storedResult.search_query}
						</a>
					</span>
					<button className="stored-result-dismiss" onClick={clearStoredResult}>
						✕
					</button>
				</div>
			)}
```

This removes the ternary (`storedResult.status === "complete"` was always true), removes the dead `else` branch, and hardcodes the CSS class to `stored-result-banner--complete` since that's the only state that occurs.

- [ ] **Step 2: Simplify `PipelineStorageEntry` type**

`status: "complete"` is a single-value literal type now used in only one branch, so it can be removed entirely or kept as documentation. The `status` field is no longer read by the component (no ternary), so it's only used by the restoration guard on line 74. Keep as-is — the guard still needs it.

No change needed on the type itself; the `status: "complete"` stays for the guard function.

Also update the sessionStorage write on line 187-191 to remove the type assertion if desired (optional, no correctness change).

- [ ] **Step 3: Run TypeScript to verify the error is gone**

Run:
```bash
cd dashboard && npx tsc --noEmit
```
Expected: EXIT CODE 0 with no errors (previously showed `error TS2339: Property 'error_detail' does not exist on type 'PipelineStorageEntry'`)

- [ ] **Step 4: Run lint on the changed file**

Run:
```bash
cd dashboard && npx biome check --write src/components/PipelineRunner.tsx
```
Expected: File is linted/formatted without errors.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/PipelineRunner.tsx
git commit -m "fix: remove dead else branch in stored-result banner"
```

---

## Self-Review Checklist

1. **Spec coverage:** Task 1 fixes all 7 test_ingestion.py failures (5 success-path mocks + 2 error-path mocks + match patterns). Task 2 fixes the TS error by removing dead code. Both issues are covered.

2. **Placeholder scan:** All steps contain exact code changes. No "TBD", "TODO", or "implement later" patterns. Every edit shows the before and after.

3. **Type consistency:** The `PipelineStorageEntry` type is unchanged. The only consumer of `status` outside the removed code is the restoration guard (line 74), which still works correctly with `status: "complete"`.

4. **Test verification:** All ingestion tests must pass before commit. No new tests needed — these are fixes to existing test infrastructure, not feature additions.
