# TECHNICAL SPECIFICATION: NARRATIVE ALPHA FORENSIC TRACKER

## Section 1: Pre-Implementation Sanity Check & Financial Feasibility
This architecture is designed to run entirely within modest cloud infrastructure allocations and free-tier operating caps:
* **Modal Compute Tier:** Modal's Starter Tier provides $30.00/month in free compute credits. Running standard CPU containers (2-core, 4 GiB memory) costs approximately $0.0000306 per execution second ($0.0021 per 60-second processing cycle), allowing over 14,000 cluster runs per month completely free.
* **Persistent Disk Volume Storage:** Cognee natively runs local-first database states (SQLite for metadata, LanceDB for vector shards, and Kuzu/Ladybug for graph storage engines). By binding a persistent `modal.Volume` to the app sandbox, the system eliminates the need for expensive managed external vector or graph cloud databases.
* **API Cost Controls:** The heavy lifting of programmatic entity-action-property mapping within Cognee's `.cognify()` pipeline is routed to **DeepSeek-Chat** ($0.14 per million input tokens). Premium reasoning tokens from **Claude-3-5-Sonnet** are strictly rationed and used only for the final comparative synthesis report and user interface rendering objects.

---

## Section 2: Architecture Isolation & Structural Separation
The application enforces four strict, decoupled abstraction boundaries. Communication across modules occurs exclusively via typed JSON schemas or file mutations over a shared cloud disk space.

```
┌────────────────────────────────────────────────────────┐
│                   1. INGESTION LAYER                   │
│  (Interfaces with Bright Data -> Emits Clean JSON)     │
└───────────────────────────┬────────────────────────────┘
│ (Raw JSON Payloads)
▼
┌────────────────────────────────────────────────────────┐
│              2. COGNITIVE PROCESSING LAYER             │
│ (Cognee E-C-L Pipeline -> Compiles Local Graph State)  │
└───────────────────────────┬────────────────────────────┘
│ (Topological Structural Maps)
▼
┌────────────────────────────────────────────────────────┐
│              3. ANALYTICAL DECONSTRUCTION LAYER       │
│  (Forensic Analysis Engine -> Generates Unified Metric)│
└───────────────────────────┬────────────────────────────┘
│ (The Unified Report Schema)
▼
┌────────────────────────────────────────────────────────┐
│               4. DUAL PRESENTATION LAYER               │
│ (Web Frontend Console   &&   Obsidian Relational Vault)│
└────────────────────────────────────────────────────────┘
```

### Layer 1: Ingestion & Extraction (The Scraper Intake)
* **Execution Boundary:** Communicates solely with the Bright Data proxy network.
* **Core Logic:** Accepts a target criteria string (Keyword or Trending front trigger), runs automated web searches via Bright Data SERP API, retrieves full article bodies through Web Unlocker or Scraping Browser proxies, strips out boilerplate scripts, and outputs a standardized data manifest.
* **Decoupling Rule:** This layer contains no LLM code, graph concepts, or UI parameters. If Bright Data alters its JSON responses, changes are isolated entirely to this module.

### Layer 2: Cognitive Processing (The Knowledge Storage Plane)
* **Execution Boundary:** Interfaces with the Cognee Python SDK and the attached storage volume.
* **Core Logic:** Ingests raw document arrays via `cognee.add()`. Invokes the JIT Split-Testing Entity Resolution strategy. Builds and grounds the vector and graph models via `cognee.cognify()`. Exposes programmatic graph query methods to output raw structural difference sets.
* **Decoupling Rule:** This layer does not evaluate news bias or format dashboards. Foundational providers are controlled entirely via environment configuration flags (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`), allowing you to swap core AI systems without changing code logic.

### Layer 3: Analytical Deconstruction (The Forensic Metric Brain)
* **Execution Boundary:** Interfaces with premium LLMs (Claude 3.5 Sonnet).
* **Core Logic:** Consumes the raw graph structures from Layer 2. Executes comparative analysis prompts to determine intentional factual omissions, track linguistic framing transformations, calculate industry-stratified drift metrics, and evaluate Outlier Origin Provenance.
* **Decoupling Rule:** This module behaves as a stateless mathematical function. It reads graph arrays and returns a single, comprehensive, frozen JSON intelligence payload.

### Layer 4: Presentation & Delivery (The User Interface Adapters)
* **Execution Boundary:** Read-only data consumption from Layer 3.
* **Core Logic:** Maps the structural payload concurrently to two targets:
    1. A web frontend client featuring independent URL pathways for each distinct event cluster.
    2. A Python generation function that formats and appends data into an Obsidian Relational Mesh Vault using idempotent block overrides.
* **Decoupling Rule:** This layer contains zero operational code, scraping logic, or data analysis steps. Modifying web styling or rewriting markdown templates will never break the data processing pipelines.

---

## Section 3: Inter-Module Data Contracts

### 1. Layer 1 to Layer 2: Ingestion Manifest Schema
```json
{
  "cluster_id": "EVT-20260528-TECH-SEMI",
  "trigger_type": "KEYWORD",
  "search_query": "Fab 7 manufacturing halt",
  "timestamp_utc": "2026-05-28T12:00:00Z",
  "documents": [
    {
      "doc_id": "DOC-001",
      "source_name": "Global Corporate News Wire",
      "source_url": "[https://globalwire.mock/fab7-status](https://globalwire.mock/fab7-status)",
      "scrape_timestamp": "2026-05-28T12:05:00Z",
      "author": "Staff Reporter",
      "raw_text_content": "Fab 7 experienced a minor power interruption today at 02:00 UTC. Normal manufacturing processes are scheduled to resume within 48 hours following standard safety recalibrations."
    }
  ]
}
```

### 2. Layer 3 to Layer 4: Complete System Output Payload

```
{
  "event_meta": {
    "cluster_id": "EVT-20260528-TECH-SEMI",
    "industry_vertical": "TECHNOLOGY",
    "consensus_summary": "Fab 7 microchip production operations halted on May 28 at 02:00 UTC."
  },
  "consensus_reality_graph": {
    "verified_anchor_nodes": ["Fab 7", "Operations Halted", "May 28 02:00 UTC"],
    "primary_database_verifications": [
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
      "calculated_omission_index": 0.65,
      "framing_volatility_score": 0.12,
      "identifiable_omissions": [
        "Omitted that the secondary backup generator arrays completely failed to cycle on."
      ],
      "linguistic_camouflage": [
        {
          "raw_expression": "minor power interruption",
          "structural_translation": "Complete physical distribution line severance"
        }
      ]
    }
  ],
  "outlier_signals": [
    {
      "signal_id": "SIG-8041",
      "origin_outlet": "The Tainan Industrial Insider",
      "extracted_claim": "The backup grid system did not fail due to a storm; internal core systems were manually overridden via a compromised service account.",
      "timestamp_first_seen": "2026-05-28T12:10:00Z",
      "outlier_origin_provenance": {
        "classification": "SINGLE_SOURCE_ORIGIN",
        "historical_origin_validation_rate": 0.84,
        "scatter_shot_anomaly_factor": 0.21,
        "echo_chamber_mimics": []
      },
      "validation_tracking": {
        "current_state": "UNVERIFIED_BY_CONSENSUS",
        "last_checked_timestamp": "2026-05-28T12:45:00Z",
        "consensus_absorption_status": "PENDING"
      }
    }
  ]
}
```

## Section 4: Operational Data Processing Flows

### 1. Dual Inception Loop Gateways

- Keyword Target Gateway: Accepts a user-curated parameters array matching high-value assets, firm names, or geographic nodes.

- Global Trend Gateway: Queries the Bright Data SERP API continuously to discover trending macro headlines, creating a cluster manifest automatically.


### 2. JIT Split-Testing Entity Resolution
To accurately evaluate the architectural impact of seeding data connections before graph extraction, Layer 2 forks the text payload into two parallel processing passes:

- Pipeline A (The Unseeded Stream): Feeds raw article text strings directly to cognee.add() and cognee.cognify(). Outlets writing variants like "Fab 7" and "The Tainan Hub" are generated as independent, distinct entities in the database.

- Pipeline B (The JIT Seeded Stream): Routes text segments through a fast LLM pass that maps text string aliases to a single, unified reference identity dictionary before invoking cognee.add().

- Both graphs are retained side-by-side inside the Cognee dataset workspace. This allows the system to compare structural differences and evaluate whether variations in reporting stem from deliberate text positioning or basic naming differences.


### Topological Graph Math Operations

Instead of using subjective text searches to find information discrepancies, Layer 3 uses mathematical set queries inside the database engine:

- Consensus Baseline Graph ($G_c$): Calculated by extracting the intersection of nodes and relational edges that appear in more than 75% of ingestion vectors. This functions as a baseline indicator of shared narrative momentum, explicitly not as absolute historical truth.

- Omission Tracking ($O_{index}$): Computed as the set subtraction of graphs ($G_c - G_{source}$). Missing edges populate the identifiable_omissions telemetry array.

- Outlier Discovery: Extracted by identifying isolated leaf nodes or subgraphs with a single connection that appear exclusively in one media source vector.


## Section 5: Advanced Forensic Metrics Configuration

### 1. Information Omission Index ($O_i$)

Quantifies transparency by dividing missing consensus parameters by total consensus structures:

$$O_i = \frac{\text{Count of Missing Consensus Nodes}}{\text{Total Count of Consensus Baseline Nodes}}$$


### 2. Programmable Framing Volatility via Neutralization Distance ($V_f$)

Linguistic framing volatility is calculated via a two-step adversarial transformation process rather than a static dictionary:

1. Neutralization Pass: Layer 3 routes raw text to an isolated prompt that strips all adjectives, emotional framing, and corporate euphemisms, reducing the passage down to a flat, clinical wire-service summary of actions and entities.

2. Distance Calculation: The engine measures the semantic vector distance and token edit distance between the raw text and the neutralized baseline text. The resulting delta serves as the objective Framing Volatility Score, measuring structural deviation from objective utility.


### 3. Outlier Origin Provenance & Fractional Scatter-Shot Logic

To catch bad actors who pump high volumes of speculative noise to inflate their validation rates, tracking operates on a fractional node basis:

- Origin Sorting: The first platform to present an outlier node based on crawl timestamps receives the True Origin Source metadata tag. Secondary platforms that repeat the node later are designated as Echo-Chamber Mimics and receive zero points.

- Fractional Absorption Vector: Outlets only gain validation points for the exact, individual sub-nodes and edges that successfully merge into the 75%+ consensus graph over time, rather than the entire macro claim manifest.

- The Scatter-Shot Anomaly Factor ($S_a$): Tracked as the ratio of permanently decayed outlier nodes versus successfully absorbed nodes generated by a single source over a rolling timeline:

```
$$S_a = \frac{\text{Count of Permanently Decayed Outlier Nodes}}{\text{Total Outlier Nodes Produced}}$$
```

A high $S_a$ flags an outlet guessing outcomes through high-volume speculation, suppressing their overall validation profile.

- Vertical Stratification: All historical metrics are completely separated by industry sector (e.g., Technology, Macroeconomics, Geopolitics), preventing noise in one vertical from distorting high-quality coverage in another.



## Section 6: Modal & Cloud Environment Configurations

### 1. Production Secrets Configuration (.env.production)

```
MODAL_ENVIRONMENT="production"
TELEMETRY_DISABLED="true"
COGNEE_SYSTEM_ROOT="/root/.cognee_system"

# ENGINE VECTOR EMBEDDING INTERFACES
EMBEDDING_PROVIDER="openai"
EMBEDDING_MODEL="text-embedding-3-small"
EMBEDDING_API_KEY="sk-proj-open-ai-key"

# LAYER 2 REASONING MATRIX (COGNIFY EXTRACTION COST MINIMIZER)
LLM_PROVIDER="openai"
LLM_MODEL="gpt-4o"
LLM_API_KEY="sk-proj-open-ai-key"

# LAYER 3 ADVANCED DECONSTRUCTION INTEL BRAIN
ANALYSIS_PROVIDER="anthropic"
ANALYSIS_MODEL="claude-3-5-sonnet-20241022"
ANALYSIS_API_KEY="sk-ant-anthropic-key"

# WEB SCRAPER ACCESS
BRIGHTDATA_API_KEY="bd_api_key_from_hackathon"
```

### 2. Modal Orchestration Entry Point (app.py)

```
import modal
import os

volume = modal.Volume.from_name("cognee-forensic-storage", create_if_missing=True)

image_recipe = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("cognee", "openai", "anthropic", "pydantic")
)

app = modal.App(name="narrative-alpha-core")

@app.function(
    image=image_recipe,
    volumes={"/root/.cognee_system": volume},
    secrets=[modal.Secret.from_dotenv(".env.production")],
    timeout=600
)
@modal.web_endpoint(method="POST")
async def execute_forensic_pipeline(payload: dict):
    """
    Decoupled Gateway Execution Entry Point.
    Accepts ingestion payload, routes to processing core, 
    saves graph states to storage volume, returns clean JSON response.
    """
    from core_processing import run_cognition_engine
    from analysis_engine import generate_forensic_report
    
    # 1. Processing Layer Execution
    graph_context = await run_cognition_engine(payload)
    
    # 2. Synthesis Layer Execution
    final_report = await generate_forensic_report(graph_context)
    
    # Commit files and graph states to the persistent Modal volume storage disk
    volume.commit()
    
    return final_report
```

## Section 7: System Failure Modes, Edge Cases, & Robust Mitigations

Functional Edge Case / Failure,Operational System Root Cause,Architectural Code Mitigation Strategy
Payload Paywalls / Bot Interception Blockages,"Target news platforms return cookie confirmations, CAPTCHA blocks, or access-denied tracking states.",Mandatory routing restriction: Content extraction is barred from using native cloud container fetch commands. All ingestion passes strictly through the Bright Data Web Unlocker or cloud Scraping Browser proxy layers to strip structural HTML blocks cleanly.
Graph Database Splitting & Duplication Noise,High variation in stylistic naming conventions across articles maps identical real-world entities into duplicate disconnected nodes.,"Execute the JIT Split-Testing System. Before running cognee.add(), pass article text fragments through a fast, structured LLM layer to clean and resolve synonym sets against a unified reference directory, running the unseeded variant in parallel."
Echo-Chamber Amplification & Loops,"Alternative outlets copy and republish identical rumors, causing the system to misidentify the echo-chamber pattern as an emerging multi-source consensus.","Outlier Origin Provenance Evaluation Engine. Build a strict timestamp sorting process that flags the very first outlet to post a claim as the single origin source, categorizing later iterations as Echo-Chamber Mimics with zero reward weight."
Modal Container Memory Limit Crash,"Running dense, iterative loops across multiple large news files within a single thread causes serverless memory allocations to overflow.",Configure a text-chunking step using clean token boundaries before data is loaded into cognee.add(). Ensure that volume.commit() runs at the end of each process block to preserve resources and keep memory use predictable.

## Section 8: Presentation & Delivery Adapters

### 1. Web UI Layout Target (With Reputation Alerts)
The JSON engine returns the Layer 3 schema to your frontend interface, displaying dedicated landing parameters and highlighting structural anomalies:

```
[ OUTLIER FORENSIC INTEL CONSOLE | EVENT ID: EVT-20260528-TECH-SEMI ]
--------------------------------------------------------------------------------
VERTICAL INDUSTRY CLASSIFICATION: TECHNOLOGY
CONSENSUS NARRATIVE BASELINE:
  • Fab 7 microchip production operations halted on May 28 at 02:00 UTC.
  • Verified via: Municipal Energy Regulatory Filing (Ref: REG-POWER-9042) [STATUS: VERIFIED]

[!] REPUTATION WARNING: HIGH SCATTER-SHOT RATIO
This outlet currently holds an 84% validation rate in TECHNOLOGY, but exhibits a 72% Scatter-Shot Anomaly Factor. They break accurate details but wrap them in high volumes of unverified structural noise. Proceed with caution.

MEDIA DISTORTION SUMMARY MATRIX:
┌──────────────────────────────┬──────────────────┬──────────────────┬───────────────────────────────────────────┐
│ OUTLET VECTOR                │ OMISSION INDEX   │ FRAMING VOLATIL. │ DETECTED TEXT CAMOUFLAGE                  │
├──────────────────────────────┼──────────────────┼──────────────────┼───────────────────────────────────────────┐
│ Global Corporate News Wire   │ 0.65 [HIGH]      │ 0.12 [LOW]       │ "minor power interruption"               │
│                              │                  │                  │  -> Complete grid line physical severance │
└──────────────────────────────┴──────────────────┴──────────────────┴───────────────────────────────────────────┘

PREDICTIVE NARRATIVE ALPHA WATCH:
• [FLAGGED SINGLE SOURCE OUTLIER CLAIM]: "The halt was triggered by an internal localized server intrusion, not external grid lines."
• ORIGIN OUTLET PROVENANCE: The Tainan Industrial Insider
• HISTORICAL ORIGIN VALIDATION RATE: 84% accuracy track record on past high-drift claims.
• CURRENT STATE: UNVERIFIED BY MAINSTREAM | ABSORPTION MONITOR ACTIVE [PENDING 30-DAY TIMELINE EVALUATION]
```

### 2. Idempotent Obsidian Storage Protocol
To guarantee that re-processing event clusters due to late-breaking updates or source additions does not cause note duplication or wipe out your personal annotations, Layer 4 updates files via regex-bounded comment blocks and YAML frontmatter merging:


Entry Template A: The Story Profile (Vault/Events/EVT-20260528-TECH-SEMI.md)
```
---
id: EVT-20260528-TECH-SEMI
industry: TECHNOLOGY
consensus_anchor: Fab 7 production operations halted on May 28 at 02:00 UTC.
last_updated: 2026-05-28T13:00:00Z
---
# Forensic Report: Fab 7 Manufacturing Halt

## Personal Notes & Synthesis Notes
(This area is safe. Anything written outside the system comment blocks is completely preserved during pipeline re-runs.)

<!-- BEGIN SYSTEM DISTORTION MATRIX -->
* Tracked Platform: [[The Tainan Industrial Insider]]
  * Omission Index: 0.10
  * Framing Volatility: 0.78
* Tracked Platform: [[Global Corporate News Wire]]
  * Omission Index: 0.65
  * Framing Volatility: 0.12
<!-- END SYSTEM DISTORTION MATRIX -->

## Field Observations
* High narrative volatility on localized reporting channels.

<!-- BEGIN SYSTEM OUTLIER WATCH -->
* **Outlier Signal ID**: SIG-8041
* **Source**: [[The Tainan Industrial Insider]]
* **Claim**: The backup grid system did not fail due to a storm; internal core systems were manually overridden via a compromised service account.
* **Absorption Status**: #pending-consensus-merge
<!-- END SYSTEM OUTLIER WATCH -->
```

The generation script executes an internal regex swap matching (<!-- BEGIN SYSTEM MODULE -->)(.*?)(<!-- END SYSTEM MODULE -->) to cleanly replace dynamic sections inline while leaving manual annotations untouched.

## Section 9: Systemic Analytical Blind Spots & The Consensus Trap

Because this system tracks historical validation by checking when an outlier node is eventually adopted into the mainstream consensus reality graph, accuracy tracking remains structurally dependent on mainstream media acknowledgment.

If a high-drift independent outlet prints a true investigative disclosure that is successfully covered up and never acknowledged by the consensus pool, your system’s graph subtraction math will permanently classify that true event node as an "unverified, decaying outlier anomaly."

Relying on this blueprint means explicitly acknowledging that the platform tracks an outlet's capacity to front-run what the consensus group eventually acknowledges, rather than determining absolute, objective reality.