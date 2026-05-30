"""Layer 1: Ingestion — Bright Data SERP discovery + Web Unlocker extraction."""

import json
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional
from urllib.parse import urlparse, quote

import requests
import trafilatura


SERP_ENDPOINT = "https://api.brightdata.com/request"
UNLOCKER_ENDPOINT = "https://api.brightdata.com/request"
MIN_BODY_CHARS = 200  # trafilatura extraction floor — JS-heavy / paywalled sites return ""


# ── 1. SERP Discovery ──

def discover_articles(keyword: str, zone: str, api_key: str, num: int = 15, time_range: str = "") -> dict:
    """
    Query Bright Data SERP API for Google News results.

    Uses the unified /request endpoint with a Google News search URL.
    Returns dict with news[] containing structured results.

    Args:
        time_range: if non-empty, appended as &tbs=qdr:{time_range}
                    (e.g. "y" for past year, "m" for past month).
    """
    search_url = (
        f"https://www.google.com/search?q={quote(keyword)}"
        f"&tbm=nws&num={num}&gl=us&hl=en"
    )
    if time_range:
        search_url += f"&tbs=qdr:{time_range}"
    payload = {"zone": zone, "url": search_url, "format": "json"}
    response = requests.post(
        SERP_ENDPOINT,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return json.loads(data["body"])


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


# ── 2B. SERP Result Parser + parallel processing helper ──

def parse_serp_result(result: dict) -> dict:
    """
    Extract and normalize fields from a single Bright Data SERP organic result.

    Centralizes .get() fallback chains, domain normalization, and published_at
    extraction so field-name volatility under parsed_light=true is contained here
    rather than scattered across the discovery loop.
    """
    url = result.get("link", "")
    title = result.get("title", "").strip()
    snippet = result.get("snippet") or result.get("description", "").strip()
    published_at = result.get("published_at") or result.get("date") or None

    source_name = result.get("source", "") or ""
    display_link = result.get("display_link") or result.get("link", "") or ""

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
    else:
        # Already have a human-readable source name — keep as-is
        pass

    return {
        "url": url,
        "title": title,
        "source_name": source_name,
        "domain": domain,
        "published_at": published_at,
        "snippet": snippet,
    }


def _process_one_result(
    idx: int, result: dict, zone: str, api_key: str,
    now_utc: str,
    progress_cb: Optional[Callable] = None,
    total: int = 0,
) -> tuple[dict, dict | None]:
    """Fetch, extract, and validate one SERP result. Returns (attempted_doc, validated_doc_or_None)."""
    parsed = parse_serp_result(result)
    url = parsed["url"]
    title = parsed["title"]
    source_name = parsed["source_name"]
    domain = parsed["domain"]
    published_at = parsed["published_at"]

    if progress_cb:
        label = source_name or domain or url
        count_str = f" ({idx + 1}/{total})" if total else ""
        progress_cb("ingesting", f"Fetching {label}{count_str}")

    if not url:
        return _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, "", 0, 0), None

    fetch_status = 0
    raw_text = ""
    try:
        html = fetch_article_body(url, zone, api_key)
        fetch_status = 200
        raw_text = extract_text(html)
    except Exception as e:
        fetch_status = getattr(getattr(e, "response", None), "status_code", 0) or -1
        return _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, "", fetch_status, 0), None

    if len(raw_text) < MIN_BODY_CHARS:
        return _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, raw_text, fetch_status, 0, body_length=len(raw_text)), None

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
        return dict(validated), validated
    else:
        return _attempted_doc(idx, source_name, url, domain, title, published_at, now_utc, raw_text, fetch_status, 0), None


# ── 2C. Attempted-doc builder (shared by sequential and parallel code paths) ──

def _attempted_doc(
    idx: int, source_name: str, url: str, domain: str, title: str,
    published_at: str | None, now_utc: str, raw_text: str,
    fetch_status: int, passed_validation: int,
    body_length: int | None = None,
) -> dict:
    doc: dict = {
        "doc_id": f"DOC-{idx:03d}",
        "source_name": source_name,
        "source_url": url,
        "source_domain": domain,
        "title": title,
        "published_at": published_at,
        "scrape_timestamp": now_utc,
        "raw_text_content": raw_text,
        "fetch_status": fetch_status,
        "passed_validation": passed_validation,
    }
    if body_length is not None:
        doc["body_length"] = body_length
    return doc


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

    # 1. Structural prerequisite checks
    if not source_url or not title:
        return None

    # Extract and normalize canonical domain
    try:
        domain = urlparse(source_url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
    except Exception:
        return None

    # 2. Character and word count floor
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
        r"members\-only\s*story",
    ]
    if any(re.search(p, raw_text, re.IGNORECASE) for p in paywall_patterns):
        return None

    # 4. Nav-bloat / boilerplate scrape detection
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
    progress_cb: Optional[Callable] = None,
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

    organic = serp_data.get("news", serp_data.get("organic", []))
    validated_docs: list[dict] = []
    all_attempted: list[dict] = []

    total = len(organic)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(_process_one_result, idx, result, zone, api_key, now_utc,
                            progress_cb, total)
            for idx, result in enumerate(organic)
        ]
        for future in futures:
            attempted_doc, validated_doc = future.result()
            all_attempted.append(attempted_doc)
            if validated_doc is not None:
                validated_docs.append(validated_doc)

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

    # Hard cap at 20 documents
    corpus_capped = False
    if len(unique_docs) > 20:
        unique_docs = unique_docs[:20]
        corpus_capped = True

    # Log all attempted docs if logger is wired
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
