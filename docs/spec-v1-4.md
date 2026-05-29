# NARRATIVE ALPHA — FORENSIC TRACKER
## Implementation Specification v1.5
**Hackathon:** Bright Data Web Data UNLOCKED | May 25–30, 2026  
**Track:** Finance & Market Intelligence  
**Status:** Authoritative. Supersedes v1.4 and all prior versions.

**v1.5 Changes (specification drift correction):**
- Section 3: Corpus floor gate JSON example corrected — added missing top-level `status` field matching `FloorGateResponse` Pydantic model
- Section 4 (Contract A): `IngestionDocument` updated with optional `published_at` field; `IngestionManifest` updated with optional `corpus_capped` flag. Pydantic models in `contracts.py` are the runtime source of truth — spec examples are descriptive, not exhaustive

**v1.1 Changes:**
- Section 5.1: $O_i$ node matching now routes through Call 1 canonical dictionary before set subtraction
- Section 6: Calls 3 & 4 updated with confirmed DeepSeek V4 thinking-mode JSON extraction pattern; `base_url` corrected
- Section 7: Cold-start back-test decoupled to non-blocking `.spawn()` background task
- Section 8: Hardened orchestration with `get_hardened_db_connection()`, SQLite WAL mode, `busy_timeout=30000`

**v1.2 Changes:**
- Section 4 (Contract A): Added `title` field to Ingestion Manifest schema
- Section 14 (New): Concrete Layer 1 implementation — validation gates, Bright Data API payload signatures, ingestion log schema; four corrections applied

**v1.3 Changes:**
- Section 9: LLM provider/model made runtime-configurable per call slot via `llm_config.json`; settings UI added to MVP scope
- Section 12: Settings UI moved to explicit MVP scope item
- Section 14.2C (New): SERP Search Context Reference Table injection into Call 1 prompt

**v1.4 Changes:**
- Platform identity sharpened throughout: forensic narrative analysis system, not misinformation detection or fact arbitration
- Section 4 (Contract B): Three new output objects added — `reality_divergence_zones`, `reality_fractures`, `narrative_regime_shifts`
- Section 5 (New — 5.5, 5.6, 5.7): Metric/label definitions for consensus stability, institutional convergence, fracture relationship classification, and narrative synchronization
- Section 6 (Call 4 expanded): Cross-corpus term-frequency aggregation step added as pre-synthesis Python pass; all three new output objects added to Call 4 input bundle
- Section 11: Frontend Zone 2 and Zone 3 updated with new panels — Reality Divergence Zones, Reality Fractures, Narrative Regime Shifts

---

One thing to add to your pip install list in Section 8 before implementation: trafilatura (referenced in 14.2B for HTML stripping) is still not in the image_recipe block. Worth adding that alongside openai, requests, pydantic, numpy.

---

## SECTION 1: SYSTEM OVERVIEW & FINANCIAL FEASIBILITY

### What This System Does
Narrative Alpha ingests news articles about a target event from multiple media outlets, extracts a structured knowledge graph from each, computes a consensus baseline from the intersection of those graphs, and surfaces exactly how each outlet deviated — via factual omission, linguistic camouflage, or framing volatility — relative to that baseline. Outlier claims from single sources are tracked over time against a historical outlet reputation ledger.

### Stack Summary
| Component | Technology | Purpose |
|---|---|---|
| Scraping | Bright Data SERP API + Web Unlocker | Article discovery and full-text extraction |
| Fast LLM | `deepseek-v4-flash` (non-thinking mode) | Entity normalization, linguistic neutralization |
| Reasoning LLM | `deepseek-v4-pro` (thinking mode enabled) | Graph extraction, forensic synthesis |
| Embeddings | OpenAI `text-embedding-3-small` | Cosine distance for $V_f$ calculation |
| Persistence | SQLite on Modal Volume | Outlet reputation ledger (`outlet_reputation.db`) |
| Compute | Modal Serverless (CPU, 2-core, 4GiB) | Orchestration runtime |
| Frontend | Static HTML/JS | Read-only dashboard consuming JSON |

### Cost Profile Per Cluster Run (8 articles, ~5 outlets)
- Modal compute: ~$0.002 per 60-second run → negligible under free tier
- Bright Data: SERP API + Web Unlocker, pay-per-successful-request only
- DeepSeek V4-Flash: $0.10/M input tokens (normalization + neutralization passes)
- DeepSeek V4-Pro: pricing at 75% discount until May 31, 2026; schedule full-price post-hackathon review
- OpenAI embeddings: `text-embedding-3-small` at $0.02/M tokens → negligible
- **No managed external vector DB. No Cognee. No graph database.**  
  All state is SQLite + Python dictionaries on a persistent Modal Volume.

---

## SECTION 2: ARCHITECTURE

### Layer Diagram
```
┌─────────────────────────────────────────────────────────┐
│                    1. INGESTION LAYER                   │
│  Bright Data SERP API → URL list                        │
│  Bright Data Web Unlocker → raw article text            │
│  Output: Ingestion Manifest JSON                        │
└──────────────────────────────┬──────────────────────────┘
                               │ Ingestion Manifest
                               ▼
┌─────────────────────────────────────────────────────────┐
│              2. PROCESSING LAYER                        │
│  Call 1: DeepSeek V4-Flash → Entity Normalization       │
│  Call 2: DeepSeek V4-Flash → Linguistic Neutralization  │
│  Output: Normalized text blocks + Neutralized baselines │
└──────────────────────────────┬──────────────────────────┘
                               │ Structured text payloads
                               ▼
┌─────────────────────────────────────────────────────────┐
│              3. ANALYTICAL LAYER                        │
│  Call 3: DeepSeek V4-Pro (thinking) → Graph Extraction  │
│  Python: Set math → Omission Index, Consensus Baseline  │
│  Call 4: DeepSeek V4-Pro (thinking) → Forensic Synthesis│
│  Python: Cosine distance → Framing Volatility Score     │
│  Python: SQLite read/write → Reputation metrics         │
│  Output: Complete Forensic Report JSON                  │
└──────────────────────────────┬──────────────────────────┘
                               │ Forensic Report JSON
                               ▼
┌─────────────────────────────────────────────────────────┐
│              4. PRESENTATION LAYER (MVP)                │
│  Static web dashboard — read-only JSON consumer         │
│  Route: /event/{cluster_id}                             │
│  Post-MVP: Obsidian vault export (Phase 2 only)         │
└─────────────────────────────────────────────────────────┘
```

### Decoupling Rules (Enforced)
- **Layer 1** contains zero LLM calls, zero metric logic.
- **Layer 2** contains zero analysis logic. It normalizes text only.
- **Layer 3** is a stateless function: same inputs always produce same outputs (reputation ledger reads are injected as inputs, not internal state).
- **Layer 4** contains zero processing logic. It renders JSON.

---

## SECTION 3: BRIGHT DATA PRODUCT INTEGRATION

### Products Used
1. **SERP API** — keyword/topic search to discover article URLs across news sources
2. **Web Unlocker API** — full article body extraction through anti-bot proxy layer
3. **Bright Data MCP Server** (bonus product) — can be invoked for agent-driven ad-hoc queries in the demo UI

### Orchestration Model: Synchronous Single-Endpoint
All Bright Data calls are **synchronous** within the single Modal endpoint. No webhooks, no async polling, no volume-watch triggers. The pipeline runs top-to-bottom in one request:

```
User submits keyword → SERP API returns N URLs → Web Unlocker fetches N article bodies
→ LLM pipeline → JSON report returned
```

Async mode is not used because cluster sizes (5–15 articles) are well within synchronous throughput limits. Async is reserved for potential future batch-mode processing (Phase 2).

### Layer 1 Detailed Logic
```python
# Step 1: Discover article URLs via SERP API
POST https://api.brightdata.com/serp/req
{
  "query": "{user_keyword}",
  "engine": "google_news",
  "num": 15,
  "country": "us"
}
  # Extract organic result URLs from response

  # Step 2: Fetch full article text via Web Unlocker (Direct API Access)
  POST https://api.brightdata.com/request
  Headers:
    Content-Type: application/json
    Authorization: Bearer {BRIGHTDATA_API_KEY}
  Body:
  {
    "zone": "{web_unlocker_zone_name}",
    "url": "{article_url}",
    "format": "raw"
  }
  # Strip HTML boilerplate with trafilatura, extract raw_text_content
  # Repeat per URL; collect into Ingestion Manifest
```

### Corpus Floor Gate
If fewer than **5 unique source domains** are successfully retrieved after deduplication, the pipeline halts and returns:
```json
{
  "status": "INSUFFICIENT_CORPUS_FLOOR",
  "validation_tracking": {
    "current_state": "INSUFFICIENT_CORPUS_FLOOR",
    "minimum_required": 5,
    "current_count": 3
  }
}
```
No LLM calls are made. No credits are consumed.

---

## SECTION 4: DATA CONTRACTS

### Contract A — Ingestion Manifest (Layer 1 → Layer 2)
```json
{
  "cluster_id": "EVT-20260528-TECH-SEMI",
  "trigger_type": "KEYWORD",
  "search_query": "Fab 7 manufacturing halt",
  "timestamp_utc": "2026-05-28T12:00:00Z",
  "corpus_count": 7,
  "corpus_capped": false,
  "documents": [
    {
      "doc_id": "DOC-001",
      "source_name": "Global Corporate News Wire",
      "source_domain": "globalwire.com",
      "source_url": "https://globalwire.com/fab7-status",
      "title": "Fab 7 Production Line Halted Following Power Anomaly",
      "scrape_timestamp": "2026-05-28T12:05:00Z",
      "published_at": "2026-05-28T10:00:00Z",
      "raw_text_content": "..."
    }
  ]
}
```

### Contract B — Forensic Report (Layer 3 → Layer 4)
```json
{
  "event_meta": {
    "cluster_id": "EVT-20260528-TECH-SEMI",
    "search_query": "Fab 7 manufacturing halt",
    "industry_vertical": "TECHNOLOGY",
    "timestamp_utc": "2026-05-28T13:00:00Z",
    "corpus_count": 7
  },
  "consensus_reality_graph": {
    "consensus_summary": "Fab 7 microchip production operations completely halted on May 28 at 02:00 UTC due to an unspecified localized grid anomaly. Normal operations estimated to resume within 48 hours.",
    "verified_anchor_nodes": ["Fab 7", "Operations Halted", "May 28 02:00 UTC", "48-hour resumption estimate"],
    "primary_verifications": [
      {
        "authority": "Municipal Energy Regulatory Filing",
        "reference_id": "REG-POWER-9042",
        "status": "VERIFIED"
      }
    ]
  },
  "distortion_matrix": [
    {
      "outlet_name": "Global Corporate News Wire",
      "source_domain": "globalwire.com",
      "omission_index": 0.65,
      "omission_label": "HIGH",
      "framing_volatility_score": 0.12,
      "framing_volatility_label": "LOW",
      "identifiable_omissions": [
        "Omitted that the secondary backup generator arrays completely failed to cycle on."
      ],
      "linguistic_camouflage": [
        {
          "raw_expression": "minor power interruption",
          "clinical_translation": "Complete physical grid line severance"
        }
      ]
    }
  ],
  "outlier_signals": [
    {
      "signal_id": "SIG-8041",
      "origin_outlet": "The Tainan Industrial Insider",
      "origin_domain": "tainanindustrial.com",
      "extracted_claim": "The backup grid system did not fail due to a transformer surge; internal industrial control systems were manually overridden via a compromised service account originating outside the region.",
      "timestamp_first_seen": "2026-05-28T12:10:00Z",
      "outlier_origin_provenance": {
        "classification": "SINGLE_SOURCE_ORIGIN",
        "historical_origin_validation_rate": 0.84,
        "scatter_shot_anomaly_factor": 0.21,
        "scatter_shot_label": "LOW",
        "reputation_warning_triggered": false,
        "echo_chamber_mimics": []
      },
      "validation_tracking": {
        "current_state": "UNVERIFIED_BY_CONSENSUS",
        "last_checked_timestamp": "2026-05-28T12:45:00Z",
        "consensus_absorption_status": "PENDING",
        "evaluation_window_days": 30
      }
    }
  ],
  "reputation_warnings": [
    {
      "outlet_name": "Some Outlet",
      "source_domain": "someoutlet.com",
      "warning_triggered": true,
      "historical_origin_validation_rate": 0.84,
      "scatter_shot_anomaly_factor": 0.72,
      "scatter_shot_label": "HIGH",
      "warning_message": "This outlet holds an 84% baseline accuracy rate in TECHNOLOGY but registers a 72% Scatter-Shot Anomaly Factor. They routinely front-run true details but lace them inside high volumes of hyper-volatile narrative noise. Filter outputs carefully."
    }
  ],
  "reality_divergence_zones": [
    {
      "topic": "Cause of Fab 7 shutdown",
      "consensus_stability": "LOW",
      "consensus_stability_score": 0.21,
      "institutional_convergence": "UNRESOLVED",
      "observed_narrative_structures": [
        "Localized grid instability",
        "Cybersecurity breach",
        "Internal systems failure",
        "Planned maintenance anomaly"
      ],
      "supporting_outlets": {
        "Localized grid instability": ["globalwire.com", "marketindustrial.net"],
        "Cybersecurity breach": ["tainanindustrial.com"],
        "Internal systems failure": ["techpulse.io"],
        "Planned maintenance anomaly": ["statechronicle.gov"]
      }
    }
  ],
  "reality_fractures": [
    {
      "fracture_id": "RF-1004",
      "topic": "Root cause of outage",
      "claim_a": {
        "statement": "The outage resulted from transformer overload.",
        "supporting_outlets": ["globalwire.com", "industrialobserver.net"]
      },
      "claim_b": {
        "statement": "The outage resulted from unauthorized remote override activity.",
        "supporting_outlets": ["tainanindustrial.com"]
      },
      "relationship": "STRUCTURALLY_CONTRADICTORY",
      "resolution_status": "UNRESOLVED",
      "classification_method": "LLM_ASSISTED"
    }
  ],
  "narrative_regime_shifts": [
    {
      "shift_id": "NRS-2201",
      "topic": "Infrastructure event terminology",
      "detected_shift": {
        "previous_term": "power outage",
        "replacement_term": "service interruption"
      },
      "observed_across": 6,
      "total_sources": 8,
      "synchronization_score": 0.75,
      "synchronization_label": "HIGH",
      "interpretive_note": "Institutional language converged toward softened operational terminology across the majority of sources."
    }
  ]
}
```

**Schema note:** `omission_label` and `framing_volatility_label` are computed in Python using threshold rules (see Section 5) before the JSON is finalized. The frontend never computes labels — it only renders them.

---

## SECTION 5: METRICS DEFINITIONS & COMPUTATION

### 5.1 Information Omission Index ($O_i$)
$$O_i = \frac{\text{Count of Consensus Nodes Missing from Source Graph}}{\text{Total Count of Consensus Baseline Nodes}}$$

**Label thresholds:**
- `LOW`: $O_i < 0.25$
- `MED`: $0.25 \leq O_i < 0.50$
- `HIGH`: $O_i \geq 0.50$

**Computation:** Python set subtraction, but nodes are first resolved through the Call 1 canonical identity dictionary before comparison. Raw LLM string variants (e.g., `"Fab 7 Halt"` vs `"Operations Halted"`) are mapped to their canonical ID token before the set operation, preventing false omission inflation from minor wording differences across separate LLM invocations.

```python
def resolve_to_canonical(node: str, canonical_map: dict) -> str:
    """Map a node string to its canonical identity, or return as-is if not in map."""
    return canonical_map.get(node.strip().lower(), node)

def compute_omission_index(consensus_nodes, source_nodes, canonical_map):
    canonical_consensus = {resolve_to_canonical(n, canonical_map) for n in consensus_nodes}
    canonical_source = {resolve_to_canonical(n, canonical_map) for n in source_nodes}
    missing_nodes = canonical_consensus - canonical_source
    omission_index = len(missing_nodes) / len(canonical_consensus)
    return omission_index, list(missing_nodes)
```

The `canonical_map` is built from the Call 1 normalization output: keys are lowercased surface form variants, values are canonical reference identities.

### 5.2 Framing Volatility Score ($V_f$)
$$V_f = 1 - \cos(\vec{e}_{raw}, \vec{e}_{neutralized})$$

Where $\vec{e}_{raw}$ is the embedding of the original article text and $\vec{e}_{neutralized}$ is the embedding of the DeepSeek V4-Flash neutralized baseline.

**Label thresholds:**
- `LOW`: $V_f < 0.25$
- `MED`: $0.25 \leq V_f < 0.55$
- `HIGH`: $V_f \geq 0.55$

**Embedding model:** `text-embedding-3-small` via OpenAI API.  
**No edit distance.** Cosine distance only — single number, reproducible.

### 5.3 Scatter-Shot Anomaly Factor ($S_a$)
$$S_a = \frac{\text{Count of Permanently Decayed Outlier Nodes}}{\text{Total Outlier Nodes Produced by Outlet}}$$

**Label thresholds:**
- `LOW`: $S_a < 0.35$
- `MED`: $0.35 \leq S_a < 0.60$
- `HIGH`: $S_a \geq 0.60$

**Reputation Warning Banner triggers when:** $S_a \geq 0.60$ AND `historical_origin_validation_rate` data exists (i.e., outlet is not `UNRATED`).

**Decayed node definition:** An outlier node that has not been absorbed into the consensus graph after 30 days is marked `DECAYED` and counted in the $S_a$ numerator.

### 5.4 Consensus Baseline ($G_c$)
A node or edge is included in the consensus baseline if it appears in **> 75% of source graphs** (rounded up: requires $\lceil 0.75 \times N \rceil$ sources where $N$ is corpus count).

Minimum corpus required: **5 unique source domains.** Below this floor, no consensus math is attempted.

---

### 5.5 Reality Divergence Zone — Consensus Stability Score

Measures how fragmented the institutional narrative landscape is around a specific topic sub-cluster. Computed after Call 3 graph extraction by grouping competing causal or descriptive claims about the same entity or event node.

$$\text{Consensus Stability Score} = 1 - \frac{\text{Count of Distinct Competing Narrative Structures} - 1}{\text{Total Sources Covering Topic}}$$

**Label thresholds:**
- `HIGH`: score $\geq 0.70$ — one narrative structure dominates
- `MED`: $0.40 \leq$ score $< 0.70$ — two or three competing structures
- `LOW`: score $< 0.40$ — four or more competing structures, no dominant view

**`institutional_convergence` field:**
- `RESOLVED`: one narrative structure holds $> 75\%$ source support
- `CONTESTED`: one structure leads but holds $50\text{–}75\%$ support
- `UNRESOLVED`: no structure holds $> 50\%$ support

---

### 5.6 Reality Fracture — Relationship Classification

Fractures are detected in Call 4 via LLM-assisted classification. The model is prompted to evaluate whether two canonical claims about the same topic node are logically compatible.

**`relationship` values (MVP):**
- `STRUCTURALLY_CONTRADICTORY` — the two claims cannot simultaneously be true without major reconciliation (e.g., "transformer failure" vs. "remote override")
- `ORTHOGONAL` — the claims address different aspects of the same event and do not directly conflict (not surfaced in UI as a fracture)

**`resolution_status` values:**
- `UNRESOLVED` — no source has retracted, corrected, or converged on one claim
- `PARTIALLY_RESOLVED` — one claim has gained majority support but the minority claim persists in at least one active source

**Implementation caveat:** Fracture classification is LLM-generated, not symbolic logic. Edge cases exist where orthogonal claims may be incorrectly flagged as contradictory, or genuinely contradictory claims may be missed if phrased with sufficient euphemistic distance. The `classification_method: "LLM_ASSISTED"` field in the output schema makes this origin explicit. The UI framing — "highlights incompatibility, not truth certification" — is the correct intellectual frame.

---

### 5.7 Narrative Regime Shift — Synchronization Score

Measures the degree to which a terminology migration is coordinated across sources rather than organic and isolated.

$$\text{Synchronization Score} = \frac{\text{Sources Using Replacement Term}}{\text{Total Sources Covering Topic}}$$

**Label thresholds:**
- `LOW`: score $< 0.35$ — isolated usage, likely organic
- `MED`: $0.35 \leq$ score $< 0.65$ — partial adoption, mixed signals
- `HIGH`: score $\geq 0.65$ — majority adoption, potentially coordinated

**Computation:** Pure Python term-frequency comparison across all neutralized article texts (Call 2 output). This is a pre-synthesis aggregation step in the Call 4 input bundle, not a new LLM call. The raw term-pair candidates (previous term → replacement term) are detected by scanning for cases where synonymous canonical entities from the Call 1 normalization map appear in the raw (un-neutralized) text at different rates across sources. The most frequent divergent pairs become regime shift candidates passed to Call 4 for interpretive note generation.

---

## SECTION 6: LLM CALL SEQUENCE (4 CALLS PER CLUSTER RUN)

### Call 1 — Entity Normalization (DeepSeek V4-Flash, non-thinking)
**Purpose:** Resolve naming variants across articles to canonical identities before graph extraction. Feeds Pipeline B (canonical stream used for $O_i$).

**System prompt:**
```
You are an entity normalization engine. Given a set of raw article text fragments, 
identify all named entities and map every surface-form variant to a single canonical 
reference identity. Output only valid JSON matching the schema provided. 
Do not include preamble, explanation, or markdown fences.
```

**Output schema:**
```json
{
  "normalized_mappings": [
    {
      "surface_form_variant": "The Tainan Hub",
      "canonical_reference_identity": "Fab 7"
    }
  ]
}
```

### Call 2 — Linguistic Neutralization (DeepSeek V4-Flash, non-thinking)
**Purpose:** Strip all adjectives, emotional framing, adverbial padding, and corporate/political euphemisms from each article. Output is the baseline text used to compute $V_f$ cosine distance.

**System prompt:**
```
You are a linguistic neutralization engine. Transform the input text into a flat, 
clinical sequence of declarative active-verb statements. Strip all qualifying 
adjectives, descriptive idioms, adverbial padding, and corporate designations. 
Preserve only: named entities, actions, timestamps, quantities, and locations. 
Output plain text only. No JSON. No markdown.
```

**Output:** Plain text string per article. Stored alongside raw text for embedding generation.

### Call 3 — Structural Graph Extraction (DeepSeek V4-Pro, thinking enabled)
**Purpose:** Extract a structured node-and-edge list from each article (using normalized entity dictionary from Call 1 applied first). This is the foundation for all set-math operations.

**Implementation pattern (confirmed against DeepSeek V4 API docs):**
```python
from openai import OpenAI
import json, os

client = OpenAI(
    base_url="https://api.deepseek.com",   # canonical URL — no /v1 suffix
    api_key=os.environ["DEEPSEEK_API_KEY"]
)

def execute_graph_extraction(normalized_text: str, entity_dict: dict) -> dict:
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a knowledge graph extraction engine. Given the normalized "
                    "article text and entity reference dictionary, extract all factual "
                    "claims as a structured node-and-edge graph. Nodes are named entities, "
                    "events, timestamps, and quantities. Edges are directed relationships "
                    "with a verb. Output only valid JSON matching the schema provided. "
                    "The word 'json' must appear in your response."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Entity dictionary: {json.dumps(entity_dict)}\n\n"
                    f"Article text: {normalized_text}\n\n"
                    "Return a json object with 'nodes' (list of strings) and "
                    "'edges' (list of objects with source, target, relationship_verb)."
                )
            }
        ],
        extra_body={"thinking": {"type": "enabled"}},
        response_format={"type": "json_object"},
        temperature=0.1
    )
    # Thinking chain is in response.choices[0].message.reasoning_content (internal only).
    # Final JSON is always in response.choices[0].message.content — parse directly.
    return json.loads(response.choices[0].message.content)
```

**Important:** `response_format={"type": "json_object"}` and thinking mode are compatible on V4 models. The thinking chain is isolated in `reasoning_content`; `content` always contains the clean final JSON. Never parse `reasoning_content`.

**Output schema:**
```json
{
  "nodes": ["Fab 7", "Operations Halted", "May 28 02:00 UTC"],
  "edges": [
    {
      "source": "Fab 7",
      "target": "Operations Halted",
      "relationship_verb": "experienced"
    }
  ]
}
```

### Call 4 — Forensic Synthesis (DeepSeek V4-Pro, thinking enabled)
**Purpose:** Given the full analytical context assembled from Calls 1–3 and Python pre-processing, synthesize the complete Forensic Report JSON payload including all three new forensic analysis objects.

**Pre-synthesis Python pass (runs before Call 4, no LLM required):**

This step aggregates cross-corpus signals that Call 4 needs as structured input. It operates entirely on data already computed:

```python
def compute_pre_synthesis_context(
    all_source_graphs: list,        # Call 3 outputs, one per doc
    neutralized_texts: list,        # Call 2 outputs, one per doc
    canonical_map: dict,            # Call 1 output
    consensus_nodes: list           # Gc computed after Call 3
) -> dict:
    """
    Produces three structured inputs for Call 4:
    1. competing_narrative_clusters — groups sources by causal claim per topic node
    2. candidate_fracture_pairs     — claim pairs flagged for contradiction check
    3. term_frequency_shifts        — synonym pair adoption rates across sources
    """

    # 1. Group sources by their causal/descriptive claim per consensus topic node
    # Sources asserting different edge relationships on the same node = divergence zone candidates
    narrative_clusters = {}  # topic -> {claim_text -> [source_domains]}

    # 2. Find claim pairs where the same topic node has edges pointing to
    # semantically distant targets across different sources
    fracture_candidates = []  # [(topic, claim_a, outlets_a, claim_b, outlets_b)]

    # 3. Term frequency shift detection across neutralized texts
    # For each canonical entity pair in canonical_map, count raw-text usage rates
    # of each surface form variant across all un-neutralized article texts
    term_shifts = []  # [{previous_term, replacement_term, observed_across, total_sources}]

    # ... implementation detail left to code agent per above logic
    return {
        "narrative_clusters": narrative_clusters,
        "fracture_candidates": fracture_candidates,
        "term_shifts": term_shifts
    }
```

**Uses same client pattern as Call 3** (`extra_body={"thinking": {"type": "enabled"}}`, `response_format={"type": "json_object"}`). Parse `response.choices[0].message.content` only.

**Input bundle passed as context:**
- Consensus baseline graph ($G_c$)
- Per-source graphs with pre-computed $O_i$ values and canonical-resolved missing node lists
- Neutralized text pairs for camouflage detection
- Reputation records from SQLite for each outlet domain
- Outlier signals (nodes appearing in only one source)
- `narrative_clusters` — competing narrative structures per topic node (from pre-synthesis pass)
- `fracture_candidates` — claim pairs for contradiction classification (from pre-synthesis pass)
- `term_shifts` — term frequency migration candidates with adoption counts (from pre-synthesis pass)

**Output:** Complete Contract B JSON (Section 4) including:
- All existing fields (`consensus_reality_graph`, `distortion_matrix`, `outlier_signals`, `reputation_warnings`)
- `reality_divergence_zones` — populated from `narrative_clusters` + stability scoring
- `reality_fractures` — populated from `fracture_candidates` with LLM contradiction classification per pair
- `narrative_regime_shifts` — populated from `term_shifts` with LLM-generated `interpretive_note` per detected shift

No post-processing required except label injection (done in Python via threshold rules in Sections 5.1–5.7).

**Positioning constraint enforced in prompt:** Call 4's system prompt must explicitly instruct the model that it is analyzing *how* reality is being described across institutional sources — not determining which description is objectively correct. The output must reflect narrative topology, not truth arbitration. This framing is non-negotiable and must survive prompt iteration.

---

## SECTION 7: REPUTATION PERSISTENCE LAYER

### Storage: SQLite on Modal Volume
**File path:** `/root/.narrative_alpha/outlet_reputation.db`  
**Bound via:** `modal.Volume` persisted across runs

### Schema
```sql
CREATE TABLE outlet_reputation (
  domain TEXT PRIMARY KEY,
  outlet_name TEXT,
  industry_vertical TEXT,
  total_outlier_nodes_produced INTEGER DEFAULT 0,
  total_absorbed_nodes INTEGER DEFAULT 0,
  total_decayed_nodes INTEGER DEFAULT 0,
  scatter_shot_anomaly_factor REAL DEFAULT NULL,
  historical_origin_validation_rate REAL DEFAULT NULL,
  back_test_article_count INTEGER DEFAULT 0,
  rating_status TEXT DEFAULT 'UNRATED',
  last_updated TEXT
);

CREATE TABLE outlier_tracking (
  signal_id TEXT PRIMARY KEY,
  cluster_id TEXT,
  origin_domain TEXT,
  extracted_claim TEXT,
  timestamp_first_seen TEXT,
  current_state TEXT DEFAULT 'PENDING',
  evaluation_deadline TEXT,
  absorbed INTEGER DEFAULT 0
);
```

### Cold-Start Seeding (New Outlet First Encounter)
When an outlet domain appears for the first time, the main pipeline **must not block**. The pattern is:

1. Check SQLite: `SELECT rating_status FROM outlet_reputation WHERE domain = ?`
2. If no row exists: **immediately** insert `rating_status = 'UNRATED'` and continue the main pipeline
3. Fire the back-test as a **detached background task** via `modal.Function.spawn()` — it runs asynchronously in a separate container and does not affect the main request's response time or timeout

```python
def handle_outlet_registration(domain: str, vertical: str, db_conn):
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT rating_status FROM outlet_reputation WHERE domain = ? AND industry_vertical = ?",
        (domain, vertical)
    )
    row = cursor.fetchone()

    if not row:
        # Register instantly as UNRATED — never block the main pipeline
        cursor.execute(
            "INSERT INTO outlet_reputation (domain, rating_status, industry_vertical, last_updated) "
            "VALUES (?, 'UNRATED', ?, datetime('now'))",
            (domain, vertical)
        )
        db_conn.commit()

        # Detach the heavy back-test to a background worker — fire and forget
        run_historical_backtest.spawn(domain, vertical)

# Decorated as a separate Modal function so .spawn() works
@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
    timeout=600
)
def run_historical_backtest(domain: str, vertical: str):
    """
    Non-blocking background task. Runs after main pipeline returns.
    1. SERP API: site:{domain} news, date filter past 12 months, up to 15 articles
    2. Web Unlocker: fetch article bodies
    3. If < 5 articles retrieved: leave rating_status = 'UNRATED', exit
    4. Call 1 + Call 3 on historical articles against present-day ground truth
    5. Count absorbed vs decayed nodes
    6. Write Sa, historical_origin_validation_rate, rating_status = 'RATED' to SQLite
    7. vol.commit()
    """
    from backtest import execute_historical_backtest
    execute_historical_backtest(domain, vertical)
    vol.commit()
```

**Result for the main pipeline:** First-encounter outlets display `UNRATED` in the UI immediately. The reputation score populates on subsequent pipeline runs once the background task completes.

---

## SECTION 8: ORCHESTRATION — `app.py`

```python
import modal
import sqlite3
import os

vol = modal.Volume.from_name("narrative-alpha-vault", create_if_missing=True)

image_recipe = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "openai",       # DeepSeek (OpenAI-compatible) + embeddings
        "requests",     # Bright Data HTTP calls
        "pydantic",     # Schema validation
        "numpy",        # Cosine distance
        "trafilatura",  # HTML stripping for Web Unlocker extraction
    )
)

app = modal.App(name="narrative-alpha-core")


def get_hardened_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Establishes a SQLite connection resilient to concurrent Modal worker instances.
    WAL mode: reads never block writes; writes never block reads.
    busy_timeout: concurrent writers queue gracefully up to 30s instead of failing.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)   # Python timeout in seconds
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")     # SQLite-level timeout in ms
    return conn


@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
    timeout=600
)
@modal.web_endpoint(method="POST")
async def execute_forensic_pipeline(payload: dict) -> dict:
    """
    Single synchronous entry point.
    Input:  { "keyword": "Fab 7 manufacturing halt", "vertical": "TECHNOLOGY" }
    Output: Complete Forensic Report JSON (Contract B)

    Execution sequence:
    1.  SERP API → discover article URLs
    2.  Web Unlocker → fetch article bodies
    3.  Corpus floor gate (min 5 unique source domains)
    4.  Outlet reputation check (SQLite) — register UNRATED + spawn backtest if new
    5.  Call 1: DeepSeek V4-Flash → entity normalization → build canonical_map
    6.  Call 2: DeepSeek V4-Flash → linguistic neutralization per article
    7.  Embed raw + neutralized texts (OpenAI) → compute Vf cosine distances
    8.  Call 3: DeepSeek V4-Pro (thinking) → graph extraction per source
    9.  Python: resolve nodes via canonical_map → consensus graph Gc → Oi per source
    10. Call 4: DeepSeek V4-Pro (thinking) → forensic synthesis → Contract B JSON
    11. Python: inject LOW/MED/HIGH labels via threshold rules
    12. Write reputation updates to SQLite via hardened connection
    13. vol.commit()
    14. Return final report JSON
    """
    from ingestion import run_ingestion_layer
    from processing import run_processing_layer
    from analysis import run_analysis_layer

    db_path = os.path.join(os.environ["NARRATIVE_ALPHA_ROOT"], "outlet_reputation.db")

    ingestion_manifest = await run_ingestion_layer(payload)

    if ingestion_manifest["corpus_count"] < 5:
        return {
            "validation_tracking": {
                "current_state": "INSUFFICIENT_CORPUS_FLOOR",
                "minimum_required": 5,
                "current_count": ingestion_manifest["corpus_count"]
            }
        }

    # Outlet registration: instant UNRATED write + non-blocking backtest spawn
    db_conn = get_hardened_db_connection(db_path)
    for doc in ingestion_manifest["documents"]:
        handle_outlet_registration(doc["source_domain"], payload["vertical"], db_conn)
    db_conn.close()

    processed_payload = await run_processing_layer(ingestion_manifest)
    final_report = await run_analysis_layer(processed_payload)

    vol.commit()
    return final_report
```

---

## SECTION 9: ENVIRONMENT CONFIGURATION & RUNTIME LLM PROVIDER SETTINGS

### 9.1 Static Secrets (`.env.production`)

API keys and infrastructure credentials. These never change at runtime.

```bash
MODAL_ENVIRONMENT="production"

# Bright Data
BRIGHTDATA_API_KEY="bd_api_key_from_hackathon"
BRIGHTDATA_SERP_ZONE="serp_zone_name"
BRIGHTDATA_UNLOCKER_ZONE="unlocker_zone_name"
BRIGHTDATA_CUSTOMER_ID="customer_id"

# LLM Provider API Keys (all loaded; active provider selected via llm_config.json)
DEEPSEEK_API_KEY="sk-deepseek-api-key"
OPENAI_API_KEY="sk-proj-openai-key"
GOOGLE_API_KEY="google-api-key"
GROQ_API_KEY="groq-api-key"

# OpenAI embeddings (fixed — not user-switchable in MVP)
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

# Storage
NARRATIVE_ALPHA_ROOT="/root/.narrative_alpha"
```

### 9.2 Runtime LLM Configuration (`llm_config.json`)

Stored at `/root/.narrative_alpha/llm_config.json` on the Modal Volume. Written and read at runtime — no redeployment required to switch providers or models. The settings UI reads and writes this file directly via a dedicated Modal GET/POST endpoint.

Each of the four LLM call slots is independently configurable. This allows mixing providers (e.g., Groq for speed on normalization, DeepSeek Pro for reasoning on synthesis) without touching any pipeline code.

```json
{
  "call_1_entity_normalization": {
    "provider": "deepseek",
    "model": "deepseek-v4-flash",
    "thinking": false,
    "temperature": 0.1
  },
  "call_2_linguistic_neutralization": {
    "provider": "deepseek",
    "model": "deepseek-v4-flash",
    "thinking": false,
    "temperature": 0.1
  },
  "call_3_graph_extraction": {
    "provider": "deepseek",
    "model": "deepseek-v4-pro",
    "thinking": true,
    "temperature": 0.1
  },
  "call_4_forensic_synthesis": {
    "provider": "deepseek",
    "model": "deepseek-v4-pro",
    "thinking": true,
    "temperature": 0.1
  }
}
```

**Supported provider values:** `"deepseek"` | `"openai"` | `"google"` | `"groq"`

**Provider base URLs (resolved in code, not config):**
| Provider | Base URL | Notes |
|---|---|---|
| `deepseek` | `https://api.deepseek.com` | OpenAI-compatible SDK |
| `openai` | `https://api.openai.com/v1` | Native OpenAI SDK |
| `google` | `https://generativelanguage.googleapis.com/v1beta/openai/` | OpenAI-compatible endpoint |
| `groq` | `https://api.groq.com/openai/v1` | OpenAI-compatible SDK |

All four providers expose an OpenAI-compatible chat completions interface, so the same client code works for all — only `base_url`, `api_key`, and `model` change per call.

**`thinking` flag behavior:** Only meaningful for DeepSeek (`extra_body={"thinking": {"type": "enabled"}}`). Ignored silently for other providers.

### 9.3 LLM Client Factory

```python
import json
import os
from openai import OpenAI

def load_llm_config() -> dict:
    config_path = os.path.join(os.environ["NARRATIVE_ALPHA_ROOT"], "llm_config.json")
    with open(config_path) as f:
        return json.load(f)

def get_llm_client(provider: str) -> OpenAI:
    """Returns an OpenAI-compatible client for the given provider."""
    api_keys = {
        "deepseek": os.environ["DEEPSEEK_API_KEY"],
        "openai":   os.environ["OPENAI_API_KEY"],
        "google":   os.environ["GOOGLE_API_KEY"],
        "groq":     os.environ["GROQ_API_KEY"],
    }
    base_urls = {
        "deepseek": "https://api.deepseek.com",
        "openai":   "https://api.openai.com/v1",
        "google":   "https://generativelanguage.googleapis.com/v1beta/openai/",
        "groq":     "https://api.groq.com/openai/v1",
    }
    return OpenAI(
        api_key=api_keys[provider],
        base_url=base_urls[provider]
    )

def call_llm(slot_config: dict, messages: list, json_mode: bool = True) -> str:
    """
    Executes a single LLM call using the slot's provider/model config.
    Returns response.choices[0].message.content as a string.
    """
    client = get_llm_client(slot_config["provider"])

    kwargs = {
        "model": slot_config["model"],
        "messages": messages,
        "temperature": slot_config.get("temperature", 0.1),
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if slot_config.get("thinking") and slot_config["provider"] == "deepseek":
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content
```

### 9.4 Settings UI Specification

A lightweight settings page served as a second route on the frontend dashboard.

**Route:** `/settings`

**UI elements — one row per call slot:**
| Call Slot | Provider dropdown | Model text input | Thinking toggle | Temperature slider |
|---|---|---|---|---|
| Call 1: Entity Normalization | ✅ | ✅ | — | ✅ |
| Call 2: Linguistic Neutralization | ✅ | ✅ | — | ✅ |
| Call 3: Graph Extraction | ✅ | ✅ | ✅ | ✅ |
| Call 4: Forensic Synthesis | ✅ | ✅ | ✅ | ✅ |

Thinking toggle only renders for DeepSeek provider selection. On save, the frontend POSTs the updated config to a `/settings` Modal endpoint that writes `llm_config.json` to the volume and calls `vol.commit()`. No pipeline redeployment required.

**Dedicated Modal endpoint:**
```python
@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
)
@modal.web_endpoint(method="POST")
async def update_llm_config(payload: dict) -> dict:
    """
    Accepts updated llm_config.json payload from settings UI.
    Validates structure, writes to volume, commits.
    """
    config_path = os.path.join(os.environ["NARRATIVE_ALPHA_ROOT"], "llm_config.json")
    required_slots = [
        "call_1_entity_normalization",
        "call_2_linguistic_neutralization",
        "call_3_graph_extraction",
        "call_4_forensic_synthesis"
    ]
    for slot in required_slots:
        if slot not in payload:
            return {"error": f"Missing required slot: {slot}"}
    with open(config_path, "w") as f:
        json.dump(payload, f, indent=2)
    vol.commit()
    return {"status": "ok", "config": payload}
```

---

## SECTION 10: FAILURE MODES & MITIGATIONS

| Failure | Root Cause | Mitigation |
|---|---|---|
| Paywall / bot block on article URL | News site blocks cloud container IP | All fetches route through Web Unlocker. Native `requests` calls to article URLs are forbidden. |
| SERP returns < 5 unique domains | Niche topic with thin coverage | Corpus floor gate returns `INSUFFICIENT_CORPUS_FLOOR`. No LLM spend. |
| DeepSeek JSON parse failure | Model outputs malformed JSON | Wrap all LLM calls in try/catch with one retry. On second failure, mark document as `PARSE_ERROR` and exclude from corpus. If exclusion drops count below 5, return floor error. |
| Cold-start back-test returns < 5 articles | Niche outlet with thin archive | Write `UNRATED` to SQLite. No reputation banner rendered. No dummy data written. |
| Context window saturation (>100 articles) | Single cluster grows very large | Hard cap ingestion at **20 documents per cluster run**. Log a `CORPUS_CAPPED` flag in event meta. |
| Modal memory overflow | Dense iterative loops on large text | Text chunked to max 2,000 tokens before embedding. `vol.commit()` called after each major phase. |
| SQLite write contention under concurrent workers | Multiple Modal containers writing `outlet_reputation.db` simultaneously | WAL mode + `busy_timeout=30000` serializes concurrent writers gracefully. At expected throughput (handful of reputation writes per run) lock wait time is negligible. |
| Back-test `.spawn()` silent failure | Background Modal function errors without surfacing to main pipeline | Back-test failures leave outlet at `UNRATED` — safe degraded state. Errors logged to Modal function logs. Main pipeline unaffected. |

---

## SECTION 11: FRONTEND DASHBOARD SPECIFICATION

### Routing
- **Index page** (`/`): List of all processed cluster IDs with timestamps and verticals
- **Cluster page** (`/event/{cluster_id}`): Full forensic report for one event

### Layout — Three Stacked Zones (per ASCII spec)

**Zone 1 — Consensus Truth Baseline**
- Renders `consensus_reality_graph.consensus_summary`
- Lists `verified_anchor_nodes`
- Lists `primary_verifications` with status badges

**Zone 2 — Media Distortion Matrix**
- Table: one row per entry in `distortion_matrix`
- Columns: Outlet Name | $O_i$ (float + label badge) | $V_f$ (float + label badge) | Detected Text Camouflage (raw → clinical pairs)
- Label badges use color: LOW = green, MED = amber, HIGH = red

**Zone 2 sub-panel — Narrative Regime Shifts**
- Rendered below the distortion matrix table, inside Zone 2
- One terminal-style alert card per entry in `narrative_regime_shifts`
- Each card displays: detected term migration (previous → replacement), synchronization score + label, source adoption count (`observed_across` / `total_sources`), interpretive note
- `HIGH` synchronization label renders in red; `MED` in amber; `LOW` in muted grey
- Visual framing: "the language architecture surrounding this event shifted in a coordinated manner"
- Empty state: panel is hidden if `narrative_regime_shifts` array is empty

**Zone 3 — Forensic Analysis of Outlier Signals**
- Reputation Warning Banner: renders for each entry in `reputation_warnings` where `warning_triggered: true`
- Outlier Signal Cards: one card per entry in `outlier_signals`

**Zone 3 sub-panel — Reality Divergence Zones**
- One forensic conflict block per entry in `reality_divergence_zones`
- Displays: topic, consensus stability score + label, institutional convergence status, list of competing narrative structures with their supporting outlet domains
- `LOW` stability renders with fracture-state warning colors (deep amber or red border)
- `UNRESOLVED` convergence status renders with a pulsing or high-contrast indicator
- Visual framing: "multiple institutional realities currently coexist"
- Critical UI rule: the panel must not imply one narrative structure is correct. It presents the landscape of descriptions, not a verdict.

**Zone 3 sub-panel — Reality Fractures**
- One forensic conflict card per entry in `reality_fractures`
- Each card displays: fracture topic, Claim A (statement + supporting outlets), Claim B (statement + supporting outlets), relationship label, resolution status
- `STRUCTURALLY_CONTRADICTORY` relationship renders with high-contrast conflict styling
- `UNRESOLVED` status renders prominently
- Critical UI rule: no "winner" is declared. The card surfaces incompatibility only. The `classification_method: "LLM_ASSISTED"` tag is visible in the card footer so users understand the classification is model-generated, not formally proven.
- Empty state: panel is hidden if `reality_fractures` array is empty

### Data Source
Frontend fetches JSON directly from the Modal endpoint response, stored as static `.json` files in a `/data/{cluster_id}.json` path on a lightweight static file server (or served directly from Modal as a GET endpoint).

### Aesthetic Direction
Terminal/forensic intelligence console aesthetic. Dark background. Monospace data elements. Color-coded alert states. Minimal decoration — the data density is the design. Inspired by financial trading terminals and investigative journalism tools.

---

## SECTION 12: SCOPE BOUNDARIES

### MVP (This Hackathon)
- ✅ Keyword-triggered cluster pipeline
- ✅ Bright Data SERP + Web Unlocker integration
- ✅ 4-call LLM processing sequence
- ✅ $O_i$, $V_f$, $S_a$ metric computation
- ✅ Reputation cold-start back-testing
- ✅ SQLite persistence on Modal Volume
- ✅ Static web dashboard with 3-zone layout
- ✅ Corpus floor gate
- ✅ Reputation warning banner
- ✅ Runtime LLM provider/model settings UI (`/settings` route, per-slot configuration)

### Post-MVP / Phase 2
- ❌ Global Trend Gateway (auto-discovery of trending headlines)
- ❌ Obsidian vault export and markdown file healing
- ❌ 30-day outlier absorption monitoring (infrastructure exists; scheduler not wired)
- ❌ Bright Data async/webhook mode for batch processing
- ❌ Multi-vertical stratification UI

---

## SECTION 13: KNOWN ANALYTICAL BLIND SPOTS

This section is preserved intentionally for intellectual honesty in the demo.

**The Consensus Trap:** The system tracks an outlet's capacity to front-run what the consensus group eventually acknowledges — not objective truth. If a true investigative disclosure is successfully suppressed and never acknowledged by mainstream sources, the system will permanently classify that true node as a decayed outlier anomaly. This is a structural limitation, not a bug, and should be disclosed to users.

**LLM Hallucination Risk in Graph Extraction:** Entity normalization and graph extraction are LLM-generated. Custom firm names, internal facility designations, and local technical jargon should ideally be passed as a reference taxonomy in context to prevent hallucinated entity merging. For the MVP, this is not implemented; accuracy depends on DeepSeek V4-Pro's world knowledge.

**$S_a$ Cold-Start Neutrality:** Outlets with fewer than 5 historical articles return `UNRATED`. This is honest but means new or niche outlets receive no reputation signal at all on first encounter.

---

## SECTION 14: INGESTION LAYER CONCRETE IMPLEMENTATION

### 14.1 Microscopic Quality Validation Gates

Before any crawled payload advances to Layer 2, it must pass a strict programmatic validation gate. Documents that fail any deterministic criterion are dropped immediately. If the surviving pool falls below 5 unique source domains, the pipeline aborts with `INSUFFICIENT_CORPUS_FLOOR`.

**Title threading note:** `title` is populated from the SERP API discovery pass (available in the structured `parsed_light` response) and carried through to the Web Unlocker extraction pass. By the time `validate_ingestion_payload` runs, `title` is always present in the doc dict.

```python
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse

def validate_ingestion_payload(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Enforces Layer 1 quality checks on scraped text.
    Returns the validated document if clean, or None if rejected.
    """
    raw_text = doc.get("raw_text_content", "").strip()
    title = doc.get("title", "").strip()
    source_url = doc.get("source_url", "").strip()

    # 1. Structural prerequisite checks
    if not source_url or not title:
        return None

    # Extract and normalize canonical domain
    try:
        domain = urlparse(source_url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        doc["source_domain"] = domain
    except Exception:
        return None

    # 2. Character and word count floor
    # Reject empty bodies and shell pages
    if len(raw_text) < 300:
        return None
    words = raw_text.split()
    if len(words) < 50:
        return None

    # 3. Paywall / authentication gate detection
    paywall_patterns = [
        r"sign\s*in\s*to\s*continue",
        r"create\s*an\s*account",
        r"subscribe\s*to\s*read",
        r"exclusive\s*subscriber\s*content",
        r"log\s*in\s*or\s*register",
        r"members\-only\s*story"
    ]
    if any(re.search(p, raw_text, re.IGNORECASE) for p in paywall_patterns):
        return None

    # 4. Nav-bloat / boilerplate scrape detection
    # Reject pages that are overwhelmingly navigation fragments
    nav_tokens = ["cookie", "privacy policy", "all rights reserved",
                  "terms of service", "share this article"]
    nav_hits = sum(1 for token in nav_tokens if token in raw_text.lower())
    if nav_hits > 3 and len(raw_text) < 1500:
        return None

    # Compute passed_validation flag (1 = clean, recorded in ingestion log)
    passed_validation = 1

    return {
        "doc_id": doc.get("doc_id"),
        "source_name": doc.get("source_name", domain),
        "source_domain": domain,
        "source_url": source_url,
        "title": title,
        "scrape_timestamp": doc.get("scrape_timestamp"),
        "author": doc.get("author", "Staff"),
        "raw_text_content": raw_text,
        "passed_validation": passed_validation
    }
```

---

### 14.2 Bright Data API Core Query Payload Signatures

#### A. Discovery Pass — SERP API

**Target URL:** `https://api.brightdata.com/serp/req`

Using `engine: "google"` with `tbm: "nws"` explicitly targets the Google News tab rather than relying on an engine alias. `parsed_light: true` returns structured article snippets and metadata directly in the response without an additional fetch pass.

```json
{
  "engine": "google",
  "q": "Fab 7 manufacturing halt",
  "tbm": "nws",
  "num": 15,
  "gl": "us",
  "hl": "en",
  "parsed_light": true
}
```

Extract `title`, `source_name`, `source_url`, and `published_at` from the structured SERP response before the extraction pass. These fields are carried forward into the doc dict so `validate_ingestion_payload` always receives a populated `title`.

#### B. Extraction Pass — Web Unlocker API (Direct API Access)

**Target URL:** `https://api.brightdata.com/request`  
**Auth:** `Authorization: Bearer <BRIGHTDATA_API_KEY>` header  
**Verified against Bright Data docs (May 2026).** Direct API access is the recommended method. Zone name goes in the JSON body — no `?zone=` query param.

> **v1.4 Correction:** Spec previously used `/unblocker/req` and `/web-unlocker/req`. Both incorrect. Canonical endpoint is `/request`.

Web Unlocker handles fingerprinting, header spoofing, and CAPTCHA solving internally via zone configuration. No additional proxy headers needed.

```json
{
  "zone": "<web_unlocker_zone_name>",
  "url": "https://globalwire.mock/fab7-status",
  "format": "raw"
}
```

Headers:
```
Content-Type: application/json
Authorization: Bearer <BRIGHTDATA_API_KEY>
```

`format: "raw"` returns the target site's raw HTML. Strip boilerplate with `trafilatura` before passing `raw_text_content` into the doc dict.

#### C. Search Context Reference Table Injection (Call 1 Boundary)

When constructing the prompt for **Call 1 (Entity Normalization)**, the pipeline prepends a structured markdown context block built from the raw SERP response. This injects Google's pre-computed synonym resolution work — worth millions in algorithmic investment — as free low-token context that anchors DeepSeek V4-Flash's entity mapping before it sees any article text.

**Why this matters:** If one article says `"Fab 7 halted"` and another says `"The Tainan Advanced Semiconductor Facility paused operations"`, Google's ranking algorithms have already linked these phrases in the SERP snippet and PAA arrays. Feeding that signal to the normalization model before it runs prevents the two phrases from being treated as independent unrelated entities, directly reducing false $O_i$ inflation downstream.

`people_also_ask` entries are included when present — they are the highest-value synonym signal, as they represent alternate human query phrasings Google has explicitly cross-referenced to the same event. If the key is absent from the SERP response (e.g., due to a Google layout update), the block degrades gracefully to titles and snippets only without any code change or pipeline interruption.

```python
def build_search_context_table(serp_data: dict) -> str:
    """
    Extracts titles, snippets, and conditional PAA data from the SERP response
    to seed DeepSeek's entity-normalization layer with a zero-cost synonym map.
    Prepended to the Call 1 system prompt as ## SYSTEM SEARCH CONTEXT REFERENCE.
    """
    context_lines = ["## SYSTEM SEARCH CONTEXT REFERENCE\n"]
    context_lines.append("| Type | Content Source / Query Variant | Contextual Text Snippet |")
    context_lines.append("| :--- | :--- | :--- |")

    # 1. Core SERP result titles and snippets
    for item in serp_data.get("organic", []):
        title = item.get("title", "").replace("|", "-")
        domain = item.get("display_link", "")
        snippet = item.get("snippet", "").replace("|", "-")
        if title and snippet:
            context_lines.append(f"| RESULT | {title} ({domain}) | {snippet} |")

    # 2. People Also Ask — conditional, graceful fallback if absent
    for paa in serp_data.get("people_also_ask", []):
        question = paa.get("question", "").replace("|", "-")
        answer = paa.get("answer", "").replace("|", "-")
        if question and answer:
            context_lines.append(
                f"| PAA_SYNONYM | ALTERNATE QUERY: {question} | CROSS-REFERENCE: {answer} |"
            )

    return "\n".join(context_lines)
```

**Integration point:** The returned string is prepended to the Call 1 system prompt before the article text blocks, separated by a `---` divider:

```python
search_context = build_search_context_table(serp_response)
call_1_system_prompt = f"{search_context}\n\n---\n\n{ENTITY_NORMALIZATION_BASE_PROMPT}"
```

**Known failure mode — structural selector volatility:** `parsed_light: true` relies on Bright Data's continuous scraping adaptations to output structured keys like `people_also_ask`. If Google pushes an unannounced layout update during the hackathon, the key may temporarily disappear or its child keys (`question`, `answer`) may rename. The graceful fallback means the pipeline will not crash — it silently degrades to titles and snippets only. If a demo relies on a synonym that was exclusively resolved via a PAA cross-reference, entity normalization accuracy will degrade without warning. Ensure `merge_and_resolve` downstream handles a completely empty PAA list predictably.

---

### 14.3 Ingestion Manifest Log Schema

Persistent log of every scrape attempt written to `/root/.narrative_alpha/outlet_reputation.db`. Used for pipeline debugging during the hackathon and as the data source for 30-day outlier absorption tracking (Phase 2).

```sql
CREATE TABLE IF NOT EXISTS ingestion_manifest_log (
    query_id          TEXT    NOT NULL,
    topic             TEXT    NOT NULL,
    discovery_timestamp TEXT  NOT NULL,
    source_domain     TEXT    NOT NULL,
    canonical_url     TEXT    NOT NULL PRIMARY KEY,
    title             TEXT    NOT NULL,
    published_at      TEXT,
    -- fetch_status: HTTP status code returned by Web Unlocker (200, 403, 429, etc.)
    -- Primary signal for diagnosing extraction failures during the demo.
    fetch_status      INTEGER,
    body_text         TEXT    NOT NULL,
    body_length       INTEGER NOT NULL,
    -- passed_validation: 1 = cleared all Layer 1 gates, 0 = rejected (row still logged for debugging)
    passed_validation INTEGER NOT NULL DEFAULT 0
);
```

**Note on rejected documents:** Rows with `passed_validation = 0` are still written to the log (with `body_text` as the raw failed content) so extraction failures are visible during the demo. They are excluded from all downstream LLM processing.