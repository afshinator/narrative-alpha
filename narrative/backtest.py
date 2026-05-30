"""Background back-test worker for outlet reputation scoring.

Invoked as a daemon thread from the pipeline. Makes SERP queries + LLM
calls to compute scatter_shot_anomaly_factor and
historical_origin_validation_rate, then writes results to SQLite.
"""

import os
import logging

from narrative.ingestion import discover_articles, fetch_article_body, extract_text
from narrative.processing import run_entity_normalization
from narrative.analysis import extract_graph, compute_consensus_baseline, resolve_to_canonical
from narrative.reputation import get_hardened_db_connection
from narrative.llm_client import load_llm_config

logger = logging.getLogger(__name__)

MIN_ARTICLES = 5
MIN_BODY_CHARS = 300


def execute_historical_backtest(domain: str, vertical: str) -> None:
    """
    Background task: back-test an outlet's historical accuracy.

    Historical backtesting does not attempt to reconstruct 30-day absorption
    behavior (that belongs to the online outlier_tracking system). Instead, it
    approximates outlet reliability through cross-source persistence.

    1. SERP Query 1 (target): site:{domain} {vertical}, tbm=nws, num=15, tbs=qdr:y
    2. SERP Query 2 (baseline): {vertical}, tbm=nws, num=15, tbs=qdr:y — no site filter
    3. Web Unlocker: fetch article bodies from both queries
    4. Floor gate: if either query < 5 articles -> UNRATED, exit
    5. Call 1 + Call 3 on both article sets independently
    6. Classify claims from target against consensus baseline:
       - consensus-supported: claim appears in multi-source consensus
       - consensus-isolated: claim appears only in target outlet's graph
    7. Compute metrics:
       historical_origin_validation_rate = consensus_supported / total_claims
       scatter_shot_anomaly_factor       = consensus_isolated / total_claims
    8. Write Sa, historical_origin_validation_rate, rating_status='RATED' to SQLite

    Args:
        domain: source domain to back-test (e.g. "globalwire.com")
        vertical: industry vertical (e.g. "TECHNOLOGY")
    """
    api_key = os.environ.get("BRIGHTDATA_API_KEY", "")
    unlocker_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE", "")
    serp_zone = os.environ.get("BRIGHTDATA_SERP_ZONE", unlocker_zone)
    narrative_root = os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha")
    db_path = os.path.join(narrative_root, "outlet_reputation.db")

    if not api_key or not unlocker_zone:
        logger.warning("Backtest %s/%s: missing API credentials", domain, vertical)
        return

    llm_config = load_llm_config()

    try:
        target_serp = discover_articles(
            f"site:{domain} {vertical}", serp_zone, api_key,
            num=15, time_range="y",
        )
        baseline_serp = discover_articles(
            vertical, serp_zone, api_key,
            num=15, time_range="y",
        )
    except Exception:
        logger.warning("Backtest %s/%s: SERP failed", domain, vertical, exc_info=True)
        return

    target_results = target_serp.get("news", target_serp.get("organic", []))
    baseline_results = baseline_serp.get("news", baseline_serp.get("organic", []))

    if len(target_results) < MIN_ARTICLES or len(baseline_results) < MIN_ARTICLES:
        logger.info("Backtest %s/%s: floor gate (SERP results < %d)", domain, vertical, MIN_ARTICLES)
        return

    target_docs = _fetch_articles(target_results, domain, unlocker_zone, api_key)
    baseline_docs = _fetch_articles(baseline_results, None, unlocker_zone, api_key)

    if len(target_docs) < MIN_ARTICLES or len(baseline_docs) < MIN_ARTICLES:
        logger.info("Backtest %s/%s: fetch floor gate (valid articles < %d)", domain, vertical, MIN_ARTICLES)
        return

    all_docs = target_docs + baseline_docs
    combined_serp = {
        "organic": target_results + baseline_results,
        "news": target_results + baseline_results,
    }

    try:
        canonical_map = run_entity_normalization(all_docs, combined_serp, llm_config)
    except Exception:
        logger.warning("Backtest %s/%s: entity normalization failed", domain, vertical, exc_info=True)
        return

    if not canonical_map:
        logger.info("Backtest %s/%s: empty canonical map", domain, vertical)
        return

    all_graphs = []
    for doc in all_docs:
        try:
            graph = extract_graph(doc["raw_text_content"], canonical_map, llm_config)
            all_graphs.append(graph)
        except Exception:
            all_graphs.append({"_parse_error": True, "nodes": [], "edges": []})

    target_graphs = all_graphs[:len(target_docs)]
    baseline_graphs = all_graphs[len(target_docs):]

    for i, g in enumerate(baseline_graphs):
        g["_source_domain"] = f"baseline-{i}"

    baseline_consensus = compute_consensus_baseline(baseline_graphs, canonical_map)

    if not baseline_consensus:
        logger.info("Backtest %s/%s: no baseline consensus", domain, vertical)
        return

    total_claims = 0
    consensus_supported = 0
    consensus_isolated = 0

    for graph in target_graphs:
        for node in graph.get("nodes", []):
            total_claims += 1
            nc = resolve_to_canonical(node, canonical_map)
            if nc in baseline_consensus:
                consensus_supported += 1
            else:
                consensus_isolated += 1

    if total_claims == 0:
        logger.info("Backtest %s/%s: zero claims", domain, vertical)
        return

    sa = round(consensus_isolated / total_claims, 4)
    validation_rate = round(consensus_supported / total_claims, 4)

    conn = get_hardened_db_connection(db_path)
    try:
        conn.execute(
            "UPDATE outlet_reputation SET "
            "scatter_shot_anomaly_factor = ?, "
            "historical_origin_validation_rate = ?, "
            "rating_status = 'RATED', "
            "back_test_article_count = ?, "
            "last_updated = datetime('now') "
            "WHERE domain = ? AND industry_vertical = ?",
            (sa, validation_rate, len(target_docs), domain, vertical),
        )
        conn.commit()
        logger.info(
            "Backtest %s/%s: SA=%.4f, val=%.4f, articles=%d",
            domain, vertical, sa, validation_rate, len(target_docs),
        )
    except Exception:
        logger.warning("Backtest %s/%s: DB write failed", domain, vertical, exc_info=True)
    finally:
        conn.close()


def _fetch_articles(
    results: list[dict],
    domain: str | None,
    unlocker_zone: str,
    api_key: str,
) -> list[dict]:
    """Fetch article bodies from SERP results and extract text.

    Args:
        domain: if set, used as source_domain; otherwise uses SERP result domain.
    """
    docs = []
    for result in results[:15]:
        url = result.get("link") or result.get("url", "")
        if not url:
            continue
        try:
            html = fetch_article_body(url, unlocker_zone, api_key)
            text = extract_text(html)
            if len(text) >= MIN_BODY_CHARS:
                source_domain = domain or result.get("display_link", "") or ""
                docs.append({
                    "source_domain": source_domain,
                    "source_name": result.get("source", source_domain),
                    "raw_text_content": text,
                    "title": result.get("title", ""),
                })
        except Exception:
            continue
    return docs
