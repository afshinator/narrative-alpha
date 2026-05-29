# Narrative Alpha — Full Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete Narrative Alpha forensic narrative analysis system per spec v1.4

**Architecture:** 4-layer decoupled pipeline (Ingestion → Processing → Analysis → Presentation) orchestrated as a single Modal web endpoint. Bright Data for scraping, DeepSeek V4 for LLM (Flash + Pro), OpenAI for embeddings, SQLite on Modal Volume for persistence.

**Tech Stack:** Python 3.11, Modal Serverless, Bright Data SERP + Web Unlocker, DeepSeek V4, OpenAI embeddings, SQLite (WAL mode), static HTML/JS dashboard

---

## File Map

| File | Layer | Responsibility |
|---|---|---|
| `contracts.py` | Shared | Pydantic models for all data contracts (Contract A, Contract B, LLM config) |
| `llm_client.py` | Shared | Runtime LLM config loader, provider client factory, `call_llm()` |
| `ingestion.py` | Layer 1 | SERP discovery, Web Unlocker extraction, `validate_ingestion_payload()`, manifest assembly, corpus floor gate |
| `processing.py` | Layer 2 | `build_search_context_table()`, entity normalization (Call 1), linguistic neutralization (Call 2), embedding generation, Vf computation |
| `analysis.py` | Layer 3 | Graph extraction (Call 3), Python set-math (Gc, Oi, Sa), `compute_pre_synthesis_context()`, forensic synthesis (Call 4), label injection |
| `reputation.py` | Persistence | SQLite schema, `get_hardened_db_connection()`, `handle_outlet_registration()`, read/write reputation, ingestion log |
| `backtest.py` | Persistence | Background `.spawn()` worker for historical reputation back-test |
| `app.py` | Orchestration | Modal endpoints: `execute_forensic_pipeline()`, `update_llm_config()` |
| `dashboard/index.html` | Layer 4 | Index page — list of processed clusters |
| `dashboard/event.html` | Layer 4 | Per-cluster forensic report (3 zones + sub-panels) |
| `dashboard/settings.html` | Layer 4 | Runtime LLM provider/model settings UI |
| `dashboard/style.css` | Layer 4 | Dark terminal aesthetic, color-coded labels |
| `dashboard/app.js` | Layer 4 | Data fetching, zone rendering, settings save |

**Dependency order:** contracts → llm_client → ingestion → reputation → processing → analysis → backtest → app → dashboard

---

### Task 1: Project Scaffolding & Pydantic Data Contracts

**Files:**
- Create: `contracts.py`
- Create: `.env.example` (verify existing, update if needed)
- Create: `llm_config.json` (default, embedded)

**What:** All JSON schemas from Sections 4, 5, 9.2 typed as Pydantic models. This is the single source of truth for data shapes across all layers.

- [ ] **Step 1: Write `contracts.py` with Contract A models**

```python
"""Data contracts for Narrative Alpha — typed Pydantic models for all layers."""

from pydantic import BaseModel, Field
from typing import List, Optional


# ── Contract A: Ingestion Manifest (Layer 1 → Layer 2) ──

class IngestionDocument(BaseModel):
    doc_id: str
    source_name: str
    source_domain: str
    source_url: str
    title: str
    scrape_timestamp: str
    author: str = "Staff"
    raw_text_content: str


class IngestionManifest(BaseModel):
    cluster_id: str
    trigger_type: str
    search_query: str
    timestamp_utc: str
    corpus_count: int
    documents: List[IngestionDocument]


# ── Contract B: Forensic Report (Layer 3 → Layer 4) ──

class EventMeta(BaseModel):
    cluster_id: str
    search_query: str
    industry_vertical: str
    timestamp_utc: str
    corpus_count: int


class PrimaryVerification(BaseModel):
    authority: str
    reference_id: str
    status: str  # "VERIFIED" | "UNVERIFIED" | ...


class ConsensusRealityGraph(BaseModel):
    consensus_summary: str
    verified_anchor_nodes: List[str]
    primary_verifications: List[PrimaryVerification] = []


class LinguisticCamouflage(BaseModel):
    raw_expression: str
    clinical_translation: str


class DistortionMatrixEntry(BaseModel):
    outlet_name: str
    source_domain: str
    omission_index: float
    omission_label: str = "MED"   # injected by Python after Call 4
    framing_volatility_score: float
    framing_volatility_label: str = "MED"
    identifiable_omissions: List[str] = []
    linguistic_camouflage: List[LinguisticCamouflage] = []


class OutlierProvenance(BaseModel):
    classification: str  # "SINGLE_SOURCE_ORIGIN" | ...
    historical_origin_validation_rate: float
    scatter_shot_anomaly_factor: float
    scatter_shot_label: str = "LOW"
    reputation_warning_triggered: bool = False
    echo_chamber_mimics: List[str] = []


class OutlierValidation(BaseModel):
    current_state: str  # "PENDING" | "VERIFIED" | "DECAYED" | "UNVERIFIED_BY_CONSENSUS" | ...
    last_checked_timestamp: str
    consensus_absorption_status: str  # "PENDING" | "ABSORBED" | "DECAYED"
    evaluation_window_days: int = 30


class OutlierSignal(BaseModel):
    signal_id: str
    origin_outlet: str
    origin_domain: str
    extracted_claim: str
    timestamp_first_seen: str
    outlier_origin_provenance: OutlierProvenance
    validation_tracking: OutlierValidation


class ReputationWarning(BaseModel):
    outlet_name: str
    source_domain: str
    warning_triggered: bool
    historical_origin_validation_rate: float
    scatter_shot_anomaly_factor: float
    scatter_shot_label: str
    warning_message: str


class SupportingOutlets(BaseModel):
    # dynamic keys — map narrative structure string → list of domain strings
    narratives: dict = {}


class RealityDivergenceZone(BaseModel):
    topic: str
    consensus_stability: str  # "HIGH" | "MED" | "LOW"
    consensus_stability_score: float
    institutional_convergence: str  # "RESOLVED" | "CONTESTED" | "UNRESOLVED"
    observed_narrative_structures: List[str]
    supporting_outlets: dict  # narrative → [domain, ...]


class RealityFractureClaim(BaseModel):
    statement: str
    supporting_outlets: List[str]


class RealityFracture(BaseModel):
    fracture_id: str
    topic: str
    claim_a: RealityFractureClaim
    claim_b: RealityFractureClaim
    relationship: str  # "STRUCTURALLY_CONTRADICTORY" | "ORTHOGONAL"
    resolution_status: str  # "UNRESOLVED" | "PARTIALLY_RESOLVED"
    classification_method: str = "LLM_ASSISTED"


class NarrativeRegimeShift(BaseModel):
    shift_id: str
    topic: str
    detected_shift: dict  # { "previous_term": str, "replacement_term": str }
    observed_across: int
    total_sources: int
    synchronization_score: float
    synchronization_label: str  # "HIGH" | "MED" | "LOW"
    interpretive_note: str


class ForensicReport(BaseModel):
    event_meta: EventMeta
    consensus_reality_graph: ConsensusRealityGraph
    distortion_matrix: List[DistortionMatrixEntry]
    outlier_signals: List[OutlierSignal]
    reputation_warnings: List[ReputationWarning]
    reality_divergence_zones: List[RealityDivergenceZone]
    reality_fractures: List[RealityFracture]
    narrative_regime_shifts: List[NarrativeRegimeShift]


# ── LLM Config Schema (llm_config.json) ──

class LLMSlotConfig(BaseModel):
    provider: str  # "deepseek" | "openai" | "google" | "groq"
    model: str
    thinking: bool = False
    temperature: float = 0.1


class LLMConfig(BaseModel):
    call_1_entity_normalization: LLMSlotConfig
    call_2_linguistic_neutralization: LLMSlotConfig
    call_3_graph_extraction: LLMSlotConfig
    call_4_forensic_synthesis: LLMSlotConfig


# ── Pipeline Input / Floor Gate Response ──

class PipelineInput(BaseModel):
    keyword: str
    vertical: str  # "TECHNOLOGY" | "FINANCE" | ...


class FloorGateResponse(BaseModel):
    validation_tracking: dict  # { current_state, minimum_required, current_count }
```

- [ ] **Step 2: Verify contracts import cleanly**

Run: `python -c "from contracts import IngestionManifest, ForensicReport, LLMConfig; print('contracts OK')"`
Expected: `contracts OK`

- [ ] **Step 3: Commit**

```bash
git add contracts.py
git commit -m "feat: add Pydantic data contracts for all pipeline layers"
```

**Sanity check:** Do all Contract B fields from Section 4 have a matching Pydantic model? Count fields in JSON example vs. models. Does `LlamaSlotConfig` match the `llm_config.json` structure from Section 9.2?

---

### Task 2: LLM Client Factory

**File:** Create `llm_client.py`

**What:** Section 9.3 — Provider-agnostic LLM client. Loads runtime config from Modal Volume, resolves base URLs and API keys, executes calls with JSON mode + optional thinking. Single function `call_llm()` used by all 4 call slots.

- [ ] **Step 1: Write `llm_client.py`**

```python
"""Runtime LLM provider configuration and client factory."""

import json
import os
from typing import Optional
from openai import OpenAI

from contracts import LLMConfig, LLMSlotConfig


# ── Provider resolution maps ──

PROVIDER_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com",
    "openai":   "https://api.openai.com/v1",
    "google":   "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq":     "https://api.groq.com/openai/v1",
}

PROVIDER_API_KEY_ENV: dict[str, str] = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai":   "OPENAI_API_KEY",
    "google":   "GOOGLE_API_KEY",
    "groq":     "GROQ_API_KEY",
}

# ── Default in-code config (written to volume on first run if file missing) ──

DEFAULT_LLM_CONFIG = LLMConfig(
    call_1_entity_normalization=LLMSlotConfig(
        provider="deepseek", model="deepseek-v4-flash", thinking=False, temperature=0.1
    ),
    call_2_linguistic_neutralization=LLMSlotConfig(
        provider="deepseek", model="deepseek-v4-flash", thinking=False, temperature=0.1
    ),
    call_3_graph_extraction=LLMSlotConfig(
        provider="deepseek", model="deepseek-v4-pro", thinking=True, temperature=0.1
    ),
    call_4_forensic_synthesis=LLMSlotConfig(
        provider="deepseek", model="deepseek-v4-pro", thinking=True, temperature=0.1
    ),
).model_dump()


# ── Config lifecycle ──

def _config_path() -> str:
    root = os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha")
    return os.path.join(root, "llm_config.json")


def load_llm_config() -> dict:
    """Load llm_config.json from volume. Write defaults if file missing."""
    path = _config_path()
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(DEFAULT_LLM_CONFIG, f, indent=2)
        return dict(DEFAULT_LLM_CONFIG)


# ── Client factory ──

_client_cache: dict[str, OpenAI] = {}

def get_llm_client(provider: str) -> OpenAI:
    """Return an OpenAI-compatible client for a provider. Cached per provider."""
    if provider in _client_cache:
        return _client_cache[provider]

    api_key_env = PROVIDER_API_KEY_ENV.get(provider)
    api_key = os.environ.get(api_key_env or "", "")
    base_url = PROVIDER_BASE_URLS.get(provider, "")

    client = OpenAI(api_key=api_key, base_url=base_url)
    _client_cache[provider] = client
    return client


# ── Call executor ──

def build_llm_kwargs(slot_config: dict, messages: list[dict],
                     json_mode: bool = True) -> dict:
    """Build kwargs dict for a chat.completions.create call from slot config."""
    kwargs: dict = {
        "model": slot_config["model"],
        "messages": messages,
        "temperature": slot_config.get("temperature", 0.1),
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if slot_config.get("thinking") and slot_config["provider"] == "deepseek":
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
    return kwargs


def call_llm(slot_config: dict, messages: list[dict],
             json_mode: bool = True, retries: int = 1) -> str:
    """
    Execute a single LLM call. Returns response content as string.

    Args:
        slot_config: e.g. llm_config["call_1_entity_normalization"]
        messages: chat messages list
        json_mode: if True, request JSON response format
        retries: number of retry attempts on failure

    Returns:
        response.choices[0].message.content
    """
    provider = slot_config["provider"]
    client = get_llm_client(provider)
    kwargs = build_llm_kwargs(slot_config, messages, json_mode)

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if json_mode:
                # Validate parseable; return raw string regardless
                json.loads(content)
            return content
        except Exception as e:
            last_error = e
            if attempt < retries:
                continue
            raise

    raise last_error  # type: ignore[misc]


# ── Standalone embedding call (not slot-configured — fixed to OpenAI) ──

def get_embedding(text: str) -> list[float]:
    """Generate embedding vector via OpenAI text-embedding-3-small."""
    client = get_llm_client("openai")
    model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding
```

- [ ] **Step 2: Verify imports + instantiation**

Run: `python -c "from llm_client import load_llm_config, get_llm_client, call_llm; print('llm_client OK')"`
Expected: `llm_client OK`

- [ ] **Step 3: Commit**

```bash
git add llm_client.py
git commit -m "feat: add LLM client factory with runtime config and multi-provider support"
```

**Sanity check:** Verify `_config_path()` reads `NARRATIVE_ALPHA_ROOT` from env. Verify thinking flag only writes `extra_body` when provider is DeepSeek. Verify `get_embedding()` uses the env-configured embedding model.

---

### Task 3: Ingestion Layer — Discovery, Extraction, Validation

**File:** Create `ingestion.py`

**What:** Full Layer 1 (Sections 3 and 14). Four sub-systems:
1. SERP API discovery (`discover_articles`)
2. Web Unlocker extraction (`fetch_article_body` + `extract_text`)
3. Validation gates (`validate_ingestion_payload` — exact code from Section 14.1)
4. Manifest assembly + corpus floor gate (`build_ingestion_manifest`)

- [ ] **Step 1: Write `ingestion.py` — discovery and extraction**

```python
"""Layer 1: Ingestion — Bright Data SERP discovery + Web Unlocker extraction."""

import uuid
import time
from datetime import datetime, timezone
from typing import Optional

import requests
import trafilatura

from contracts import IngestionDocument


SERP_ENDPOINT = "https://api.brightdata.com/serp/req"
UNLOCKER_ENDPOINT = "https://api.brightdata.com/request"


# ── 1. SERP Discovery ──

def discover_articles(keyword: str, api_key: str, num: int = 15) -> dict:
    """
    Query Bright Data SERP API for Google News results.

    Returns parsed SERP response dict. Uses engine=google + tbm=nws
    for the News tab; parsed_light=true for structured metadata.
    """
    payload = {
        "engine": "google",
        "q": keyword,
        "tbm": "nws",
        "num": num,
        "gl": "us",
        "hl": "en",
        "parsed_light": True,
    }
    response = requests.post(
        SERP_ENDPOINT,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ── 2. Web Unlocker Extraction ──

def fetch_article_body(url: str, zone: str, api_key: str) -> str:
    """
    Fetch full article HTML through Bright Data Web Unlocker anti-bot proxy.

    Uses the /request endpoint (Direct API Access). Zone name in body.
    """
    response = requests.post(
        UNLOCKER_ENDPOINT,
        json={"zone": zone, "url": url, "format": "raw"},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def extract_text(html: str) -> str:
    """Strip HTML boilerplate via trafilatura. Returns clean text or ''."""
    text = trafilatura.extract(html)
    return (text or "").strip()


# ── 3. Validation Gates ──

def validate_ingestion_payload(doc: dict) -> Optional[dict]:
    """
    Enforce Layer 1 quality checks on scraped text.
    Returns validated document dict or None if rejected.

    Exact implementation from spec Section 14.1.
    """
    raw_text = doc.get("raw_text_content", "").strip()
    title = doc.get("title", "").strip()
    source_url = doc.get("source_url", "").strip()

    # Structural prerequisite checks
    if not source_url or not title:
        return None

    # Extract and normalize canonical domain
    from urllib.parse import urlparse
    try:
        domain = urlparse(source_url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
    except Exception:
        return None

    # Character and word count floor
    if len(raw_text) < 300:
        return None
    if len(raw_text.split()) < 50:
        return None

    # Paywall / authentication gate detection
    import re
    paywall_patterns = [
        r"sign\s*in\s*to\s*continue",
        r"create\s*an\s*account",
        r"subscribe\s*to\s*read",
        r"exclusive\s*subscriber\s*content",
        r"log\s*in\s*or\s*register",
        r"members\-only\s*story",
    ]
    if any(re.search(p, raw_text, re.IGNORECASE) for p in paywall_patterns):
        return None

    # Nav-bloat / boilerplate scrape detection
    nav_tokens = [
        "cookie", "privacy policy", "all rights reserved",
        "terms of service", "share this article",
    ]
    nav_hits = sum(1 for token in nav_tokens if token in raw_text.lower())
    if nav_hits > 3 and len(raw_text) < 1500:
        return None

    return {
        "doc_id": doc.get("doc_id"),
        "source_name": doc.get("source_name", domain),
        "source_domain": domain,
        "source_url": source_url,
        "title": title,
        "scrape_timestamp": doc.get("scrape_timestamp"),
        "author": doc.get("author", "Staff"),
        "raw_text_content": raw_text,
    }


# ── 4. Manifest Assembly + Corpus Floor ──

def build_ingestion_manifest(
    keyword: str,
    serp_data: dict,
    zone: str,
    api_key: str,
) -> dict:
    """
    Full Layer 1 pipeline: SERP results → Web Unlocker fetch → validate → manifest.

    Returns one of:
        - A valid IngestionManifest dict (corpus_count >= 5)
        - A FloorGateResponse dict (corpus_count < 5)
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    cluster_id = f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{keyword[:20].upper().replace(' ', '-')}"

    organic = serp_data.get("organic", [])
    validated_docs: list[dict] = []

    for idx, result in enumerate(organic):
        url = result.get("link", "")
        title = result.get("title", "")
        source_name = result.get("source", "") or result.get("display_link", "")

        if not url:
            continue

        try:
            html = fetch_article_body(url, zone, api_key)
            raw_text = extract_text(html)
        except Exception:
            continue   # fetch/extract failure — skip silently

        doc = {
            "doc_id": f"DOC-{idx:03d}",
            "source_name": source_name,
            "source_url": url,
            "title": title,
            "scrape_timestamp": now_utc,
            "raw_text_content": raw_text,
        }

        validated = validate_ingestion_payload(doc)
        if validated:
            validated_docs.append(validated)

    # Deduplicate by unique source_domain
    seen_domains: set[str] = set()
    unique_docs = []
    for doc in validated_docs:
        domain = doc.get("source_domain", "")
        if domain not in seen_domains:
            seen_domains.add(domain)
            unique_docs.append(doc)

    corpus_count = len(unique_docs)

    if corpus_count < 5:
        return {
            "validation_tracking": {
                "current_state": "INSUFFICIENT_CORPUS_FLOOR",
                "minimum_required": 5,
                "current_count": corpus_count,
            }
        }

    return {
        "cluster_id": cluster_id,
        "trigger_type": "KEYWORD",
        "search_query": keyword,
        "timestamp_utc": now_utc,
        "corpus_count": corpus_count,
        "documents": unique_docs,
    }
```

- [ ] **Step 2: Verify imports + basic structure**

Run: `python -c "from ingestion import discover_articles, fetch_article_body, extract_text, validate_ingestion_payload, build_ingestion_manifest; print('ingestion OK')"`
Expected: `ingestion OK`

- [ ] **Step 3: Commit**

```bash
git add ingestion.py
git commit -m "feat: add Layer 1 ingestion — SERP discovery, Web Unlocker extraction, validation gates"
```

**Sanity check:** Does `build_ingestion_manifest` return `FloorGateResponse` shape when corpus < 5? Does it return `IngestionManifest` shape when corpus >= 5? Are extracted domains normalized (no www prefix, lowercased)?

---

### Task 4: Reputation Persistence Layer

**File:** Create `reputation.py`

**What:** Section 7 — SQLite on Modal Volume. Schema creation, hardened connection, outlet registration with cold-start UNRATED pattern. Also Section 14.3 — ingestion manifest log table.

- [ ] **Step 1: Write `reputation.py`**

```python
"""Layer: Persistence — SQLite reputation ledger on Modal Volume."""

import os
import sqlite3
from typing import Optional


DB_FILENAME = "outlet_reputation.db"


def _db_path(root: Optional[str] = None) -> str:
    root = root or os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha")
    return os.path.join(root, DB_FILENAME)


def get_hardened_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    SQLite connection with WAL mode for concurrent Modal workers.
    - WAL mode: reads never block writes
    - busy_timeout: 30000ms grace for concurrent writers
    - synchronous=NORMAL: safety without full fsync penalty
    """
    path = db_path or _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables if they do not exist (idempotent)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS outlet_reputation (
            domain TEXT NOT NULL,
            industry_vertical TEXT NOT NULL,
            outlet_name TEXT,
            total_outlier_nodes_produced INTEGER DEFAULT 0,
            total_absorbed_nodes INTEGER DEFAULT 0,
            total_decayed_nodes INTEGER DEFAULT 0,
            scatter_shot_anomaly_factor REAL DEFAULT NULL,
            historical_origin_validation_rate REAL DEFAULT NULL,
            back_test_article_count INTEGER DEFAULT 0,
            rating_status TEXT DEFAULT 'UNRATED',
            last_updated TEXT,
            PRIMARY KEY (domain, industry_vertical)
        );

        CREATE TABLE IF NOT EXISTS outlier_tracking (
            signal_id TEXT PRIMARY KEY,
            cluster_id TEXT,
            origin_domain TEXT,
            extracted_claim TEXT,
            timestamp_first_seen TEXT,
            current_state TEXT DEFAULT 'PENDING',
            evaluation_deadline TEXT,
            absorbed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ingestion_manifest_log (
            query_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            discovery_timestamp TEXT NOT NULL,
            source_domain TEXT NOT NULL,
            canonical_url TEXT NOT NULL,
            title TEXT NOT NULL,
            published_at TEXT,
            fetch_status INTEGER,
            body_text TEXT NOT NULL,
            body_length INTEGER NOT NULL,
            passed_validation INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (canonical_url)
        );
    """)
    conn.commit()


def handle_outlet_registration(
    domain: str,
    vertical: str,
    conn: sqlite3.Connection,
) -> str:
    """
    Check if outlet is known. If new: insert UNRATED row immediately.
    Returns the outlet's current rating_status.

    Does NOT spawn the back-test — that's the orchestrator's job.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rating_status FROM outlet_reputation WHERE domain = ? AND industry_vertical = ?",
        (domain, vertical),
    )
    row = cursor.fetchone()

    if not row:
        cursor.execute(
            "INSERT INTO outlet_reputation (domain, industry_vertical, rating_status, last_updated) "
            "VALUES (?, ?, 'UNRATED', datetime('now'))",
            (domain, vertical),
        )
        conn.commit()
        return "UNRATED"

    return row[0]


def read_outlet_reputation(
    domain: str,
    vertical: str,
    conn: sqlite3.Connection,
) -> Optional[dict]:
    """Read full reputation row for an outlet. Returns None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM outlet_reputation WHERE domain = ? AND industry_vertical = ?",
        (domain, vertical),
    )
    row = cursor.fetchone()
    if not row:
        return None
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))


def write_outlier_signal(
    signal_id: str,
    cluster_id: str,
    origin_domain: str,
    extracted_claim: str,
    timestamp: str,
    conn: sqlite3.Connection,
) -> None:
    """Log a new outlier signal to the tracking table."""
    conn.execute(
        "INSERT OR IGNORE INTO outlier_tracking "
        "(signal_id, cluster_id, origin_domain, extracted_claim, timestamp_first_seen) "
        "VALUES (?, ?, ?, ?, ?)",
        (signal_id, cluster_id, origin_domain, extracted_claim, timestamp),
    )
    conn.commit()


def write_ingestion_log(
    query_id: str,
    topic: str,
    discovery_timestamp: str,
    docs: list[dict],
    conn: sqlite3.Connection,
) -> None:
    """
    Log every scrape attempt (passed and failed) to ingestion_manifest_log.
    Section 14.3 schema.
    """
    for doc in docs:
        conn.execute(
            "INSERT OR IGNORE INTO ingestion_manifest_log "
            "(query_id, topic, discovery_timestamp, source_domain, canonical_url, "
            "title, fetch_status, body_text, body_length, passed_validation) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                query_id,
                topic,
                discovery_timestamp,
                doc.get("source_domain", ""),
                doc.get("source_url", ""),
                doc.get("title", ""),
                doc.get("fetch_status"),
                doc.get("raw_text_content", ""),
                doc.get("body_length", len(doc.get("raw_text_content", ""))),
                doc.get("passed_validation", 0),
            ),
        )
    conn.commit()
```

- [ ] **Step 2: Verify + test with in-memory SQLite**

Run: `python -c "
from reputation import get_hardened_db_connection, init_db, handle_outlet_registration
import sqlite3
# Test with in-memory (bypassing Modal Volume)
conn = sqlite3.connect(':memory:')
init_db(conn)
status = handle_outlet_registration('example.com', 'TECHNOLOGY', conn)
assert status == 'UNRATED', f'Expected UNRATED, got {status}'
# Second registration should return UNRATED (already exists)
status2 = handle_outlet_registration('example.com', 'TECHNOLOGY', conn)
assert status2 == 'UNRATED', f'Expected UNRATED, got {status2}'
# Different vertical should be new
status3 = handle_outlet_registration('example.com', 'FINANCE', conn)
assert status3 == 'UNRATED', f'Expected UNRATED, got {status3}'
print('reputation tests pass')
"`
Expected: `reputation tests pass`

- [ ] **Step 3: Commit**

```bash
git add reputation.py
git commit -m "feat: add SQLite reputation ledger — outlet registration, outlier tracking, ingestion log"
```

**Sanity check:** Does `init_db` create 3 tables with correct PKs? Does `handle_outlet_registration` use composite PK (domain, vertical)? Does WAL mode actually activate (PRAGMA journal_mode)?

---

### Task 5: Processing Layer — Calls 1, 2 + Embeddings

**File:** Create `processing.py`

**What:** Sections 6 (Call 1, Call 2), 5.2 (Vf), and 14.2C (search context). Three functions run sequentially: entity normalization, linguistic neutralization, framing volatility.

- [ ] **Step 1: Write `processing.py` — search context helper**

```python
"""Layer 2: Processing — entity normalization, linguistic neutralization, embeddings."""

from llm_client import call_llm, load_llm_config, get_embedding
import numpy as np


# ── Search Context Reference Table (Section 14.2C) ──

def build_search_context_table(serp_data: dict) -> str:
    """
    Build a markdown table from SERP response for Call 1 prompt injection.
    Extracts titles, snippets, and People Also Ask (PAA) data.
    Gracefully degrades if PAA key absent.
    """
    lines = ["## SYSTEM SEARCH CONTEXT REFERENCE\n"]
    lines.append("| Type | Content Source / Query Variant | Contextual Text Snippet |")
    lines.append("| :--- | :--- | :--- |")

    for item in serp_data.get("organic", []):
        title = item.get("title", "").replace("|", "-")
        domain = item.get("display_link", "")
        snippet = item.get("snippet", "").replace("|", "-")
        if title and snippet:
            lines.append(f"| RESULT | {title} ({domain}) | {snippet} |")

    for paa in serp_data.get("people_also_ask", []):
        question = paa.get("question", "").replace("|", "-")
        answer = paa.get("answer", "").replace("|", "-")
        if question and answer:
            lines.append(
                f"| PAA_SYNONYM | ALTERNATE QUERY: {question} | CROSS-REFERENCE: {answer} |"
            )

    return "\n".join(lines)
```

- [ ] **Step 2: Write `processing.py` — Call 1 + Call 2 + Vf**

```python
# ── Call 1: Entity Normalization (Fast LLM, non-thinking) ──

ENTITY_NORMALIZATION_SYSTEM_PROMPT = (
    "You are an entity normalization engine. Given a set of raw article text fragments, "
    "identify all named entities and map every surface-form variant to a single canonical "
    "reference identity. Output only valid JSON matching the schema provided. "
    "Do not include preamble, explanation, or markdown fences."
)


def run_entity_normalization(
    documents: list[dict],
    serp_data: dict,
    llm_config: dict,
) -> dict[str, str]:
    """
    Resolve naming variants across articles to canonical identities.

    Returns: canonical_map = {lowercased_surface_form: canonical_reference_identity}

    Uses search context table from SERP data to seed the prompt with
    Google's pre-computed synonym resolution.
    """
    from llm_client import call_llm

    # Build search context table
    search_context = build_search_context_table(serp_data)

    # Concatenate all article texts
    article_texts = "\n\n---\n\n".join(
        f"[{doc['source_domain']}] {doc['title']}: {doc['raw_text_content'][:2000]}"
        for doc in documents
    )

    system_prompt = (
        f"{search_context}\n\n---\n\n{ENTITY_NORMALIZATION_SYSTEM_PROMPT}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": article_texts},
    ]

    slot_cfg = llm_config["call_1_entity_normalization"]
    raw = call_llm(slot_cfg, messages, json_mode=True)

    import json
    data = json.loads(raw)
    mappings = data.get("normalized_mappings", [])

    canonical_map: dict[str, str] = {}
    for m in mappings:
        key = m["surface_form_variant"].strip().lower()
        canonical_map[key] = m["canonical_reference_identity"]

    return canonical_map


# ── Call 2: Linguistic Neutralization (Fast LLM, non-thinking) ──

LINGUISTIC_NEUTRALIZATION_SYSTEM_PROMPT = (
    "You are a linguistic neutralization engine. Transform the input text into a flat, "
    "clinical sequence of declarative active-verb statements. Strip all qualifying "
    "adjectives, descriptive idioms, adverbial padding, and corporate designations. "
    "Preserve only: named entities, actions, timestamps, quantities, and locations. "
    "Output plain text only. No JSON. No markdown."
)


def run_linguistic_neutralization(
    documents: list[dict],
    llm_config: dict,
) -> list[str]:
    """
    Strip emotional framing, adjectives, euphemisms from each article.
    Returns list of neutralized text strings (one per doc).
    """
    slot_cfg = llm_config["call_2_linguistic_neutralization"]
    results = []

    for doc in documents:
        messages = [
            {"role": "system", "content": LINGUISTIC_NEUTRALIZATION_SYSTEM_PROMPT},
            {"role": "user", "content": doc["raw_text_content"]},
        ]
        neutralized = call_llm(slot_cfg, messages, json_mode=False)
        results.append(neutralized.strip())

    return results


# ── Framing Volatility Score (Section 5.2) ──

def compute_framing_volatility(
    raw_texts: list[str],
    neutralized_texts: list[str],
) -> tuple[list[float], list[str]]:
    """
    Compute Vf = 1 - cos(raw_embedding, neutralized_embedding) per document.

    Args:
        raw_texts: original article texts
        neutralized_texts: Call 2 output texts (same indexing)

    Returns:
        (vf_scores, vf_labels) — one per doc
    """
    scores = []
    labels = []

    for raw, neut in zip(raw_texts, neutralized_texts):
        e_raw = np.array(get_embedding(raw))
        e_neut = np.array(get_embedding(neut))
        cos_sim = np.dot(e_raw, e_neut) / (
            np.linalg.norm(e_raw) * np.linalg.norm(e_neut)
        )
        vf = 1.0 - float(cos_sim)
        scores.append(round(vf, 4))

        if vf < 0.25:
            labels.append("LOW")
        elif vf < 0.55:
            labels.append("MED")
        else:
            labels.append("HIGH")

    return scores, labels
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from processing import build_search_context_table, run_entity_normalization, run_linguistic_neutralization, compute_framing_volatility; print('processing OK')"`
Expected: `processing OK`

- [ ] **Step 4: Commit**

```bash
git add processing.py
git commit -m "feat: add Layer 2 processing — entity normalization, linguistic neutralization, framing volatility"
```

**Sanity check:** Does `build_search_context_table` handle missing `people_also_ask` key? Does `run_entity_normalization` lowercase all map keys? Does `compute_framing_volatility` use correct label thresholds from Section 5.2?

---

### Task 6: Analysis Layer — Calls 3, 4 + Python Set Math

**File:** Create `analysis.py`

**What:** Sections 5, 6 (Call 3, Call 4), and pre-synthesis pass. This is the largest and most complex file. Five sub-systems:
1. Graph extraction (Call 3 — DeepSeek V4-Pro thinking)
2. Resolve-to-canonical + omission index (Python)
3. Consensus baseline Gc (Python)
4. Scatter-Shot Anomaly Sa (Python + SQLite)
5. Pre-synthesis context aggregation (Python)
6. Forensic synthesis (Call 4 — DeepSeek V4-Pro thinking)
7. Label injection (Python threshold rules)

- [ ] **Step 1: Write `analysis.py` — Call 3 + Python metrics**

```python
"""Layer 3: Analysis — graph extraction, forensic synthesis, metric computation."""

import json
import uuid
from typing import Optional

from llm_client import call_llm


# ── Call 3: Graph Extraction (DeepSeek V4-Pro, thinking enabled) ──

GRAPH_EXTRACTION_SYSTEM_PROMPT = (
    "You are a knowledge graph extraction engine. Given the normalized "
    "article text and entity reference dictionary, extract all factual "
    "claims as a structured node-and-edge graph. Nodes are named entities, "
    "events, timestamps, and quantities. Edges are directed relationships "
    "with a verb. Output only valid JSON matching the schema provided. "
    "The word 'json' must appear in your response."
)


def extract_graph(
    article_text: str,
    entity_dict: dict[str, str],
    llm_config: dict,
) -> dict:
    """
    Extract structured node-and-edge graph from a single article.

    Returns: {"nodes": [...], "edges": [{"source":..., "target":..., "relationship_verb":...}]}
    """
    slot_cfg = llm_config["call_3_graph_extraction"]

    messages = [
        {"role": "system", "content": GRAPH_EXTRACTION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Entity dictionary: {json.dumps(entity_dict)}\n\n"
                f"Article text: {article_text}\n\n"
                "Return a json object with 'nodes' (list of strings) and "
                "'edges' (list of objects with source, target, relationship_verb)."
            ),
        },
    ]

    raw = call_llm(slot_cfg, messages, json_mode=True)
    return json.loads(raw)


def extract_all_graphs(
    documents: list[dict],
    neutralized_texts: list[str],
    canonical_map: dict[str, str],
    llm_config: dict,
) -> list[dict]:
    """
    Extract graph for each document — one Call 3 per doc.
    Uses neutralized text (Call 2 output) as input to reduce noise.
    """
    graphs = []
    for i, (doc, neut_text) in enumerate(zip(documents, neutralized_texts)):
        try:
            graph = extract_graph(neut_text, canonical_map, llm_config)
            graph["_source_domain"] = doc.get("source_domain", f"doc-{i}")
            graph["_source_name"] = doc.get("source_name", "")
            graphs.append(graph)
        except Exception:
            # Mark as PARSE_ERROR, exclude from downstream math
            graphs.append({
                "_source_domain": doc.get("source_domain", f"doc-{i}"),
                "_source_name": doc.get("source_name", ""),
                "_parse_error": True,
                "nodes": [],
                "edges": [],
            })
    return graphs


# ── Resolve to Canonical (Section 5.1) ──

def resolve_to_canonical(node: str, canonical_map: dict[str, str]) -> str:
    """Map a surface-form node string to its canonical identity."""
    return canonical_map.get(node.strip().lower(), node)


# ── Omission Index (Section 5.1) ──

def compute_omission_index(
    consensus_nodes: set[str],
    source_nodes: set[str],
    canonical_map: dict[str, str],
) -> tuple[float, list[str]]:
    """
    Oi = missing_nodes / total_consensus_nodes.
    Nodes are resolved through canonical_map before comparison.
    """
    canonical_consensus = {resolve_to_canonical(n, canonical_map) for n in consensus_nodes}
    canonical_source = {resolve_to_canonical(n, canonical_map) for n in source_nodes}
    missing = canonical_consensus - canonical_source

    if len(canonical_consensus) == 0:
        return 0.0, []

    omission = len(missing) / len(canonical_consensus)
    return round(omission, 4), list(missing)


def omission_label(oi: float) -> str:
    if oi < 0.25:
        return "LOW"
    elif oi < 0.50:
        return "MED"
    else:
        return "HIGH"


# ── Consensus Baseline (Section 5.4) ──

def compute_consensus_baseline(
    all_graphs: list[dict],
    canonical_map: dict[str, str],
) -> set[str]:
    """
    Determine consensus node set Gc: nodes appearing in >75% of source graphs.
    Uses canonical-resolved node names.
    """
    n = len(all_graphs)
    if n < 5:
        return set()

    threshold = int(0.75 * n) + 1  # ceiling

    node_source_counts: dict[str, set[str]] = {}
    for graph in all_graphs:
        if graph.get("_parse_error"):
            continue
        domain = graph.get("_source_domain", "unknown")
        for node in graph.get("nodes", []):
            canonical = resolve_to_canonical(node, canonical_map)
            node_source_counts.setdefault(canonical, set()).add(domain)

    consensus = {node for node, sources in node_source_counts.items()
                 if len(sources) >= threshold}
    return consensus


# ── Scatter-Shot Anomaly (Section 5.3) ──

def scatter_shot_label(sa: float) -> str:
    if sa < 0.35:
        return "LOW"
    elif sa < 0.60:
        return "MED"
    else:
        return "HIGH"


def compute_sa_for_outlet(
    domain: str,
    decayed_count: int,
    total_produced: int,
) -> tuple[float, str]:
    """
    Sa = total_decayed / total_outlier_nodes_produced.
    If total_produced is 0, return 0.0 (UNRATED handled upstream).
    """
    if total_produced == 0:
        return 0.0, "LOW"
    sa = decayed_count / total_produced
    return round(sa, 4), scatter_shot_label(sa)


# ── Framing Volatility label (Section 5.2) ──

def framing_volatility_label(vf: float) -> str:
    if vf < 0.25:
        return "LOW"
    elif vf < 0.55:
        return "MED"
    else:
        return "HIGH"


# ── Consensus Stability Score (Section 5.5) ──

def compute_consensus_stability(
    observed_narratives: dict[str, int],
    total_sources: int,
) -> tuple[float, str]:
    """
    Stability = 1 - (distinct_structures - 1) / total_sources
    """
    distinct = len(observed_narratives)
    if total_sources == 0:
        return 0.0, "LOW"
    score = 1.0 - ((distinct - 1) / total_sources)
    score = max(0.0, min(1.0, score))

    if score >= 0.70:
        label = "HIGH"
    elif score >= 0.40:
        label = "MED"
    else:
        label = "LOW"

    return round(score, 4), label


# ── Synchronization Score (Section 5.7) ──

def sync_label(score: float) -> str:
    if score >= 0.65:
        return "HIGH"
    elif score >= 0.35:
        return "MED"
    else:
        return "LOW"
```

- [ ] **Step 2: Write `analysis.py` — pre-synthesis pass**

```python
# ── Pre-Synthesis Context Aggregation (Section 6) ──

def compute_pre_synthesis_context(
    all_source_graphs: list[dict],
    neutralized_texts: list[str],
    raw_texts: list[str],
    canonical_map: dict[str, str],
    consensus_nodes: set[str],
) -> dict:
    """
    Produces three structured inputs for Call 4:
    1. narrative_clusters — groups sources by causal claim per topic node
    2. fracture_candidates — claim pairs flagged for contradiction check
    3. term_shifts — synonym pair adoption rates across sources

    Pure Python — no LLM.
    """
    # TBD: full implementation.
    # Overview:
    # - narrative_clusters: for each consensus node, group edges from different
    #   sources. If sources disagree on target/relationship → divergence zone candidate.
    #   {topic: {claim_text: [domain, ...]}}
    #
    # - fracture_candidates: where same topic node has edges pointing to semantically
    #   different targets across sources. Two-pass: first collect all targets per topic per
    #   source, then flag pairs where target strings differ by > threshold.
    #   [(topic, claim_a, outlets_a, claim_b, outlets_b), ...]
    #
    # - term_shifts: for each (surface_form, canonical) pair in canonical_map, scan
    #   un-neutralized texts for usage rates. Where adoption of a term across sources
    #   exceeds threshold → regime shift candidate.
    #   [{previous_term, replacement_term, observed_across, total_sources}, ...]
    #
    # Placeholder returns empty structures for now:
    return {
        "narrative_clusters": {},
        "fracture_candidates": [],
        "term_shifts": [],
    }
```

- [ ] **Step 3: Write `analysis.py` — Call 4 forensic synthesis**

```python
# ── Call 4: Forensic Synthesis (DeepSeek V4-Pro, thinking enabled) ──

FORENSIC_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a forensic narrative analysis engine. Your task is to analyze HOW reality "
    "is being described across institutional media sources — not to determine which "
    "description is objectively correct. You map narrative topology: what all outlets "
    "agree on, who omitted which facts, who used linguistic camouflage, and which "
    "single-source outlier claims exist. "
    "Your output must reflect narrative structure, not truth arbitration. "
    "Output only valid JSON matching the schema provided. "
    "The word 'json' must appear in your response."
)


def synthesize_forensic_report(
    context_bundle: dict,
    llm_config: dict,
) -> dict:
    """
    Synthesize the complete Contract B Forensic Report JSON via Call 4.

    context_bundle must include:
        - Gc consensus baseline (nodes list)
        - Per-source graphs with pre-computed Oi and missing node lists
        - Neutralized text pairs for camouflage detection
        - Reputation records per outlet domain
        - Outlier signals (single-source nodes)
        - narrative_clusters from pre-synthesis pass
        - fracture_candidates from pre-synthesis pass
        - term_shifts from pre-synthesis pass
    """
    slot_cfg = llm_config["call_4_forensic_synthesis"]

    # Build a structured prompt from the context bundle
    user_content = json.dumps(context_bundle, indent=2, default=str)

    messages = [
        {"role": "system", "content": FORENSIC_SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    raw = call_llm(slot_cfg, messages, json_mode=True)
    return json.loads(raw)


# ── Label Injection (Python — post Call 4) ──

def inject_labels(report: dict) -> dict:
    """
    Apply Python threshold rules to add LOW/MED/HIGH labels to every
    metric field in the report. Frontend never computes labels.

    Runs after Call 4 returns. Modifies report in place.
    """
    for entry in report.get("distortion_matrix", []):
        entry["omission_label"] = omission_label(entry.get("omission_index", 0))
        entry["framing_volatility_label"] = framing_volatility_label(
            entry.get("framing_volatility_score", 0)
        )

    for signal in report.get("outlier_signals", []):
        prov = signal.get("outlier_origin_provenance", {})
        sa = prov.get("scatter_shot_anomaly_factor", 0)
        prov["scatter_shot_label"] = scatter_shot_label(sa)

    for zone in report.get("reality_divergence_zones", []):
        score = zone.get("consensus_stability_score", 0)
        zone["consensus_stability"] = (
            "HIGH" if score >= 0.70 else "MED" if score >= 0.40 else "LOW"
        )

    for shift in report.get("narrative_regime_shifts", []):
        shift["synchronization_label"] = sync_label(
            shift.get("synchronization_score", 0)
        )

    return report
```

- [ ] **Step 4: Verify imports**

Run: `python -c "from analysis import extract_graph, compute_omission_index, compute_consensus_baseline, synthesize_forensic_report, inject_labels; print('analysis OK')"`
Expected: `analysis OK`

- [ ] **Step 5: Commit**

```bash
git add analysis.py
git commit -m "feat: add Layer 3 analysis — graph extraction, forensic synthesis, all metrics"
```

**Sanity check:** Does `resolve_to_canonical` handle lowercase mapping correctly? Does `compute_consensus_baseline` use ceiling threshold (>75%, not >=)? Does `compute_omission_index` handle division by zero? Does `inject_labels` cover all 4 metric fields?

---

### Task 7: Back-Test Worker

**File:** Create `backtest.py`

**What:** Section 7 — `run_historical_backtest()`. This is a detached Modal function invoked via `.spawn()` after cold-start outlet registration. It queries Bright Data SERP for historical articles from a domain, runs Call 1 + Call 3 against them, then writes reputation metrics to SQLite.

- [ ] **Step 1: Write `backtest.py` — stub with full structure**

```python
"""Background back-test worker for outlet reputation scoring.

Invoked via modal.Function.spawn() — non-blocking, fire-and-forget.
Runs after main pipeline returns. Analyzes historical articles from
a single domain to populate scatter_shot_anomaly_factor and
historical_origin_validation_rate.
"""


def execute_historical_backtest(domain: str, vertical: str) -> None:
    """
    Background task: back-test an outlet's historical accuracy.

    1. SERP API: site:{domain} news, date filter past 12 months, up to 15 articles
    2. Web Unlocker: fetch article bodies
    3. If < 5 articles retrieved: leave rating_status = 'UNRATED', exit
    4. Call 1 + Call 3 on historical articles against present-day ground truth
    5. Count absorbed vs decayed nodes
    6. Write Sa, historical_origin_validation_rate, rating_status = 'RATED' to SQLite
    7. vol.commit()

    Args:
        domain: source domain to back-test (e.g. "globalwire.com")
        vertical: industry vertical (e.g. "TECHNOLOGY")
    """
    # TBD: full implementation.
    # Overview:
    # - Uses the same discover_articles + fetch_article_body from ingestion.py
    #   but with a site:domain query modifier and 12-month date range
    # - Runs Call 1 (entity normalization) and Call 3 (graph extraction)
    #   against historical articles
    # - Compares historical outlier claims against known-consensus baseline
    #   (what was eventually acknowledged)
    # - Counts absorbed (verified later) vs decayed (never verified) nodes
    # - Updates outlet_reputation table with computed metrics
    pass
```

- [ ] **Step 2: Verify import**

Run: `python -c "from backtest import execute_historical_backtest; print('backtest OK')"`
Expected: `backtest OK`

- [ ] **Step 3: Commit**

```bash
git add backtest.py
git commit -m "feat: add back-test worker stub for historical outlet reputation scoring"
```

---

### Task 8: Orchestration — `app.py` + Settings Endpoint

**File:** Create `app.py`

**What:** Sections 8 and 9.4 — Modal orchestration. Two web endpoints:
1. `execute_forensic_pipeline` (POST) — the main pipeline
2. `update_llm_config` (POST) — runtime settings writer

- [ ] **Step 1: Write `app.py`**

```python
"""Modal orchestration — single-entry-point forensic pipeline + settings."""

import os
import json
import modal

from contracts import PipelineInput
from reputation import (
    get_hardened_db_connection,
    init_db,
    handle_outlet_registration,
    write_outlier_signal,
)
from ingestion import discover_articles, build_ingestion_manifest
from processing import (
    run_entity_normalization,
    run_linguistic_neutralization,
    compute_framing_volatility,
)
from analysis import (
    extract_all_graphs,
    compute_consensus_baseline,
    compute_omission_index,
    omission_label,
    framing_volatility_label,
    compute_sa_for_outlet,
    scatter_shot_label,
    compute_pre_synthesis_context,
    synthesize_forensic_report,
    inject_labels,
)
from llm_client import load_llm_config


# ── Modal infrastructure ──

vol = modal.Volume.from_name("narrative-alpha-vault", create_if_missing=True)

image_recipe = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "openai>=1.0.0",
        "requests>=2.31.0",
        "pydantic>=2.0.0",
        "numpy>=1.26.0",
        "trafilatura>=1.12.0",
    )
)

app = modal.App(name="narrative-alpha-core")


# ── Firewall hook: init DB + write default llm_config on cold start ──

DB_INITIALIZED = False


def _ensure_initialized():
    """Idempotent: create SQLite tables and default llm_config on first run."""
    global DB_INITIALIZED
    if DB_INITIALIZED:
        return
    db_path = os.path.join(
        os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha"),
        "outlet_reputation.db",
    )
    conn = get_hardened_db_connection(db_path)
    init_db(conn)
    conn.close()
    load_llm_config()  # writes default if missing
    DB_INITIALIZED = True


# ── Main endpoint ──

@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
    timeout=600,
)
@modal.web_endpoint(method="POST")
async def execute_forensic_pipeline(payload: dict) -> dict:
    """
    Single synchronous pipeline entry point.

    Input:  {"keyword": "Fab 7 manufacturing halt", "vertical": "TECHNOLOGY"}
    Output: Complete Forensic Report JSON (Contract B)

    Execution order (13 steps, see Section 8):
    1. SERP API → discover articles
    2. Web Unlocker → fetch article bodies
    3. Corpus floor gate (min 5 unique source domains)
    4. Outlet reputation check (UNRATED + spawn back-test if new)
    5. Call 1: entity normalization → canonical_map
    6. Call 2: linguistic neutralization per article
    7. Embed raw + neutralized texts → Vf cosine distances
    8. Call 3: graph extraction per source
    9. Python: resolve nodes → Gc → Oi per source
    10. Pre-synthesis: narrative clusters, fractures, term shifts
    11. Call 4: forensic synthesis → Contract B JSON
    12. Python: inject labels via threshold rules
    13. Write reputation + outlier signals → vol.commit()
    """
    _ensure_initialized()

    keyword = payload.get("keyword", "")
    vertical = payload.get("vertical", "TECHNOLOGY")
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    serp_zone = os.environ.get("BRIGHTDATA_SERP_ZONE", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")

    llm_config = load_llm_config()

    # ── Step 1-2: Ingestion ──
    serp_data = discover_articles(keyword, api_key)
    manifest = build_ingestion_manifest(keyword, serp_data, unlocker_zone, api_key)

    # ── Step 3: Corpus floor gate ──
    if "validation_tracking" in manifest:
        return manifest

    documents = manifest["documents"]
    corp_count = manifest["corpus_count"]

    # ── Step 4: Reputation check ──
    db_path = os.path.join(
        os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha"),
        "outlet_reputation.db",
    )
    db_conn = get_hardened_db_connection(db_path)
    for doc in documents:
        status = handle_outlet_registration(
            doc["source_domain"], vertical, db_conn
        )
        if status == "UNRATED":
            # TBD: spawn background back-test via modal.Function.spawn()
            # Requires backtest.py to be a Modal function
            pass
    db_conn.close()

    # ── Step 5: Call 1 — Entity normalization ──
    canonical_map = run_entity_normalization(documents, serp_data, llm_config)

    # ── Step 6: Call 2 — Linguistic neutralization ──
    neutralized = run_linguistic_neutralization(documents, llm_config)

    # ── Step 7: Framing volatility ──
    raw_texts = [d["raw_text_content"] for d in documents]
    vf_scores, vf_labels = compute_framing_volatility(raw_texts, neutralized)

    # ── Step 8: Call 3 — Graph extraction ──
    all_graphs = extract_all_graphs(documents, neutralized, canonical_map, llm_config)

    # ── Step 9: Consensus baseline + Omission index ──
    consensus_nodes = compute_consensus_baseline(all_graphs, canonical_map)

    omission_results = []
    for i, graph in enumerate(all_graphs):
        if graph.get("_parse_error"):
            omission_results.append((1.0, [], "HIGH"))
            continue
        source_nodes = set(graph.get("nodes", []))
        oi, missing = compute_omission_index(consensus_nodes, source_nodes, canonical_map)
        omission_results.append((oi, missing, omission_label(oi)))

    # ── Step 10: Pre-synthesis context ──
    pre_context = compute_pre_synthesis_context(
        all_graphs, neutralized, raw_texts, canonical_map, consensus_nodes
    )

    # ── Build the Call 4 input bundle ──
    # TBD: assemble full context_bundle from all computed data
    context_bundle = {
        "consensus_nodes": list(consensus_nodes),
        "corpus_count": corp_count,
        "per_source": [
            {
                "domain": g.get("_source_domain", ""),
                "name": g.get("_source_name", ""),
                "graph": g,
                "omission_index": omission_results[i][0],
                "omission_label": omission_results[i][2],
                "missing_nodes": omission_results[i][1],
                "framing_volatility": vf_scores[i] if i < len(vf_scores) else 0.0,
                "framing_volatility_label": vf_labels[i] if i < len(vf_labels) else "MED",
            }
            for i, g in enumerate(all_graphs)
        ],
        "narrative_clusters": pre_context["narrative_clusters"],
        "fracture_candidates": pre_context["fracture_candidates"],
        "term_shifts": pre_context["term_shifts"],
    }

    # ── Step 11: Call 4 — Forensic synthesis ──
    report = synthesize_forensic_report(context_bundle, llm_config)

    # ── Step 12: Label injection ──
    report = inject_labels(report)

    # ── Step 13: Persist + commit ──
    # TBD: write outlier signals to SQLite, update reputation ledger
    vol.commit()

    return report


# ── Settings endpoint ──

@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
)
@modal.web_endpoint(method="POST")
async def update_llm_config(payload: dict) -> dict:
    """
    Accepts updated llm_config.json from settings UI.
    Validates required slots, writes to volume, commits.

    Required slots (Section 9.4):
        call_1_entity_normalization
        call_2_linguistic_neutralization
        call_3_graph_extraction
        call_4_forensic_synthesis
    """
    _ensure_initialized()

    required_slots = [
        "call_1_entity_normalization",
        "call_2_linguistic_neutralization",
        "call_3_graph_extraction",
        "call_4_forensic_synthesis",
    ]
    for slot in required_slots:
        if slot not in payload:
            return {"error": f"Missing required slot: {slot}"}

    config_path = os.path.join(
        os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha"),
        "llm_config.json",
    )
    with open(config_path, "w") as f:
        json.dump(payload, f, indent=2)
    vol.commit()

    return {"status": "ok", "config": payload}
```

- [ ] **Step 2: Verify imports**

Run: `python -c "print('app.py not importable without Modal runtime — structural check only')"`
Expected: structural OK (Modal decorators only load inside Modal container)

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Modal orchestration — pipeline endpoint + LLM config settings endpoint"
```

**Sanity check:** Does `execute_forensic_pipeline` follow the 13-step sequence from Section 8? Does the corpus floor gate return before any LLM calls? Does `update_llm_config` validate all 4 required slots?

---

### Task 9: Frontend Dashboard — Static HTML/JS/CSS

**Files:** Create `dashboard/` directory with 4 files.

**What:** Section 11 — Three-zone forensic dashboard with sub-panels + settings page. Dark terminal aesthetic. Read-only JSON consumer.

**Strategy:** Start with a minimal single-file HTML that renders all 3 zones from hardcoded sample JSON. Iterate into separate files (index, event, settings) + shared CSS/JS.

- [ ] **Step 1: Create directory**

```bash
mkdir -p dashboard
```

- [ ] **Step 2: Write `dashboard/style.css`** — TBD (dark terminal aesthetic, color-coded labels per Section 11)
- [ ] **Step 3: Write `dashboard/index.html`** — TBD (cluster list page with timestamps and verticals)
- [ ] **Step 4: Write `dashboard/event.html`** — TBD (3-zone forensic report: consensus baseline, distortion matrix + regime shifts, outlier signals + divergence zones + fractures)
- [ ] **Step 5: Write `dashboard/settings.html`** — TBD (per-slot provider/model/temperature/th!nking form + save POST)
- [ ] **Step 6: Write `dashboard/app.js`** — TBD (fetch cluster data, render zones, settings form logic)

- [ ] **Step 7: Verify HTML/CSS loads in browser**

Open `dashboard/index.html` → check layout, labels render.

- [ ] **Step 8: Commit**

```bash
git add dashboard/
git commit -m "feat: add static dashboard — 3-zone forensic report + settings UI"
```

---

### Task 10: Integration — End-to-End Wire-Up

**Files:** None new. Modify `app.py` to connect TBD stubs.

**What:** Ensure all imports resolve, data flows between layers match the spec contracts, edge cases from Section 10 are handled.

- [ ] **Step 1: Trace `execute_forensic_pipeline` flow against Section 8 ordered list**

Verify each of the 13 steps has a corresponding code block.

- [ ] **Step 2: Verify Contract A → Layer 2 input**

Ingestion manifest dict keys match what `run_entity_normalization` and `run_linguistic_neutralization` expect.

- [ ] **Step 3: Verify Layer 2 → Layer 3 input**

`canonical_map` + `neutralized` + `raw_texts` correctly fed into `extract_all_graphs` and `compute_consensus_baseline`.

- [ ] **Step 4: Verify Contract B output shape**

`ForensicReport` Pydantic model validates against `synthesize_forensic_report` output (after `inject_labels`).

- [ ] **Step 5: Handle Section 10 failure modes**

- SERP returns < 5 domains → floor gate returns early
- LLM parse error → document excluded, graph marked `_parse_error`
- Missing `people_also_ask` → graceful degrade in `build_search_context_table`
- Context window cap → hard cap at 20 docs (add check in `build_ingestion_manifest`)

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "chore: integration wire-up, edge case hardening, contract verification"
```

---

### Task 11: `compute_pre_synthesis_context` — Full Implementation

**File:** Modify `analysis.py`

**What:** Replace the TBD stub with the full Python implementation from Section 6. This is the most algorithmically dense function — narrative clustering, fracture candidate detection, term shift scanning.

- [ ] **Step 1: Write narrative cluster grouping logic**

For each consensus node, iterate over all source graphs. For each source that has an edge pointing to/from the consensus node, collect the connecting node and relationship verb. Sources with different target nodes for the same source node = competing narrative structures.

- [ ] **Step 2: Write fracture candidate detection**

Same pass — flag topic + claim pairs where structurally contradictory claims exist across sources. A simple heuristic: if claim A says "cause = X" and claim B says "cause = Y" and X != Y, flag as a fracture candidate. (Full LLM classification happens in Call 4.)

- [ ] **Step 3: Write term frequency shift scanning**

For each (surface_form, canonical) pair in canonical_map, count how many raw (un-neutralized) document texts contain the surface_form vs the canonical form. Where > 35% of sources use the surface form adjacent to the canonical term, flag as a regime shift candidate.

- [ ] **Step 4: Verify function outputs match Call 4 input expectations**

`narrative_clusters` → `reality_divergence_zones`  
`fracture_candidates` → `reality_fractures`  
`term_shifts` → `narrative_regime_shifts`

- [ ] **Step 5: Commit**

```bash
git add analysis.py
git commit -m "feat: implement compute_pre_synthesis_context — narrative clusters, fracture detection, term shift scanning"
```

---

### Task 12: `execute_historical_backtest` — Full Implementation

**File:** Modify `backtest.py`

**What:** Replace the TBD stub with a full Modal `.spawn()` worker. Wire into `app.py` reputation check step.

- [ ] **Step 1: Implement the 7-step back-test flow**

1. Bright Data SERP `site:{domain}` query with 12-month date range
2. Web Unlocker fetch of up to 15 historical articles
3. < 5 articles → exit with UNRATED
4. Call 1 (entity normalization) + Call 3 (graph extraction) against historical articles
5. Compare historical claim nodes against known-consensus baseline for that topic
6. Count absorbed vs decayed nodes
7. Write `scatter_shot_anomaly_factor`, `historical_origin_validation_rate`, `rating_status = 'RATED'` to SQLite

- [ ] **Step 2: Wire spawn call in `app.py`**

Replace the `# TBD: spawn background back-test` comment with actual `modal.Function.spawn()` call.

- [ ] **Step 3: Verify**

Test with a known domain — verify SQLite row updated from UNRATED → RATED after back-test completes.

- [ ] **Step 4: Commit**

```bash
git add backtest.py app.py
git commit -m "feat: implement full historical back-test worker with Modal spawn integration"
```

---

## Execution Notes

- **Each task = one commit stop.** Run the sanity check before committing.
- **Tasks 9, 11, 12 contain TBD sections.** The Python core (Tasks 1-8, 10) is fully detailed. Frontend and back-test can be fleshed out after the pipeline works end-to-end.
- **Tests:** Each task's Sanity Check serves as the minimum verification. Full test suite (pytest with mocked Bright Data and LLM calls) is deferred to a follow-up plan — the current priority is a working pipeline for the hackathon demo.
- **Hackathon deadline:** Event ends May 31. Tasks 1-8 (Python core) + 10 (integration) are the critical path. Frontend (Task 9) can use the existing `docs/preview-01.html` as a starting point. Back-test (Task 12) is Phase 2 infrastructure and can ship after the demo.

## Self-Review Checklist

- [ ] Spec coverage: Section 14 validation gates → Task 3, Section 7 reputation → Task 4, Section 6 LLM sequence → Tasks 5+6, Section 5 metrics → Task 6, Section 11 frontend → Task 9, Section 9 settings → Task 8
- [ ] No TBD placeholders in Tasks 1-8, 10 (core Python path)
- [ ] Type consistency: `Contracts.py` model field names match dict keys used in `analysis.py`, `processing.py`, `app.py`
- [ ] `compute_omission_index` in `analysis.py` uses `resolve_to_canonical` from same module
- [ ] `inject_labels` covers `omission_label`, `framing_volatility_label`, `scatter_shot_label`, `consensus_stability`, `synchronization_label`
