# Narrative Alpha — Full Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete Narrative Alpha forensic narrative analysis system per spec v1.4

**Architecture:** 4-layer decoupled pipeline (Ingestion → Processing → Analysis → Presentation) orchestrated as a single Modal web endpoint. Bright Data for scraping, DeepSeek V4 for LLM (Flash + Pro), OpenAI for embeddings, SQLite on Modal Volume for persistence.

**Tech Stack:** Python 3.11, Modal Serverless, Bright Data SERP + Web Unlocker, DeepSeek V4, OpenAI embeddings, SQLite (WAL mode), static HTML/JS dashboard

---

## File Map

| File | Layer | Responsibility |
|---|---|---|---|
| `narrative/contracts.py` | Shared | Pydantic models for all data contracts (Contract A, Contract B, LLM config) |
| `narrative/llm_client.py` | Shared | Runtime LLM config loader, provider client factory, `call_llm()` |
| `narrative/ingestion.py` | Layer 1 | SERP discovery, Web Unlocker extraction, `validate_ingestion_payload()`, manifest assembly, corpus floor gate |
| `narrative/processing.py` | Layer 2 | `build_search_context_table()`, entity normalization (Call 1), linguistic neutralization (Call 2) |
| `narrative/analysis.py` | Layer 3 | Graph extraction (Call 3), Python set-math (Gc, Oi, Sa), `compute_pre_synthesis_context()`, forensic synthesis (Call 4), label injection |
| `narrative/reputation.py` | Persistence | SQLite schema, `get_hardened_db_connection()`, `handle_outlet_registration()`, read/write reputation, ingestion log |
| `narrative/backtest.py` | Persistence | Background `.spawn()` worker for historical reputation back-test |
| `narrative/app.py` | Orchestration | Modal endpoints: `execute_forensic_pipeline()`, `update_llm_config()` |
| `dashboard/index.html` | Layer 4 | Index page — list of processed clusters |
| `dashboard/event.html` | Layer 4 | Per-cluster forensic report (3 zones + sub-panels) |
| `dashboard/settings.html` | Layer 4 | Runtime LLM provider/model settings UI |
| `dashboard/style.css` | Layer 4 | Dark terminal aesthetic, color-coded labels |
| `dashboard/app.js` | Layer 4 | Data fetching, zone rendering, settings save |

**Dependency order:** contracts → llm_client → ingestion → reputation → processing → analysis → backtest → app → dashboard

---

### Task 1: Project Scaffolding & Pydantic Data Contracts

**Files:**
- Create: `narrative/contracts.py`
- Create: `.env.example` (verify existing, update if needed)

**What:** All JSON schemas from Sections 4, 5, 9.2 typed as Pydantic models. This is the single source of truth for data shapes across all layers.

**Note:** `llm_config.json` is NOT created as a static file. The defaults are defined as a Pydantic `LLMConfig` model in `narrative/llm_client.py` and auto-written to the Modal Volume on first cold start. This ensures validation at import time — a static JSON file cannot be validated until runtime.

- [ ] **Step 1: Write `narrative/contracts.py` with Contract A models**

```python
"""Data contracts for Narrative Alpha — typed Pydantic models for all layers."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# ── Contract A: Ingestion Manifest (Layer 1 → Layer 2) ──

class IngestionDocument(BaseModel):
    doc_id: str
    source_name: str
    source_domain: str
    source_url: str
    title: str
    scrape_timestamp: str
    published_at: Optional[str] = None
    author: str = "Staff"
    raw_text_content: str


class IngestionManifest(BaseModel):
    cluster_id: str
    trigger_type: str
    search_query: str
    timestamp_utc: str
    corpus_count: int = Field(ge=0)
    corpus_capped: bool = False
    documents: List[IngestionDocument]


# ── Contract B: Forensic Report (Layer 3 → Layer 4) ──

class EventMeta(BaseModel):
    cluster_id: str
    search_query: str
    industry_vertical: str
    timestamp_utc: str
    corpus_count: int
    corpus_capped: bool = False


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


class FloorGateTracking(BaseModel):
    current_state: Literal["INSUFFICIENT_CORPUS_FLOOR"]
    minimum_required: int
    current_count: int


class FloorGateResponse(BaseModel):
    status: Literal["INSUFFICIENT_CORPUS_FLOOR"]
    validation_tracking: FloorGateTracking
```

- [ ] **Step 2: Verify contracts import cleanly**

Run: `python -c "from contracts import IngestionManifest, ForensicReport, LLMConfig; print('contracts OK')"`
Expected: `contracts OK`

- [ ] **Step 3: Commit**

```bash
git add contracts.py
git commit -m "feat: add Pydantic data contracts for all pipeline layers"
```

**Sanity check:** Do all Contract B fields from Section 4 have a matching Pydantic model? Count fields in JSON example vs. models. Does `LLMSlotConfig` match the `llm_config.json` structure from Section 9.2?

---

### Task 2: LLM Client Factory

**File:** Create `narrative/llm_client.py`

**What:** Section 9.3 — Provider-agnostic LLM client. Loads runtime config from Modal Volume, resolves base URLs and API keys, executes calls with JSON mode + optional thinking. Single function `call_llm()` used by all 4 call slots.

**Hardening (beyond base plan):**

| # | Change | Rationale |
|---|---|---|
| H1 | `threading.Lock()` on `_client_cache` | Task 6 may use `asyncio.gather` for parallel Call 2/3 — prevents race on cache init |
| H2 | `retries` default: 1 (2 total attempts), per spec Section 10 | Spec says "one retry" — 1 retry = 2 total |
| H3 | `content is None` guard before `json.loads` | Prevents `TypeError` from `json.loads(None)` — explicit `RuntimeError` instead |
| H4 | Narrow exception handling: re-raise `BaseException` subclasses | Prevents swallowing `KeyboardInterrupt`, `asyncio.CancelledError`, `SystemExit` |

- [ ] **Step 1: Write `narrative/llm_client.py`**

```python
"""Runtime LLM provider configuration and client factory."""

import json
import os
import threading
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


# ── Client factory (H1: thread-safe with Lock) ──

_client_cache: dict[str, OpenAI] = {}
_client_cache_lock = threading.Lock()

def get_llm_client(provider: str) -> OpenAI:
    """Return an OpenAI-compatible client for a provider. Thread-safe, cached per provider."""
    if provider in _client_cache:
        return _client_cache[provider]

    with _client_cache_lock:
        if provider in _client_cache:
            return _client_cache[provider]

        api_key_env = PROVIDER_API_KEY_ENV.get(provider)
        api_key = os.environ.get(api_key_env or "", "")
        if not api_key:
            raise RuntimeError(
                f"No API key for provider '{provider}'. "
                f"Set the {api_key_env} environment variable."
            )
        base_url = PROVIDER_BASE_URLS.get(provider, "")

        client = OpenAI(api_key=api_key, base_url=base_url)
        _client_cache[provider] = client
        return client


# ── Call executor (H4: _NON_RETRIABLE fast-fail) ──

_NON_RETRIABLE = (RuntimeError, KeyError, TypeError, AttributeError)


def build_llm_kwargs(slot_config: dict, messages: list[dict],
                     json_mode: bool = True) -> dict:
    """Build kwargs dict for a chat.completions.create call from slot config."""
    model = slot_config.get("model")
    if not model:
        raise KeyError("slot_config missing required key: 'model'")
    provider = slot_config.get("provider", "")
    kwargs: dict = {
        "model": model,
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
        json_mode: if True, request JSON response format and validate parse
        retries: max retry attempts (default 1 → 2 total attempts, per spec Section 10)

    Returns:
        response.choices[0].message.content as a string.

    Raises:
        RuntimeError: if LLM returns None content (empty response)
        BaseException: re-raised immediately (KeyboardInterrupt, CancelledError, etc.)

    Note: All current calls are single-turn. If multi-turn history is ever needed,
    use extract_assistant_message() to append the assistant turn — do NOT reconstruct
    the dict manually. DeepSeek returns reasoning_content on thinking-mode responses
    and will reject the next request with a 400 if it is missing from the history.
    """
    provider = slot_config["provider"]
    client = get_llm_client(provider)
    kwargs = build_llm_kwargs(slot_config, messages, json_mode)

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if content is None:                                     # H3: explicit None guard
                raise RuntimeError("LLM returned None content")
            if json_mode:
                json.loads(content)                                 # validate parseable
            return content
        except BaseException as e:                                 # H4: narrow catch
            if not isinstance(e, Exception):                        # keyboard / cancel
                raise
            last_error = e
            if attempt < retries:
                continue
            raise

    raise last_error  # type: ignore[misc]


# ── DeepSeek multi-turn helper ──

def extract_assistant_message(response_message) -> dict:
    """
    Build a correctly-shaped assistant message dict from a DeepSeek response object
    for appending to messages history in multi-turn calls.

    DeepSeek's API rejects multi-turn requests with a 400 error if reasoning_content
    is present in the previous assistant turn but not echoed back in the messages list.
    Using the SDK object (not a manually reconstructed dict) is the safe approach.

    Usage:
        response = client.chat.completions.create(...)
        messages.append(extract_assistant_message(response.choices[0].message))
        # then add next user turn and call again
    """
    msg: dict = {"role": "assistant", "content": response_message.content}
    # reasoning_content is only present on thinking-mode responses
    reasoning = getattr(response_message, "reasoning_content", None)
    if reasoning is not None:
        msg["reasoning_content"] = reasoning
    return msg


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

**Sanity check:** Verify `_config_path()` reads `NARRATIVE_ALPHA_ROOT` from env. Verify thinking flag only writes `extra_body` when provider is DeepSeek. Verify `get_embedding()` uses the env-configured embedding model. Verify `get_llm_client` uses double-checked locking (H1). Verify `call_llm` raises `RuntimeError` on None content (H3). Verify `BaseException` subclasses pass through (H4).

---

### Task 3: Ingestion Layer — Discovery, Extraction, Validation

**File:** Create `narrative/ingestion.py`

**What:** Full Layer 1 (Sections 3 and 14). Four sub-systems:
1. SERP API discovery (`discover_articles`)
2. Web Unlocker extraction (`fetch_article_body` + `extract_text`)
3. Validation gates (`validate_ingestion_payload` — exact code from Section 14.1)
4. Manifest assembly + corpus floor gate (`build_ingestion_manifest`)

- [ ] **Step 1: Write `narrative/ingestion.py` — discovery and extraction**

```python
"""Layer 1: Ingestion — Bright Data SERP discovery + Web Unlocker extraction."""

import re
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import urlparse

import requests
import trafilatura


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


MIN_BODY_CHARS = 200  # trafilatura extraction floor — JS-heavy / paywalled sites return ""


def extract_text(html: str) -> str:
    """Strip HTML boilerplate via trafilatura. Returns clean text or ''."""
    text = trafilatura.extract(html)
    return (text or "").strip()


# ── 2B. SERP Result Parser ──

def parse_serp_result(result: dict) -> dict:
    """
    Extract and normalize fields from a single Bright Data SERP organic result.

    Centralizes .get() fallback chains, domain normalization, and published_at
    extraction so field-name volatility under parsed_light=true is contained here
    rather than scattered across the discovery loop.
    """
    from urllib.parse import urlparse

    url = result.get("link", "")
    title = result.get("title", "").strip()
    snippet = result.get("snippet", "").strip()
    published_at = result.get("published_at") or None

    source_name = result.get("source", "") or ""
    display_link = result.get("display_link", "") or ""

    # Domain always from display_link or url — never from source (human-readable name)
    domain = ""
    domain_source = display_link if display_link else url
    if domain_source:
        try:
            parsed = urlparse(domain_source if "://" in domain_source else f"https://{domain_source}")
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            pass

    # Source name: prefer explicit source field; fall back to domain-derived name
    if not source_name:
        if domain:
            name_part = domain.rsplit(".", 1)[0]
            source_name = name_part.replace("-", " ").replace(".", " ").title()

    return {
        "url": url,
        "title": title,
        "source_name": source_name,
        "domain": domain,
        "published_at": published_at,
        "snippet": snippet,
    }


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
        "passed_validation": 1,
    }


# ── 4. Manifest Assembly + Corpus Floor ──

def build_ingestion_manifest(
    keyword: str,
    serp_data: dict,
    zone: str,
    api_key: str,
    db_conn=None,
    logger_func: Optional[Callable] = None,
) -> dict:
    """
    Full Layer 1 pipeline: SERP results → Web Unlocker fetch → validate → manifest.

    Args:
        db_conn: optional SQLite connection — if provided AND logger_func is set,
                 logs ALL scrape attempts (pass and fail) to ingestion_manifest_log.
        logger_func: optional callable matching write_ingestion_log's signature.
                     Passed downstream to avoid a hard import dependency on
                     reputation.py (Task 4). The orchestrator wires this.

    Returns one of:
        - A valid IngestionManifest dict (corpus_count >= 5)
        - A FloorGateResponse dict (corpus_count < 5)
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    cluster_id = f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{keyword[:20].upper().replace(' ', '-')}"

    organic = serp_data.get("organic", [])
    validated_docs: list[dict] = []
    all_attempted: list[dict] = []   # every fetch attempt — for ingestion log

    for idx, result in enumerate(organic):
        parsed = parse_serp_result(result)
        url = parsed["url"]
        title = parsed["title"]
        source_name = parsed["source_name"]
        domain = parsed["domain"]
        published_at = parsed["published_at"]

        if not url:
            continue

        fetch_status = None
        raw_text = ""
        try:
            html = fetch_article_body(url, zone, api_key)
            fetch_status = 200
            raw_text = extract_text(html)
        except Exception as e:
            fetch_status = getattr(getattr(e, "response", None), "status_code", 0) or -1
            all_attempted.append({
                "doc_id": f"DOC-{idx:03d}",
                "source_name": source_name,
                "source_url": url,
                "source_domain": domain,
                "title": title,
                "published_at": published_at,
                "scrape_timestamp": now_utc,
                "raw_text_content": "",
                "fetch_status": fetch_status,
                "passed_validation": 0,
            })
            continue

        # Explicit extraction failure check: HTTP succeeded but trafilatura returned
        # nothing (JS-rendered layout, anti-scrape gate, or paywalled iframe).
        # Log immediately as failed rather than letting validate_ingestion_payload
        # reject it silently with no distinguishable reason in the ingestion log.
        if len(raw_text) < MIN_BODY_CHARS:
            all_attempted.append({
                "doc_id": f"DOC-{idx:03d}",
                "source_name": source_name,
                "source_url": url,
                "source_domain": domain,
                "title": title,
                "published_at": published_at,
                "scrape_timestamp": now_utc,
                "raw_text_content": raw_text,
                "fetch_status": fetch_status,
                "body_length": len(raw_text),
                "passed_validation": 0,
            })
            continue

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
            validated_docs.append(validated)
            all_attempted.append(validated)
        else:
            all_attempted.append({
                "doc_id": f"DOC-{idx:03d}",
                "source_name": source_name,
                "source_url": url,
                "source_domain": domain,
                "title": title,
                "published_at": published_at,
                "scrape_timestamp": now_utc,
                "raw_text_content": raw_text,
                "fetch_status": fetch_status,
                "passed_validation": 0,
            })

    # Deduplicate by unique source_domain, stripping internal tracking fields
    seen_domains: set[str] = set()
    unique_docs = []
    for doc in validated_docs:
        domain = doc.get("source_domain", "")
        if domain not in seen_domains:
            seen_domains.add(domain)
            clean = {k: v for k, v in doc.items()
                     if k not in ("passed_validation", "fetch_status")}
            unique_docs.append(clean)

    # Hard cap at 20 documents — prevents context saturation + Modal timeout (Section 10)
    corpus_capped = False
    if len(unique_docs) > 20:
        unique_docs = unique_docs[:20]
        corpus_capped = True

    # Log all attempted docs (pass and fail) if logger is wired (Section 14.3)
    if db_conn is not None and logger_func is not None:
        logger_func(cluster_id, keyword, now_utc, all_attempted, db_conn)

    corpus_count = len(unique_docs)

    if corpus_count < 5:
        return {
            "status": "INSUFFICIENT_CORPUS_FLOOR",
            "validation_tracking": {
                "current_state": "INSUFFICIENT_CORPUS_FLOOR",
                "minimum_required": 5,
                "current_count": corpus_count,
            },
        }

    manifest = {
        "cluster_id": cluster_id,
        "trigger_type": "KEYWORD",
        "search_query": keyword,
        "timestamp_utc": now_utc,
        "corpus_count": corpus_count,
        "documents": unique_docs,
    }
    if corpus_capped:
        manifest["corpus_capped"] = True
    return manifest
```

- [ ] **Step 2: Verify imports + basic structure**

Run: `python -c "from ingestion import discover_articles, fetch_article_body, extract_text, validate_ingestion_payload, build_ingestion_manifest; print('ingestion OK')"`
Expected: `ingestion OK`

- [ ] **Step 3: Commit**

```bash
git add ingestion.py
git commit -m "feat: add Layer 1 ingestion — SERP discovery, Web Unlocker extraction, validation gates"
```

**Sanity check:** Does `build_ingestion_manifest` accept `logger_func` as an optional keyword? Does it only call `logger_func` when BOTH `db_conn` and `logger_func` are provided? Does it return `FloorGateResponse` shape when corpus < 5? Does it return `IngestionManifest` shape when corpus >= 5? Does `parse_serp_result` normalize domains (no www prefix, lowercased) and derive clean source names? Does `published_at` appear in every `all_attempted` entry and in validated docs? Does `passed_validation: 1` appear in the return dict of `validate_ingestion_payload`? Does the 20-doc hard cap apply before the floor gate check? Does `corpus_capped: True` appear in the manifest when cap fires?

---

### Task 4: Reputation Persistence Layer

**File:** Create `narrative/reputation.py`

**What:** Section 7 — SQLite on Modal Volume. Schema creation, hardened connection, outlet registration with cold-start UNRATED pattern. Also Section 14.3 — ingestion manifest log table.

- [ ] **Step 1: Write `narrative/reputation.py`**

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


def _write_with_retry(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple,
    max_retries: int = 3,
) -> None:
    """
    Execute a write with exponential backoff on OperationalError (database locked).
    Needed because Modal Volumes are network-attached; WAL mode locking can fail
    when the backtest worker and main pipeline write concurrently.
    """
    import time
    delay = 0.1
    for attempt in range(max_retries):
        try:
            conn.execute(sql, params)
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2


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
            PRIMARY KEY (canonical_url, query_id)
        );
    """)
    conn.commit()


def handle_outlet_registration(
    domain: str,
    vertical: str,
    conn: sqlite3.Connection,
    outlet_name: str = "",
) -> str:
    """
    Check if outlet is known. If new: insert UNRATED row immediately.
    Returns the outlet's current rating_status.

    Does NOT spawn the back-test — that's the orchestrator's job.
    outlet_name is stored on first registration (Issue #15 fix).
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rating_status FROM outlet_reputation WHERE domain = ? AND industry_vertical = ?",
        (domain, vertical),
    )
    row = cursor.fetchone()

    if not row:
        _write_with_retry(
            conn,
            "INSERT INTO outlet_reputation (domain, industry_vertical, outlet_name, rating_status, last_updated) "
            "VALUES (?, ?, ?, 'UNRATED', datetime('now'))",
            (domain, vertical, outlet_name),
        )
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
    _write_with_retry(
        conn,
        "INSERT OR IGNORE INTO outlier_tracking "
        "(signal_id, cluster_id, origin_domain, extracted_claim, timestamp_first_seen) "
        "VALUES (?, ?, ?, ?, ?)",
        (signal_id, cluster_id, origin_domain, extracted_claim, timestamp),
    )


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
        # INSERT OR REPLACE so both fetch attempts for the same URL across cluster runs
        # are visible in the debug log (composite uniqueness: canonical_url + query_id)
        conn.execute(
            "INSERT OR REPLACE INTO ingestion_manifest_log "
            "(query_id, topic, discovery_timestamp, source_domain, canonical_url, "
            "title, published_at, fetch_status, body_text, body_length, passed_validation) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                query_id,
                topic,
                discovery_timestamp,
                doc.get("source_domain", ""),
                doc.get("source_url", ""),
                doc.get("title", ""),
                doc.get("published_at"),
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

**Sanity check:** Does `init_db` create 3 tables with correct PKs? Does `handle_outlet_registration` use composite PK (domain, vertical)? Does WAL mode actually activate (PRAGMA journal_mode)? Does `handle_outlet_registration` write `outlet_name` to the INSERT statement?

---

### Task 5: Processing Layer — Calls 1, 2 + Embeddings

**File:** Create `narrative/processing.py`

**What:** Sections 6 (Call 1, Call 2) and 14.2C (search context). Two LLM calls: entity normalization and linguistic neutralization. Vf (framing volatility) computation lives in Layer 3 (`narrative/analysis.py`) per spec Section 2 decoupling rule: "Layer 2 contains zero analysis logic."

**Contract note:** `IngestionDocument` includes optional `published_at` field from Layer 1. If Layer 2 does date-based filtering or temporal decay, field is available and populated. If unused, it passes through silently to Layer 3 via the manifest documents — no stripping needed.

- [ ] **Step 1: Write `narrative/processing.py` — search context helper**

```python
"""Layer 2: Processing — entity normalization and linguistic neutralization only.

Vf (framing volatility) computation is Layer 3 concern — see analysis.py.
"""

from llm_client import call_llm, load_llm_config


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

- [ ] **Step 2: Write `narrative/processing.py` — Call 1 + Call 2 + Vf**

```python
# ── Constants ──

# Max characters per article fed to Call 1 entity normalization.
# DeepSeek V4-Flash 128K context easily handles 15 × 6K + overhead.
ARTICLE_CHAR_LIMIT = 6000


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
    Returns empty dict if LLM returns unparseable JSON — pipeline continues degraded.

    Uses search context table from SERP data to seed the prompt with
    Google's pre-computed synonym resolution.
    """
    from llm_client import call_llm
    import json

    # Build search context table
    search_context = build_search_context_table(serp_data)

    # Concatenate all article texts (truncated to ARTICLE_CHAR_LIMIT each)
    article_texts = "\n\n---\n\n".join(
        f"[{doc['source_domain']}] {doc['title']}: {doc['raw_text_content'][:ARTICLE_CHAR_LIMIT]}"
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

    # Shield: LLM structural failure → empty map, don't crash pipeline
    try:
        raw = call_llm(slot_cfg, messages, json_mode=True)
        data = json.loads(raw)
    except (json.JSONDecodeError, RuntimeError):
        return {}

    mappings = data.get("normalized_mappings", [])
    if not isinstance(mappings, list):
        return {}

    canonical_map: dict[str, str] = {}
    for m in mappings:
        try:
            key = m["surface_form_variant"].strip().lower()
            canonical_map[key] = m["canonical_reference_identity"]
        except (KeyError, TypeError):
            continue

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
    Uses ThreadPoolExecutor for parallel LLM calls (max 5 concurrent).
    Returns list of neutralized text strings (one per doc).
    Failed articles return empty string — filtered downstream.
    """
    from concurrent.futures import ThreadPoolExecutor
    from llm_client import call_llm

    slot_cfg = llm_config["call_2_linguistic_neutralization"]

    def _neutralize_one(doc: dict) -> str:
        messages = [
            {"role": "system", "content": LINGUISTIC_NEUTRALIZATION_SYSTEM_PROMPT},
            {"role": "user", "content": doc["raw_text_content"]},
        ]
        try:
            return call_llm(slot_cfg, messages, json_mode=False).strip()
        except RuntimeError:
            return ""

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(_neutralize_one, documents))

    return results
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from processing import build_search_context_table, run_entity_normalization, run_linguistic_neutralization; print('processing OK')"`
Expected: `processing OK`

- [ ] **Step 4: Commit**

```bash
git add processing.py
git commit -m "feat: add Layer 2 processing — entity normalization and linguistic neutralization"
```

**Sanity check:** Does `build_search_context_table` handle missing `people_also_ask` key (PAA loop just skips — graceful degrade, no code change needed for `merge_and_resolve`)? Does `run_entity_normalization` lowercase all map keys? Is `compute_framing_volatility` absent from `narrative/processing.py` (it belongs in `narrative/analysis.py`)?

---

### Task 6: Analysis Layer — Calls 3, 4 + Python Set Math

**File:** Create `narrative/analysis.py`

**What:** Sections 5, 6 (Call 3, Call 4), 5.2 (Vf), and pre-synthesis pass. This is the largest and most complex file. Seven sub-systems:
1. Graph extraction (Call 3 — DeepSeek V4-Pro thinking)
2. Resolve-to-canonical + omission index (Python)
3. Consensus baseline Gc (Python)
4. Scatter-Shot Anomaly Sa (Python + SQLite)
5. **Framing Volatility Vf** (Python + OpenAI embeddings) — moved here from processing.py per layer decoupling
6. Pre-synthesis context aggregation (Python)
7. Forensic synthesis (Call 4 — DeepSeek V4-Pro thinking)
8. Label injection (Python threshold rules)

**Call 3 timeout note:** Serial thinking-mode calls take ~10–30s each. 15 articles × 20s = 300s, leaving minimal headroom in Modal's 600s timeout. Consider `asyncio.gather` for parallel Call 3 invocations — articles are independent, no ordering dependency. The 20-doc hard cap (Task 3) bounds worst-case to 20 × 20s = 400s absolute ceiling.

- [ ] **Step 1: Write `narrative/analysis.py` — Call 3 + Python metrics**

```python
"""Layer 3: Analysis — graph extraction, forensic synthesis, metric computation.

Vf (framing volatility) lives here — not in processing.py — per spec Section 2
decoupling rule: Layer 2 contains zero analysis logic.
"""

import json
import uuid
from typing import Optional

import numpy as np

from llm_client import call_llm, get_embedding


# ── Call 3: Graph Extraction (DeepSeek V4-Pro, thinking enabled) ──

GRAPH_EXTRACTION_SYSTEM_PROMPT = (
    "You are a knowledge graph extraction engine. Given the normalized "
    "article text and entity reference dictionary, extract all factual "
    "claims as a structured node-and-edge graph. Nodes are named entities, "
    "events, timestamps, and quantities. Edges are directed relationships "
    "with a verb. Entity dictionary keys are lowercased — match "
    "case-insensitively against the article text (e.g. 'Apple' matches "
    "'apple'). Output only valid JSON matching the schema provided. "
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
    n = sum(1 for g in all_graphs if not g.get("_parse_error"))
    if n < 5:
        return set()

    threshold = int(0.75 * n) + 1  # ceiling against valid sources only

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


# ── Framing Volatility Score + label (Section 5.2) — Layer 3, not Layer 2 ──

def framing_volatility_label(vf: float) -> str:
    if vf < 0.25:
        return "LOW"
    elif vf < 0.55:
        return "MED"
    else:
        return "HIGH"


def compute_framing_volatility(
    raw_texts: list[str],
    neutralized_texts: list[str],
) -> tuple[list[float], list[str]]:
    """
    Compute Vf = 1 - cos(raw_embedding, neutralized_embedding) per document.
    Called inside run_analysis_layer after Call 2 outputs are available.

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
        labels.append(framing_volatility_label(vf))

    return scores, labels


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

- [ ] **Step 2: Write `narrative/analysis.py` — pre-synthesis pass**

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
    # STUB: Task 11 must implement this before the pipeline can run.
    # Overview of what Task 11 must build:
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
    raise NotImplementedError(
        "Task 11: compute_pre_synthesis_context not yet implemented. "
        "Running the pipeline without this produces empty reality_divergence_zones, "
        "reality_fractures, and narrative_regime_shifts — the entire v1.4 forensic layer. "
        "Implement Task 11 before executing the pipeline."
    )
```

- [ ] **Step 3: Write `narrative/analysis.py` — Call 4 forensic synthesis**

```python
# ── Call 4: Forensic Synthesis (DeepSeek V4-Pro, thinking enabled) ──

FORENSIC_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a forensic narrative analysis engine. Your task is to analyze HOW reality "
    "is being described across institutional media sources — not to determine which "
    "description is objectively correct. You map narrative topology: what all outlets "
    "agree on, who omitted which facts, who used linguistic camouflage, and which "
    "single-source outlier claims exist. "
    "Your output must reflect narrative structure, not truth arbitration. "
    "Output only valid JSON. The word 'json' must appear in your response.\n\n"
    "Required output schema (Contract B):\n"
    "{\n"
    "  \"event_meta\": {\"cluster_id\": str, \"search_query\": str, \"industry_vertical\": str, \"timestamp_utc\": str, \"corpus_count\": int},\n"
    "  \"consensus_reality_graph\": {\"consensus_summary\": str, \"verified_anchor_nodes\": [str], \"primary_verifications\": [{\"authority\": str, \"reference_id\": str, \"status\": str}]},\n"
    "  \"distortion_matrix\": [{\"outlet_name\": str, \"source_domain\": str, \"omission_index\": float, \"framing_volatility_score\": float, \"identifiable_omissions\": [str], \"linguistic_camouflage\": [{\"raw_expression\": str, \"clinical_translation\": str}]}],\n"
    "  \"outlier_signals\": [{\"signal_id\": str, \"origin_outlet\": str, \"origin_domain\": str, \"extracted_claim\": str, \"timestamp_first_seen\": str, \"outlier_origin_provenance\": {\"classification\": str, \"historical_origin_validation_rate\": float, \"scatter_shot_anomaly_factor\": float, \"reputation_warning_triggered\": bool, \"echo_chamber_mimics\": [str]}, \"validation_tracking\": {\"current_state\": str, \"last_checked_timestamp\": str, \"consensus_absorption_status\": str, \"evaluation_window_days\": int}}],\n"
    "  \"reputation_warnings\": [{\"outlet_name\": str, \"source_domain\": str, \"warning_triggered\": bool, \"historical_origin_validation_rate\": float, \"scatter_shot_anomaly_factor\": float, \"scatter_shot_label\": str, \"warning_message\": str}],\n"
    "  \"reality_divergence_zones\": [{\"topic\": str, \"consensus_stability_score\": float, \"institutional_convergence\": str, \"observed_narrative_structures\": [str], \"supporting_outlets\": {\"<narrative>\": [\"<domain>\"]}}],\n"
    "  \"reality_fractures\": [{\"fracture_id\": str, \"topic\": str, \"claim_a\": {\"statement\": str, \"supporting_outlets\": [str]}, \"claim_b\": {\"statement\": str, \"supporting_outlets\": [str]}, \"relationship\": str, \"resolution_status\": str}],\n"
    "  \"narrative_regime_shifts\": [{\"shift_id\": str, \"topic\": str, \"detected_shift\": {\"previous_term\": str, \"replacement_term\": str}, \"observed_across\": int, \"total_sources\": int, \"synchronization_score\": float, \"interpretive_note\": str}]\n"
    "}"
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

    for fracture in report.get("reality_fractures", []):
        # Constant default — not a threshold label, but missing from raw dict
        # since Pydantic defaults only apply on model instantiation.
        fracture.setdefault("classification_method", "LLM_ASSISTED")

    return report
```

- [ ] **Step 4: Verify imports**

Run: `python -c "from analysis import extract_graph, compute_omission_index, compute_consensus_baseline, compute_framing_volatility, synthesize_forensic_report, inject_labels; print('analysis OK')"`
Expected: `analysis OK`

- [ ] **Step 5: Commit**

```bash
git add analysis.py
git commit -m "feat: add Layer 3 analysis — graph extraction, forensic synthesis, all metrics"
```

**Sanity check:** Does `resolve_to_canonical` handle lowercase mapping correctly? Does `compute_consensus_baseline` use ceiling threshold (>75%, not >=)? Does `compute_omission_index` handle division by zero? Does `inject_labels` cover all 4 metric fields plus `classification_method` on `reality_fractures`? Is `compute_framing_volatility` in `narrative/analysis.py` (not `narrative/processing.py`)? Does `compute_framing_volatility` import `get_embedding` from `llm_client`?

---

### Task 7: Back-Test Worker

**File:** Create `narrative/backtest.py`

**What:** Section 7 — `run_historical_backtest()`. This is a detached Modal function invoked via `.spawn()` after cold-start outlet registration. It queries Bright Data SERP for historical articles from a domain, runs Call 1 + Call 3 against them, then writes reputation metrics to SQLite.

- [ ] **Step 1: Write `narrative/backtest.py` — stub with full structure**

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

### Task 8: Orchestration — `narrative/app.py` + Settings Endpoint

**File:** Create `narrative/app.py`

**What:** Sections 8 and 9.4 — Modal orchestration. Two web endpoints:
1. `execute_forensic_pipeline` (POST) — the main pipeline
2. `update_llm_config` (POST) — runtime settings writer

- [ ] **Step 1: Write `narrative/app.py`**

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
    read_outlet_reputation,
    write_outlier_signal,
)
from ingestion import discover_articles, build_ingestion_manifest
from processing import (
    run_entity_normalization,
    run_linguistic_neutralization,
)
from analysis import (
    extract_all_graphs,
    compute_consensus_baseline,
    compute_omission_index,
    compute_framing_volatility,
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


# ── Cold-start init: runs on every container start (all ops are idempotent) ──

def _run_startup_init():
    """
    Run DB init and config load on every cold start.
    Safe to call repeatedly — init_db uses CREATE TABLE IF NOT EXISTS,
    load_llm_config skips write if config already exists.
    No module-level flag needed; the underlying ops are idempotent.
    """
    db_path = os.path.join(
        os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha"),
        "outlet_reputation.db",
    )
    conn = get_hardened_db_connection(db_path)
    init_db(conn)
    conn.close()
    load_llm_config()  # writes default if missing


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

    Execution order (14 steps, see Section 8):
    1.  SERP API → discover articles
    2.  Web Unlocker → fetch article bodies + log all attempts to ingestion_manifest_log
    3.  Corpus floor gate (min 5 unique source domains)
    4.  Outlet reputation check (UNRATED + spawn back-test if new); read reputation records
    5.  Call 1: entity normalization → canonical_map
    6.  Call 2: linguistic neutralization per article
    7.  Call 3: graph extraction per source
    8.  Python: resolve nodes → Gc → Oi per source
    9.  Vf: embed raw + neutralized texts → cosine distances (Layer 3)
    10. Pre-synthesis: narrative clusters, fractures, term shifts
    11. Call 4: forensic synthesis → Contract B JSON
    12. Python: inject labels via threshold rules
    13. Write outlier signals to SQLite
    14. vol.commit()
    """
    _run_startup_init()

    keyword = payload.get("keyword", "")
    vertical = payload.get("vertical", "TECHNOLOGY")
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")

    llm_config = load_llm_config()

    db_path = os.path.join(
        os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha"),
        "outlet_reputation.db",
    )

    # ── Step 1-2: Ingestion + ingestion log ──
    # Pass db_conn so build_ingestion_manifest logs all fetch attempts (pass+fail)
    db_conn = get_hardened_db_connection(db_path)
    serp_data = discover_articles(keyword, api_key)
    manifest = build_ingestion_manifest(keyword, serp_data, unlocker_zone, api_key, db_conn=db_conn)

    # ── Step 3: Corpus floor gate ──
    if "validation_tracking" in manifest:
        db_conn.close()
        return manifest

    documents = manifest["documents"]
    corp_count = manifest["corpus_count"]

    # ── Step 4: Reputation check + read records for Call 4 bundle ──
    reputation_records: dict[str, dict] = {}
    for doc in documents:
        status = handle_outlet_registration(
            doc["source_domain"], vertical, db_conn,
            outlet_name=doc.get("source_name", ""),
        )
        rep = read_outlet_reputation(doc["source_domain"], vertical, db_conn)
        reputation_records[doc["source_domain"]] = rep or {"rating_status": "UNRATED"}
        if status == "UNRATED":
            run_historical_backtest.spawn(doc["source_domain"], vertical)
    db_conn.close()

    # ── Step 5: Call 1 — Entity normalization ──
    canonical_map = run_entity_normalization(documents, serp_data, llm_config)

    # ── Step 6: Call 2 — Linguistic neutralization ──
    neutralized = run_linguistic_neutralization(documents, llm_config)

    # ── Step 7: Call 3 — Graph extraction ──
    raw_texts = [d["raw_text_content"] for d in documents]
    all_graphs = extract_all_graphs(documents, neutralized, canonical_map, llm_config)

    # ── Step 8: Consensus baseline + Omission index ──
    consensus_nodes = compute_consensus_baseline(all_graphs, canonical_map)

    omission_results = []
    for i, graph in enumerate(all_graphs):
        if graph.get("_parse_error"):
            omission_results.append((1.0, [], "HIGH"))
            continue
        source_nodes = set(graph.get("nodes", []))
        oi, missing = compute_omission_index(consensus_nodes, source_nodes, canonical_map)
        omission_results.append((oi, missing, omission_label(oi)))

    # ── Step 9: Vf — Framing volatility (Layer 3, not Layer 2) ──
    vf_scores, vf_labels = compute_framing_volatility(raw_texts, neutralized)

    # ── Step 10: Pre-synthesis context ──
    pre_context = compute_pre_synthesis_context(
        all_graphs, neutralized, raw_texts, canonical_map, consensus_nodes
    )

    # ── Build the Call 4 input bundle (Section 6) ──
    context_bundle = {
        "consensus_nodes": list(consensus_nodes),
        "corpus_count": corp_count,
        "search_query": keyword,
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
                # Neutralized text pairs for linguistic camouflage detection
                "raw_text": raw_texts[i] if i < len(raw_texts) else "",
                "neutralized_text": neutralized[i] if i < len(neutralized) else "",
            }
            for i, g in enumerate(all_graphs)
        ],
        # Reputation records from SQLite — required for reputation_warnings in Call 4
        "reputation_records": reputation_records,
        "narrative_clusters": pre_context["narrative_clusters"],
        "fracture_candidates": pre_context["fracture_candidates"],
        "term_shifts": pre_context["term_shifts"],
        "corpus_capped": manifest.get("corpus_capped", False),
    }

    # ── Step 11: Call 4 — Forensic synthesis ──
    report = synthesize_forensic_report(context_bundle, llm_config)

    # ── Step 12: Label injection + corpus_capped flag ──
    report = inject_labels(report)
    report.setdefault("event_meta", {})["corpus_capped"] = manifest.get("corpus_capped", False)

    # ── Step 13: Write outlier signals to SQLite ──
    db_conn = get_hardened_db_connection(db_path)
    for signal in report.get("outlier_signals", []):
        write_outlier_signal(
            signal_id=signal.get("signal_id", ""),
            cluster_id=manifest["cluster_id"],
            origin_domain=signal.get("origin_domain", ""),
            extracted_claim=signal.get("extracted_claim", ""),
            timestamp=signal.get("timestamp_first_seen", ""),
            conn=db_conn,
        )
    db_conn.close()

    # ── Step 14: Commit volume ──
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
    _run_startup_init()

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


# ── Background back-test Modal function (Section 7) ──
# Decorated here in app.py so .spawn() works — implementation is in backtest.py.
# Task 12 implements execute_historical_backtest in backtest.py.

@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
    timeout=600,
)
def run_historical_backtest(domain: str, vertical: str) -> None:
    """
    Non-blocking background task. Runs after main pipeline returns.
    Imports execute_historical_backtest from backtest.py.
    On completion: writes reputation metrics to SQLite and commits volume.
    """
    from backtest import execute_historical_backtest
    execute_historical_backtest(domain, vertical)
    vol.commit()
```

- [ ] **Step 2: Verify imports**

Run: `python -c "print('app.py not importable without Modal runtime — structural check only')"`
Expected: structural OK (Modal decorators only load inside Modal container)

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Modal orchestration — pipeline endpoint + LLM config settings endpoint + backtest spawn"
```

**Sanity check:** Does `execute_forensic_pipeline` follow the 14-step sequence? Does the corpus floor gate return before any LLM calls? Does `update_llm_config` validate all 4 required slots? Does `reputation_records` appear in `context_bundle`? Is `compute_framing_volatility` called from analysis (step 9), not processing? Does `run_historical_backtest` have `@app.function` decorator? Does step 4 call `.spawn()` (not pass)?

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

**Files:** None new. Modify `narrative/app.py` to connect TBD stubs.

**What:** Ensure all imports resolve, data flows between layers match the spec contracts, edge cases from Section 10 are handled.

- [ ] **Step 1: Trace `execute_forensic_pipeline` flow against Section 8 ordered list**

Verify each of the 14 steps has a corresponding code block.

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

**File:** Modify `narrative/analysis.py`

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

**File:** Modify `narrative/backtest.py`

**What:** Replace the TBD stub with a full Modal `.spawn()` worker. Wire into `narrative/app.py` reputation check step.

- [ ] **Step 1: Implement the 7-step back-test flow**

1. Bright Data SERP `site:{domain}` query with 12-month date range
2. Web Unlocker fetch of up to 15 historical articles
3. < 5 articles → exit with UNRATED
4. Call 1 (entity normalization) + Call 3 (graph extraction) against historical articles
5. Compare historical claim nodes against known-consensus baseline for that topic
6. Count absorbed vs decayed nodes
7. Write `scatter_shot_anomaly_factor`, `historical_origin_validation_rate`, `rating_status = 'RATED'` to SQLite

- [ ] **Step 2: Wire spawn call in `narrative/app.py`**

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
- **Tasks 9 and 12 contain TBD sections.** The Python core (Tasks 1-8, 10, 11) is fully detailed. Frontend and full back-test implementation can be fleshed out after the pipeline works end-to-end.
- **Tests:** Each task's Sanity Check serves as the minimum verification. Full test suite (pytest with mocked Bright Data and LLM calls) is deferred to a follow-up plan — the current priority is a working pipeline for the hackathon demo.
- **Hackathon deadline:** Event ends May 31. **Critical path: Tasks 1-8, 10, 11.** Task 11 (`compute_pre_synthesis_context`) must be on the critical path — without it, all three v1.4 forensic output objects (`reality_divergence_zones`, `reality_fractures`, `narrative_regime_shifts`) will be empty arrays in the demo. Frontend (Task 9) can use the existing `docs/preview-01.html` as a starting point. Back-test Task 12 is Phase 2 infrastructure.
- **Call 2 + Call 3 serial timeout risk:** Call 2 (linguistic neutralization) runs N sequential flash-tier calls — fast (~1–2s each) but cumulative. Call 3 (graph extraction) runs N thinking-mode calls at ~10–30s each. 20 articles × 20s = 400s for Call 3 alone, barely under Modal's 600s timeout. If demo runs slow, switch both `run_linguistic_neutralization` and `extract_all_graphs` to use `asyncio.gather` — articles are fully independent in both passes. The 20-doc hard cap (Task 3) limits worst-case exposure.

## Self-Review Checklist

- [ ] Spec coverage: Section 14 validation gates → Task 3, Section 7 reputation → Task 4, Section 6 LLM sequence → Tasks 5+6, Section 5 metrics → Task 6, Section 11 frontend → Task 9, Section 9 settings → Task 8
- [ ] No TBD placeholders in Tasks 1-8, 10, 11 (critical path)
- [ ] Type consistency: `narrative/contracts.py` model field names match dict keys used in `narrative/analysis.py`, `narrative/processing.py`, `narrative/app.py`
- [ ] `compute_omission_index` in `narrative/analysis.py` uses `resolve_to_canonical` from same module
- [ ] `inject_labels` covers `omission_label`, `framing_volatility_label`, `scatter_shot_label`, `consensus_stability`, `synchronization_label`
- [ ] `compute_framing_volatility` is in `narrative/analysis.py`, NOT `narrative/processing.py` (layer decoupling — Issue #1 fix)
- [ ] `validate_ingestion_payload` return dict includes `passed_validation: 1` (Issue #4 fix)
- [ ] `build_ingestion_manifest` accepts `db_conn`, calls `write_ingestion_log`, applies 20-doc cap (Issues #3, #13 fix)
- [ ] `handle_outlet_registration` stores `outlet_name` (Issue #15 fix)
- [ ] `context_bundle` in `narrative/app.py` includes `reputation_records` dict (Issue #9 fix)
- [ ] `run_historical_backtest` has `@app.function` decorator in `narrative/app.py`; step 4 calls `.spawn()` (Issue #10 fix)
- [ ] Task 11 (`compute_pre_synthesis_context`) is on critical path — v1.4 forensic objects empty without it (Issue #7 fix)
- [ ] SERP payload uses `"engine": "google"`, `"tbm": "nws"`, `"q"` — confirmed present in plan (Issue #5 was false positive)
- [ ] `serp_data` raw response passed to both `build_ingestion_manifest` and `run_entity_normalization` — same object (Issue #8 confirmed correct)
- [ ] `compute_pre_synthesis_context` stub raises `NotImplementedError` — fails loud before demo rather than returning hollow report (v2 Issue #1 fix)
- [ ] `FORENSIC_SYNTHESIS_SYSTEM_PROMPT` contains explicit Contract B JSON schema skeleton — Call 4 not flying blind on output shape (v2 Issue #2 fix)
- [ ] `_run_startup_init()` replaces `DB_INITIALIZED` flag — runs every cold start, no false cache (v2 Issue #3 fix)
- [ ] `EventMeta` has `corpus_capped: bool = False`; app.py injects `manifest.get("corpus_capped")` into `report["event_meta"]` after Call 4 (v2 Issue #5 fix)
- [ ] `compute_consensus_baseline` computes `n` from non-error graphs only — threshold not skewed by parse failures (v2 Issue #6 fix)
- [ ] Execution Notes call out both Call 2 and Call 3 serial timeout risk (v2 Issue #7 fix)
- [ ] `write_ingestion_log` uses `INSERT OR REPLACE` — both fetch attempts for same URL visible in debug log (v2 Issue #8 fix)
- [ ] Task 10 Step 1 says "14 steps" not "13 steps" (v2 Issue #9 fix)
- [ ] File map `narrative/processing.py` row no longer lists "embedding generation, Vf computation" (v2 Issue #10 fix)
- [ ] `_write_with_retry` exists in `narrative/reputation.py`; `handle_outlet_registration` and `write_outlier_signal` use it (concurrent backtest write safety)
- [ ] `extract_assistant_message()` exists in `narrative/llm_client.py`; checks for `reasoning_content` via `getattr` and includes it when present; `call_llm` docstring warns against manual dict reconstruction for multi-turn
- [ ] `MIN_BODY_CHARS = 200` constant defined in `narrative/ingestion.py`; early exit after `extract_text` logs extraction-failed docs to `all_attempted` with `passed_validation: 0` before `validate_ingestion_payload` is called
- [ ] `inject_labels` sets `fracture.setdefault("classification_method", "LLM_ASSISTED")` on all `reality_fractures` — field present in Pydantic model but absent from raw Call 4 dict without explicit injection
