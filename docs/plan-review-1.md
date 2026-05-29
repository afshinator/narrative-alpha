## Plan vs. Spec Review — Narrative Alpha v1.4

### 🔴 Critical Issues (will break the build)

**1. `Vf` computation is in the wrong layer.**
The spec is explicit in Section 2's layer diagram: cosine distance / framing volatility lives in Layer 3 (Analytical Layer). The plan puts `compute_framing_volatility()` in `processing.py` (Layer 2). Embeddings need to be called *after* neutralization, but the `Vf` score computation and labeling should be in `analysis.py`, not `processing.py`. As written, the plan violates the decoupling rule that Layer 2 "contains zero analysis logic." Fix: move `compute_framing_volatility` and `get_embedding` calls to `analysis.py`, leave only the neutralization text generation in `processing.py`.

**2. `app.py` steps 7 and 9 are out of order.**
The plan has step 7 ("embed raw + neutralized texts → Vf") happening before step 8 (graph extraction). This is fine computationally, but it means the framing volatility logic runs in `app.py` directly rather than being encapsulated in the analysis layer. Combined with issue #1 above, the Vf computation is scattered across the orchestrator — the plan doesn't have a clean `run_analysis_layer()` call, unlike the spec's Section 8 which implies the analysis layer is a clean invocation. This needs a `run_analysis_layer(processed_payload)` function in `analysis.py` that wraps steps 7–12.

**3. Ingestion log write is entirely missing from the plan.**
Section 14.3 specifies that *every* scrape attempt (pass AND fail) gets logged to `ingestion_manifest_log`. The plan's `ingestion.py` has no call to `write_ingestion_log()`. Task 4 defines `write_ingestion_log()` in `reputation.py` but Task 3 (ingestion) never calls it. The integration task (Task 10) doesn't flag this either. You'll have zero debugging data during the hackathon demo.

**4. `validate_ingestion_payload` strips `passed_validation` from its return dict.**
The spec's Section 14.1 includes `passed_validation: 1` in the returned dict. The plan's Task 3 code omits it. Meanwhile, `write_ingestion_log()` in Task 4 reads `doc.get("passed_validation", 0)`. When a passing document hits the log writer, it'll always log `0` (the default), not `1`. The failed-doc logging path works (failed docs never hit `validate_ingestion_payload`'s return), but all passing docs will be misclassified in the log.

**5. SERP payload uses wrong field name in Section 3 vs Section 14.**
Section 3's Layer 1 detail code uses `"query": "{user_keyword}"` and `"engine": "google_news"`. Section 14.2A (authoritative) uses `"q": keyword` and `"engine": "google"` with `"tbm": "nws"`. The plan's `ingestion.py` correctly uses `"q"` and `"engine": "google"` — good. But it omits `"tbm": "nws"` from the `discover_articles()` payload. This means the SERP call hits general Google search, not Google News. The `tbm` parameter is in the spec's canonical payload signature and must be present.

---

### 🟡 Medium Issues (functional gaps that will hurt the demo)

**6. Call 3 is called once per article, not once per batch.**
The spec says graph extraction runs "per source," which the plan correctly models. But `extract_all_graphs()` in the plan makes N separate LLM calls in a loop. With 15 articles, that's 15 consecutive DeepSeek V4-Pro thinking-mode calls — each taking potentially 10–30 seconds. With Modal's 600-second timeout and 15 articles, you're looking at 225–450 seconds for Call 3 alone, leaving very little headroom for Calls 1, 2, 4, and scraping. Consider parallelizing with `asyncio.gather` or batching multiple articles into a single Call 3 prompt. The spec doesn't prohibit batching, and the 20-doc hard cap (Section 10) implicitly assumes the timeout won't be blown.

**7. `compute_pre_synthesis_context` is left as a stub in Tasks 6 and 11.**
Task 6 ships a placeholder that returns empty dicts. Task 11 says "implement it." The plan's critical path note at the bottom says Tasks 1-8 + 10 are the critical path and Task 11 is deferred. But if `compute_pre_synthesis_context` returns empty structures, Call 4 will receive no `narrative_clusters`, `fracture_candidates`, or `term_shifts` — meaning all three new v1.4 output objects (`reality_divergence_zones`, `reality_fractures`, `narrative_regime_shifts`) will be empty arrays in the final report. This effectively makes v1.4's entire new forensic layer dead on arrival for the demo. Task 11 needs to be on the critical path.

**8. `serp_data` is not passed to `build_ingestion_manifest`.**
The plan's `app.py` calls `discover_articles()` first (gets `serp_data`), then passes it to `build_ingestion_manifest()`. That's correct structurally. But `build_ingestion_manifest()` in `ingestion.py` also takes `serp_data` as a parameter — and the plan correctly threads it through. However, the SERP response used by `build_search_context_table()` in `processing.py` during Call 1 must be the *same raw response object* from step 1. The plan does pass `serp_data` to `run_entity_normalization()` — this is fine, but needs a note in the integration task to ensure it's the raw pre-parsed response, not a filtered version.

**9. Reputation records are not injected into the Call 4 input bundle.**
The spec's Section 6 (Call 4) says the input bundle must include "Reputation records from SQLite for each outlet domain." The plan's `context_bundle` dict in `app.py` has no reputation data — it includes graphs, omission indices, and pre-synthesis context, but never reads `outlet_reputation` rows and includes them. Call 4 will have no reputation context to generate `reputation_warnings` from.

**10. `run_historical_backtest` is never decorated as a `@app.function` in `backtest.py`.**
The spec's Section 7 shows it decorated as a Modal function so `.spawn()` works. Task 7 ships a plain Python function with no Modal decorator. Task 12 says "wire spawn in app.py" but if the function isn't a Modal `@app.function`, `.spawn()` will throw. The backtest is Phase 2, but the registration hook in `app.py` already has a `# TBD: spawn background back-test` comment that implies it'll be wired during the hackathon. Either add the decorator in Task 7, or explicitly move the `app.py` spawn wiring to Phase 2 in the scope boundary.

---

### 🟢 Minor Issues / Clean-ups

**11. `LlamaSlotConfig` typo in Task 1 sanity check.**
The sanity check comment says: "Does `LlamaSlotConfig` match the `llm_config.json` structure?" — should be `LLMSlotConfig`. Not a code bug, but will confuse whoever reads the plan before implementation.

**12. `merge_and_resolve` referenced but never defined.**
Section 14.2C of the spec mentions "Ensure `merge_and_resolve` downstream handles a completely empty PAA list predictably." Neither the spec nor the plan defines this function anywhere. If this is a real downstream dependency, it needs a home — probably inside `build_search_context_table` or the Call 1 prompt builder. If it's just a conceptual note from the spec author, it should be renamed to something concrete (e.g., "ensure `run_entity_normalization` handles empty PAA list").

**13. 20-doc hard cap is not implemented in `build_ingestion_manifest`.**
Section 10 specifies a hard cap of 20 documents per cluster run with a `CORPUS_CAPPED` flag. The plan's `build_ingestion_manifest()` has no such cap. Given the timeout risk (#6 above), this is more urgent than it appears.

**14. `trafilatura` is already in the plan's `image_recipe` pip_install.**
The spec's changelog note (the inline note before Section 1) flags that `trafilatura` was missing from the image recipe. The plan correctly includes it. This is already fixed — just noting it doesn't need attention.

**15. `outlet_name` is never populated in `handle_outlet_registration`.**
The `outlet_reputation` schema has an `outlet_name` column. The plan's `handle_outlet_registration()` only inserts `domain`, `industry_vertical`, `rating_status`, and `last_updated` — `outlet_name` stays NULL. Minor, but the UI renders outlet names and the reputation warning banner uses `outlet_name` from the DB row. The `source_name` field is available in the doc dict at registration time and should be threaded in.

---

### Summary Prioritization

Before kicking off implementation, I'd address these in this order:

1. **Fix #5** (missing `tbm` in SERP payload) — one-line fix, breaks the entire discovery pass if missed
2. **Fix #4** (`passed_validation` missing from return dict) — one-line fix
3. **Fix #3** (ingestion log never written) — add `write_ingestion_log()` call in `build_ingestion_manifest`
4. **Fix #1 + #2** (Vf in wrong layer, no clean `run_analysis_layer`) — architectural, needs a clear decision: either accept Vf staying in the orchestrator and document it as a deliberate deviation, or add a proper analysis layer wrapper
5. **Fix #9** (reputation data missing from Call 4 bundle) — DB read needed before building `context_bundle`
6. **Move Task 11 to critical path** (#7) — the v1.4 forensic objects will be hollow without it
7. **Fix #13** (20-doc cap) — add before timeout risk becomes a demo problem
8. **Fix #10** (Modal decorator on backtest) — if spawn wiring is happening during the hackathon