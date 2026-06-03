# Narrative Alpha — Forensic Narrative Analysis Platform

Narrative Alpha is a forensic narrative analysis platform for news intelligence. It systematically discovers what news outlets are **saying**, what they are **not saying**, and **how** they are saying it relative to a multi-source baseline.

It is **not** a fact-checker, a misinformation detector, a summarization RAG system, or an autonomous agent. It maps **narrative topology** — the structure of what the institutional press agrees on, who omitted what, who spun it, and whose claims are isolated outliers.

---

## What It Does

Given a keyword and an industry vertical, Narrative Alpha:

1. **Discovers** news articles about that topic from a broad set of sources
2. **Ingests and validates** each article against quality gates
3. **Normalizes entities** across all articles (resolving synonyms — "AI", "artificial intelligence", "machine learning" — to canonical identities)
4. **Strips linguistic bias** from each article, producing a neutralized version
5. **Extracts structured knowledge graphs** from both the original and neutralized text
6. **Computes a consensus baseline** — the set of entities and facts that most sources agree on
7. **Measures each outlet's deviation** from the consensus across four metrics
8. **Synthesizes a forensic report** that surfaces exactly how each outlet distorted coverage

The result is a structured report organized into three forensic zones, described below.

---

## The Pipeline (7 Steps)

### Step 1: Discovery

A keyword search is executed against a news search API. Results include article URLs, headlines, publishers, publication dates, and snippets. A `time_range` parameter limits results to a configurable window (e.g., past month, past year). The goal is to assemble a diverse set of sources covering the same topic.

### Step 2: Ingestion and Validation

Each discovered article URL is fetched in parallel. Raw HTML is extracted and cleaned into plain text. Each article then passes through a series of quality gates:

- **Minimum length:** At least 300 characters and 50 words
- **Paywall detection:** 6 patterns for sign-in gates, subscriber-only content, and login walls
- **Boilerplate detection:** If navigation boilerplate exceeds a threshold and the body is short, the article is rejected

Articles are deduplicated by source domain (only one article per outlet). A hard cap of 20 documents is enforced. If fewer than 5 valid articles survive, the pipeline stops with an "insufficient corpus" signal.

### Step 3: Outlet Registration and Historical Backtesting

Each outlet that hasn't been rated before is registered in a reputation database. A background backtest runs in parallel for each unrated outlet: it searches for the outlet's past reporting on the same vertical, compares those claims against a baseline from other sources, and computes the outlet's **historical origin validation rate** and **scatter-shot anomaly factor**. Backtests run with a global timeout of two minutes; any that don't complete leave the outlet as "unrated" for the current report.

### Step 4: Entity Normalization (LLM Call 1)

All articles are sent to an LLM alongside a reference table built from the search results (titles, snippets, "People Also Ask" questions). The LLM maps every surface-form variant of each entity to a single canonical identity. Example:

| Surface Form | Canonical |
|---|---|
| "AI" | artificial intelligence |
| "artificial intelligence" | artificial intelligence |
| "machine learning" | artificial intelligence |
| "ML models" | artificial intelligence |

This ensures that "the Federal Reserve" and "the Fed" and "the central bank" are treated as the same entity throughout the analysis. If this step fails, the pipeline continues in degraded mode with an empty mapping.

### Step 5: Linguistic Neutralization (LLM Call 2)

Each article is sent to an LLM and stripped of emotional framing, qualifying adjectives, descriptive idioms, adverbial padding, euphemisms, and spin. The output preserves only: named entities, actions, timestamps, quantities, and locations. This produces a "neutralized" version alongside the original text.

Example:

| Original | Neutralized |
|---|---|
| "The controversial bill narrowly passed" | "The bill passed" |
| "A staggering surge in unemployment" | "Unemployment increased" |
| "The administration quietly admitted" | "The administration admitted" |

### Step 6: Graph Extraction and Metric Computation (LLM Call 3 + Set Math)

Each neutralized article is sent to an LLM to extract a structured knowledge graph: a set of **nodes** (entities, concepts) and **edges** (relationships between them). This runs in parallel across all documents.

From the collected graphs, four metrics are computed:

**Consensus Baseline (Gc):** A set of nodes that appear in at least 60% of sources. This represents the common ground — what most outlets agree is worth mentioning.

**Omission Index (Oi):** For each outlet, the fraction of consensus nodes that are missing from its graph. A high omission index means the outlet left out widely-reported facts.

**Framing Volatility (Vf):** The cosine distance between embeddings of the original and neutralized versions of each article. High volatility means the outlet's original text was heavily spun — the neutralized version looks very different from what was actually published.

**Scatter-Shot Anomaly (Sa):** Computed per-outlet during the historical backtest. The fraction of an outlet's claims that contradict or lie outside the multi-source consensus. A high scatter-shot factor flags an outlet as a persistent outlier.

### Step 7: Synthesis (LLM Call 4)

A comprehensive context bundle is assembled containing all 20 articles (truncated to 5000 characters each), all four metrics, the consensus baseline, per-outlet graphs, omission lists, fracture candidates (pairs of contradictory claims across sources, capped at 30 per topic), and term shifts (coordinated terminology changes).

This context bundle is sent to the most capable LLM (with reasoning enabled) to produce the **ForensicReport**. The LLM performs:

- **Narrative clustering:** Groups claims by topic across all outlets
- **Fracture identification:** Identifies structurally contradictory claims on the same topic
- **Narrative regime shift detection:** Spots coordinated vocabulary changes (e.g., a group of outlets all switching from "climate change" to "climate crisis" simultaneously)
- **Reputation warnings:** Flags outlets where scatter-shot anomaly is high enough to warrant distrust
- **Reality divergence zoning:** Identifies topics where narratives diverge so much that no stable consensus exists

After the LLM returns its JSON, the pipeline post-processes it: injects numeric-to-label mappings (e.g., Oi < 0.25 → "LOW"), overwrites metadata with ground truth (cluster ID, search query, article count), and writes outlier signals to the tracking database. The final report is saved as a JSON file.

---

## The Forensic Report (Three Zones)

### Zone 1 — Consensus Truth Baseline

What the majority of sources agree on:

- **Consensus summary:** A human-readable narrative of the agreed-upon facts
- **Verified anchor nodes:** The specific entities and concepts that appear across 60%+ of sources
- **Primary verifications:** External reference citations that the LLM identified as well-supported

### Zone 2 — Media Distortion Matrix

How each outlet deviated from consensus, presented as a table:

- **Omission index** (Oi): Which consensus facts each outlet left out, with a severity label
- **Framing volatility** (Vf): How much linguistic spin was detected, with a severity label
- **Detected camouflage:** Specific examples of loaded language paired with their neutralized renderings
- **Narrative regime shifts:** Detected term transitions across the corpus (e.g., ~~"illegal aliens"~~ → "undocumented immigrants"), including what fraction of sources made the shift and how synchronized the change was

### Zone 3 — Forensic Analysis of Outlier Signals

Things that don't fit the consensus:

- **Reputation warnings:** Outlets with a history of high scatter-shot anomaly
- **Outlier signals:** Claims made by only one source, flagged for monitoring with an evaluation deadline
- **Reality divergence zones:** Topics where sources disagree so fundamentally that no consensus can be computed
- **Reality fractures:** Side-by-side comparisons of structurally contradictory claims on the same topic (no winner declared — the fracture is surfaced for human judgment)
- **Narrative regime shifts** (cross-referenced from Zone 2): Coordinated terminology changes treated as a signal of narrative engineering

---

## Key Features

- **Multi-provider LLM orchestration:** Four distinct LLM slots, each independently configurable for provider and model. Slots 1–3 (entity normalization, neutralization, graph extraction) use a fast, cheap model. Slot 4 (synthesis) uses the most capable model with reasoning enabled. Each slot can be set to a different provider or model.

- **Parallel execution:** Article fetching (5 concurrent workers), graph extraction (5 concurrent workers), and historical backtests (4 concurrent workers) all run in parallel for performance.

- **Real-time streaming:** The pipeline streams progress events via Server-Sent Events (SSE), providing per-step status, per-article ingest results, and phase transition updates to the frontend.

- **Outlet reputation database:** SQLite-backed persistent store tracking outlet identity, historical scatter-shot anomaly, validation rate, and rating status (UNRATED / RATED / BLACKLISTED). Ratings persist across pipeline runs.

- **Outlier tracking:** Anomalous claims are written to an outlier tracking table with signal IDs, evaluation deadlines, and state management (PENDING / RESOLVED / ABSORBED).

- **Ingestion audit log:** Every scrape attempt (pass or fail) is logged to a manifest table with article text, timestamps, and validation outcomes.

- **Configurable thresholds:** Consensus ratio, time range, text truncation limits, per-slot LLM configuration — all adjustable without code changes.

- **Corpus floor gate:** The pipeline refuses to produce a report with fewer than 5 valid, distinct sources.

- **Session persistence:** Completed pipeline metadata is stored in session storage, allowing users to navigate away and return to the last completed report.

- **Three-zone visualization:** A dark-themed React dashboard renders the forensic report as three distinct visual zones with color-coded metrics, badges, pills, and progressive disclosure.

- **Health checking:** The server exposes env var validation, deep health checks (testing actual LLM calls), and configuration inspection endpoints.

- **Report management:** Reports are saved as JSON files and can be listed, viewed, and deleted through the API and UI.

---

## Architecture

```
                    ┌─────────────────────────────────┐
                    │      React Dashboard (Vite)     │
                    │  PipelineRunner  │  EventPage   │
                    │  HomePage        │  Settings    │
                    └──────┬──────────────────────────┘
                           │ HTTP / SSE
                    ┌──────▼──────────────────────────┐
                    │      FastAPI Server             │
                    │  /api/pipeline/stream  SSE      │
                    │  /api/reports CRUD              │
                    │  /api/health                    │
                    │  /api/config                    │
                    └──────┬──────────────────────────┘
                           │
               ┌───────────┼───────────────┐
               │           │               │
        ┌──────▼───┐ ┌────▼────┐  ┌──────▼───┐
        │Ingestion │ │Analysis │  │Processing│
        │          │ │         │  │          │
        │Discovery │ │Graph    │  │Entity    │
        │Fetch     │ │Extract  │  │Normalize │
        │Validate  │ │Metrics  │  │Neutralize│
        │Dedup     │ │Synthesis│  │          │
        └──────┬───┘ └────┬────┘  └──────────┘
               │           │
               │    ┌──────▼──────┐
               │    │ Reputation  │
               │    │ SQLite DB   │
               │    │ Backtest    │
               │    └─────────────┘
               │
        ┌──────▼──────┐
        │ Reports     │
        │ JSON files  │
        └─────────────┘
```

### Frontend Routes

| Route | Component | Purpose |
|---|---|---|
| `/` | HomePage | Pipeline runner + report list |
| `/event/:clusterId` | EventPage | Three-zone forensic report view |
| `/settings` | SettingsPage | LLM config, env health |

---

##  Implementation Details

### Specific Tool Choices

| Function | Tool | Why |
|---|---|---|
| News search API | Bright Data SERP API | Provides structured Google News results with reliable zone-based targeting and time range filtering |
| Article content extraction | Bright Data Web Unlocker | Handles anti-bot shields, paywall bypass, and JavaScript-rendered content; returns clean HTML for downstream processing |
| HTML-to-text conversion | trafilatura | Lightweight, fast, purpose-built for news article extraction; returns None gracefully when content isn't parseable |
| LLM — Call 1 (Entity Normalization) | DeepSeek V4 Flash | Fast (sub-second), cheap, sufficient for synonym resolution; no reasoning needed |
| LLM — Call 2 (Linguistic Neutralization) | DeepSeek V4 Flash | Same rationale as Call 1; high throughput for parallel article processing |
| LLM — Call 3 (Graph Extraction) | DeepSeek V4 Flash | Runs once per article in parallel (up to 20 concurrent calls); speed and cost are critical |
| LLM — Call 4 (Synthesis) | DeepSeek V4 Pro | Most capable model; reasoning enabled for complex structural analysis across 20 articles; highest token budget |
| Embeddings (framing volatility) | OpenAI text-embedding-3-small | Industry-standard embedding quality; hardcoded (not configurable) because the volatility metric requires consistent embedding space |
| Data validation | Pydantic v2 | Strict schema enforcement at every layer boundary; `extra="forbid"` catches LLM key drift |
| Test framework | pytest | Standard Python testing; monkeypatch-based HTTP mocking |
| Frontend framework | React 18 + TypeScript | Type-safe UI with Vite dev server and hash-based routing |
| SSE streaming | FastAPI + asyncio | Server-Sent Events for real-time pipeline progress; synchronous pipeline runs in executor thread |
| Storage — Reports | JSON files on disk | Simple, inspectable, no DB dependency; one file per report |
| Storage — Reputation | SQLite with WAL mode | Zero-config, file-based, concurrent-reader-friendly; WAL mode prevents writer lock contention |

### Limits and Issues Encountered

#### LLM Providers

- **JSON mode reliability:** LLMs occasionally return parseable JSON with unexpected field names. Pydantic's `extra="forbid"` catches these, but the pipeline must decide whether to retry or degrade. Currently, all four LLM calls retry once on JSON failures; Call 4 (synthesis) is particularly sensitive to structural drift because its output model is complex (8 nested sections).

- **Token limit errors:** The synthesis context bundle (all 20 articles + graphs + metrics) can overflow the model's context window in worst-case scenarios. With 10 topics × 40 claims × all pair combinations, the unstructured fracture candidate space grows as O(n²). Initial deployments hit a 1,214,606 token request against a 1,048,565 token limit. Mitigations enacted:
  - JSON serialization uses compact formatting (no indentation) — saves ~21%
  - Fracture candidates are capped at 30 pairs per topic — prevents O(n²) explosion
  - Text fields are truncated to 5000 characters per article
  - Worst-case payload now measures ~451,000 tokens (well under an 80% safety margin)

- **Provider heterogeneity:** Each provider has slightly different API semantics. DeepSeek requires `reasoning_content` in assistant messages for multi-turn calls. Google and Groq use different endpoint formats. The client layer normalizes these through a provider-specific function.

- **Embedding vendor lock:** Framing volatility uses OpenAI embeddings. If OpenAI is unavailable, the Vf metric silently degrades to `0.0`. This is a known weak point — the embedding model should ideally be configurable, but the metric's interpretability depends on a consistent embedding space across pipeline runs.

#### Bright Data

- **403 Forbidden (SERP):** The SERP API can return 403 errors with either "Blocked" (Geo-edge restriction) or "Forbidden" (account/payment issue) messages. Both raise `RuntimeError` with the HTTP code and body excerpt. The error message format changed during development from `raise_for_status()` output to explicit `response.ok` checking, which broke test mocks until they were updated.

- **Unlocker failures:** Web Unlocker can fail on certain paywalled or bot-sensitive sites. These are caught per-article (not per-pipeline), so a single failure doesn't block the entire run. The affected article is logged as a failed scrape in the ingestion manifest.

- **Latency:** Article fetching is the pipeline's slowest step (network I/O to arbitrary sites through a proxy). Parallelizing with 5 workers helps, but a run with 15-20 articles can spend 20-40 seconds in the ingestion phase alone.

#### Corpus Limitations

- **Domain deduplication:** Only one article per domain is kept. If Google News returns multiple results from the same outlet, only the first (highest-ranked) is used. This prevents any single outlet from dominating the corpus but may discard valuable multi-article coverage from major outlets.

- **Minimum 5 sources:** The pipeline refuses to run with fewer than 5 valid articles from distinct domains. This is a deliberate floor gate — a consensus baseline is meaningless with too few voices. But it means the tool can't analyze niche topics with sparse coverage.

- **60% consensus threshold:** A node must appear in at least 60% of source graphs to enter the consensus baseline. With 20 diverse sources, this requires 13 outlets to independently mention the same entity. This threshold was lowered from 75% (which required 16 of 20) to reduce "INSUFFICIENT_CONSENSUS" results with diverse sources.

#### LLM Extraction Quality

- **Graph extraction inconsistency:** Call 3's output varies between LLM providers. DeepSeek V4 Flash sometimes omits edges, produces duplicate nodes, or returns incomplete graphs. Each failed extraction places a placeholder graph with `_parse_error: True`, which is excluded from consensus computation. The pipeline continues with the remaining graphs.

- **Entity normalization drift:** Call 1 can over-normalize (mapping distinct entities to the same canonical, e.g., "Bitcoin" and "blockchain" both mapped to "cryptocurrency") or under-normalize (leaving synonyms unresolved). The reference table from SERP data helps but doesn't fully solve this. An empty normalization map from a failed Call 1 means the pipeline continues without synonym resolution — graphs will contain surface-form variants as separate nodes.

- **Synthesis quality varies by model:** Call 4's output quality depends heavily on the model and whether thinking/reasoning is enabled. With reasoning enabled (DeepSeek V4 Pro), fracture identification and regime shift detection are notably more precise. Without reasoning (or with a smaller model), the report tends to produce shallower analysis with more "no consensus" defaults.

#### Frontend

- **SSE reconnection:** If the server restarts mid-pipeline, the browser's EventSource auto-reconnects but the pipeline state is lost. The UI shows the pipeline as "running" indefinitely with no timeout. A server-reconnect guard was considered but not yet implemented.

- **TypeScript type alignment:** The frontend types must stay synchronized with the Pydantic models on the backend. Adding or renaming fields on the Python side without updating the TS interfaces causes silent runtime errors (undefined accesses in zone components). This is mitigated by the zone components using optional chaining and fallback renderings, but structural mismatches can still produce empty sections.

- **sessionStorage-only persistence:** Completed pipeline results survive browser tab navigation but not tab closure. If the user closes the tab, the "stored result" banner disappears. Report data is always available from the saved JSON file, but the convenience link is lost.

#### Testing

- **HTTP mock fragility:** All seven `FakeResp` mock classes in the ingestion test file had to be individually updated when the production code switched from `raise_for_status()` to `response.ok`. Inline mock classes are simple but create maintenance burden — any change to how the production code processes HTTP responses requires updating every mock independently. A shared test helper (`fake_response(ok=True, status_code=200, text="", json_data=None)`) would reduce this friction.

- **LLM-dependent tests:** Tests that exercise the pipeline end-to-end require valid API keys and incur per-call costs. The current test suite uses isolated unit tests with mocked HTTP and injected responses. Integration tests are manual.
