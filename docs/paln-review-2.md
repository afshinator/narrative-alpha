## Plan v2 Review — Narrative Alpha v1.4

**Bottom line up front:** All 15 issues from the previous review have been addressed. The plan is structurally solid and ready to implement. What remains are smaller issues — one genuine blocker, two real functional gaps, and a handful of things that will bite during the demo if uncaught.

---

### 🔴 One Remaining Blocker

**1. `compute_pre_synthesis_context` is still a TBD stub in Task 6.**
Task 11 is correctly on the critical path now, but the stub in Task 6's code is what gets committed to the repo. When Task 6 is merged and Task 11 hasn't run yet, any integration test will silently pass with empty pre-synthesis outputs — which means the developer could reach the demo before realizing Tasks 6 and 11 are coupled. The cleaner fix: raise a `NotImplementedError` in the stub body instead of returning empty dicts. That way running the pipeline before Task 11 is done fails loudly rather than producing a hollow report with no `reality_divergence_zones`, `reality_fractures`, or `narrative_regime_shifts`. This is a one-line change but matters a lot for demo integrity.

---

### 🟡 Functional Gaps

**2. `context_bundle` includes raw and neutralized texts per source (good), but Call 4's system prompt has no schema instruction.**
The `synthesize_forensic_report` function dumps the entire `context_bundle` as raw JSON into the user message and tells the model to "output only valid JSON matching the schema provided" — but the schema is never provided in the prompt. Call 4 is flying blind on output shape. The spec's Section 6 has an output description ("complete Contract B JSON including all existing fields plus the three new objects"), but that description needs to be embedded in the Call 4 prompt as an explicit JSON schema skeleton or at minimum a field list. Without it, DeepSeek's thinking model will infer structure from the input bundle, which will produce an inconsistent output shape run-to-run. Add the Contract B output schema (or a condensed version of it) to `FORENSIC_SYNTHESIS_SYSTEM_PROMPT`.

**3. `_ensure_initialized` uses a module-level Python flag (`DB_INITIALIZED`) that doesn't persist across Modal cold starts.**
`DB_INITIALIZED = False` is reset every time Modal spins up a new container — which is every cold start and every new worker. This is actually fine for its stated purpose (idempotent init), since `init_db` uses `CREATE TABLE IF NOT EXISTS`. The real issue is that `_ensure_initialized` will re-run on every cold start container, which is cheap, but the flag's implication (that it's a once-per-process guard) is misleading. Rename it to `_run_startup_init()` and remove the global flag — just let it run every container start. The underlying operations are idempotent so there's no correctness risk, and removing the flag eliminates the false safety of thinking you've cached something that resets anyway.

**4. `ingestion.py` passes `all_attempted` to `write_ingestion_log`, but `all_attempted` is never defined in the visible code.**
The `build_ingestion_manifest` signature (Task 3) accepts `db_conn`, and the log call is present at line 675: `write_ingestion_log(cluster_id, keyword, now_utc, all_attempted, db_conn)`. The function needs to track both passing and failing docs in an `all_attempted` list before validation filtering occurs, but that accumulation isn't shown in the snippet — it jumps from the fetch loop straight to `validated_docs`. The agent implementing this needs to know to maintain a parallel `all_attempted` list that captures every doc dict (including failed ones with `passed_validation: 0`) before the dedup step. Worth adding this explicitly to Task 3's implementation steps so the agent doesn't skip it.

---

### 🟢 Minor Issues

**5. `corpus_capped` flag in the manifest is not reflected in `event_meta` of the final report.**
The spec's Section 10 says to "log a `CORPUS_CAPPED` flag in event meta." The plan adds `corpus_capped: True` to the ingestion manifest dict (good), but nothing passes it through to `ForensicReport.event_meta`. The `EventMeta` Pydantic model has no `corpus_capped` field, and the orchestrator doesn't thread it into the report. The frontend can't surface this warning. Add `corpus_capped: bool = False` to `EventMeta` and thread the flag through.

**6. `compute_consensus_baseline` counts all graphs including `_parse_error` ones in `n`.**
Line 1246: `n = len(all_graphs)`. Then the loop skips `_parse_error` graphs. This means if 3 of 10 articles parse-fail, the threshold is calculated against 10 sources but only 7 actually contribute nodes — so you need 8+ sources to agree (ceiling of 0.75 × 10) when only 7 are participating. A node appearing in all 7 valid sources won't reach consensus. Fix: compute `n` from the count of non-error graphs, or explicitly document this as intentional conservative behavior.

**7. Call 2 (linguistic neutralization) runs N sequential LLM calls, same serial timeout risk as Call 3.**
The timeout warning in the execution notes mentions Call 3 specifically, but Call 2 also runs a loop over all docs. With 20 docs, that's 20 flash-tier calls — each is fast (~1–2s), but the same `asyncio.gather` optimization mentioned for Call 3 applies here too. At minimum, flag it in the execution note so the agent knows to parallelize both if timeout becomes an issue.

**8. `write_ingestion_log` uses `INSERT OR IGNORE` with `canonical_url` as the unique constraint, but the same URL could be fetched in two different cluster runs.**
On the second run about the same topic, the same article URL would silently be ignored rather than updated. For debugging purposes during the hackathon, you probably want to see both fetch attempts. Consider using a composite PK of `(canonical_url, query_id)` or switching to `INSERT OR REPLACE`. Low priority since it only affects the debug log, not the pipeline.

**9. Task 10 integration step 1 says "verify each of the 13 steps has a corresponding code block" but app.py now has 14 steps.**
The docstring in `execute_forensic_pipeline` correctly says "14 steps", but the integration task's Step 1 still says "13 steps." Cosmetic, but if an agent runs this checklist it'll stop counting at 13 and miss the outlier signal write step.

**10. The file map still lists `processing.py` as owning "Vf computation."**
The file map at the top says: `processing.py | Layer 2 | ... embedding generation, Vf computation`. This was the old assignment. Vf is now correctly in `analysis.py`, but the file map header wasn't updated. The task descriptions and sanity checks are correct — just the file map header entry for `processing.py` is stale. Small but will confuse anyone reading the map before diving into the tasks.

---

### Summary

The plan is in genuinely good shape. The previous round of fixes landed cleanly and the architecture is coherent. For implementation safety, the three things worth fixing before kicking off:

1. Change the `compute_pre_synthesis_context` stub to `raise NotImplementedError` (blocker protection for the demo)
2. Add the Contract B output schema to `FORENSIC_SYNTHESIS_SYSTEM_PROMPT` (Call 4 output consistency)
3. Add `all_attempted` accumulation explicitly to Task 3's steps (prevents a silent logging bug)

The rest can be caught during integration (Task 10) or are low-stakes cosmetic fixes.