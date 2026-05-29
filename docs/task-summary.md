# Narrative Alpha — Task Summary

> Reference document — one paragraph per task with test counts.

---

## Task 1 (contracts.py)
**26 tests** — Pydantic models for Contract A (IngestionManifest, IngestionDocument), Contract B (ForensicReport with 8 sub-objects), LLM config (LLMConfig, LLMSlotConfig), and pipeline IO (PipelineInput, FloorGateResponse). Enforces `extra="forbid"` strict mode on all models, prevents silent field drift, and sets `__version__ = "1.4.1"`. 26 tests covering instantiation, defaults, out-of-range rejection, field-name validation, and three round-trip serialize/deserialize cycles.

---

## Task 2 (llm_client.py)
**46 tests** — Provider-agnostic LLM client factory supporting DeepSeek, OpenAI, Google, and Groq with thread-safe double-checked caching via `threading.Lock()`. Single `call_llm()` function across all 4 call slots with configurable retries (default 1 = 2 total attempts per spec Section 10), JSON mode validation, thinking-mode via `extra_body`, and narrow exception handling that re-raises `BaseException` subclasses (KeyboardInterrupt, CancelledError). 46 tests covering retry exhaustion, JSON parse failure recovery, None content guards, provider-specific base URL resolution, embedding model env override, and multi-turn assistant message extraction with reasoning_content.

---

## Task 3 (ingestion.py)
**49 tests** — Full Layer 1 pipeline: Bright Data SERP API discovery (Google News, parsed_light), Web Unlocker extraction via trafilatura, `parse_serp_result` domain normalization (never uses `source` field for URL parsing), and 6 programmatic validation gates (300-char floor, 50-word floor, 6 paywall regex patterns, 5 nav-bloat tokens with 1500-char exemption). Corpus floor gate returns `INSUFFICIENT_CORPUS_FLOOR` below 5 unique domains, 20-doc hard cap sets `corpus_capped=True`, and optional `logger_func`+`db_conn` wires ingestion logging without circular import. 49 tests.

---

## Task 4 (reputation.py)
**20 tests** — SQLite persistence with WAL-mode hardened connection, 3-table schema (outlet_reputation composite PK domain+vertical, outlier_tracking, ingestion_manifest_log composite PK canonical_url+query_id), and `_write_with_retry` for concurrent-write safety from background backtest worker. Cold-start outlet registration stores `outlet_name` on first encounter (Issue #15 fix), returns `UNRATED` immediately, and ingestion log uses per-doc atomic inserts to prevent connection poisoning on mid-batch failure. 20 tests including 4 mock-based retry/rollback/backoff tests for `_write_with_retry`.

---

## Task 5 (processing.py)
Layer 2 with search context table builder from SERP PAA data, Call 1 entity normalization via DeepSeek V4-Flash producing canonical identity map from surface-form variants, and Call 2 linguistic neutralization stripping emotional framing per article into clinical declarative statements. Outputs feed directly into Layer 3 graph extraction and Vf cosine distance computation. Embeddings generated via OpenAI text-embedding-3-small.

---

## Task 6 (analysis.py)
Layer 3 with Call 3 graph extraction via DeepSeek V4-Pro thinking mode (one per article, parallelizable via asyncio.gather), Python set-math for Omission Index Oi (canonical-resolved node subtraction), Consensus Baseline Gc (>75% source threshold), Scatter-Shot Anomaly Sa (decayed/total ratio), and Framing Volatility Vf (1 - cosine similarity of raw vs neutralized embeddings). Pre-synthesis pass aggregates narrative clusters, fracture candidates, and term-frequency shifts, then Call 4 produces complete Contract B JSON with label injection via threshold rules.

---

## Task 7 (backtest.py)
Background Modal `.spawn()` worker that runs SERP + extraction + Call 1 + Call 3 on up to 15 historical articles for a given outlet domain, computes absorbed vs decayed node counts, writes Sa + historical_origin_validation_rate + rating_status = `RATED` to SQLite. Runs asynchronously after main pipeline returns, never blocks the response timeout. Leaves outlet as `UNRATED` if fewer than 5 historical articles available.

---

## Task 8 (app.py)
Single Modal web endpoint orchestrating the full 13-step pipeline: SERP → Web Unlocker → floor gate → outlet registration + backtest spawn → Call 1 → Call 2 → embeddings → Call 3 → Python set-math → Call 4 → label injection → `vol.commit()`. Also exposes a `/settings` POST endpoint for runtime LLM config updates.

---

## Task 9 (dashboard/)
Static HTML/JS frontend with 3-zone forensic report layout: Zone 1 (consensus reality graph with verified anchor nodes and primary verifications), Zone 2 (distortion matrix table with Oi/Vf badges + narrative regime shift cards), Zone 3 (outlier signal cards + reputation warning banner + reality divergence zones + reality fracture cards). Dark terminal / forensic console aesthetic, green/amber/red color-coded labels, empty-state hiding for absent panels.

---

## Task 10 (settings UI)
`/settings` route with one form row per call slot: provider dropdown (deepseek / openai / google / groq), model text input, thinking toggle (visible only for DeepSeek), and temperature slider. Saves updated `llm_config.json` to Modal Volume via POST endpoint, calls `vol.commit()`. No pipeline redeployment required.
