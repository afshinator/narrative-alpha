"""Core forensic pipeline — no Modal dependencies, fully testable."""

import os
import threading
import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

from narrative.reputation import (
    get_hardened_db_connection,
    init_db,
    handle_outlet_registration,
    read_outlet_reputation,
    write_outlier_signal,
    write_ingestion_log,
)
from narrative.ingestion import discover_articles, build_ingestion_manifest
from narrative.processing import (
    run_entity_normalization,
    run_linguistic_neutralization,
)
from narrative.analysis import (
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
from narrative.llm_client import load_llm_config


def _run_startup_init():
    db_path = os.path.join(
        os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha"),
        "outlet_reputation.db",
    )
    conn = get_hardened_db_connection(db_path)
    init_db(conn)
    conn.close()
    load_llm_config()


def _run_pipeline(
    keyword: str,
    vertical: str,
    api_key: str,
    unlocker_zone: str,
    serp_zone: str,
    db_path: str,
    progress_cb: Optional[Callable[[str, str], None]] = None,
) -> dict:
    """Execute the full forensic pipeline synchronously."""
    from narrative.backtest import execute_historical_backtest

    _pipeline_start = time.time()
    _t = time.time()
    llm_config = load_llm_config()

    db_conn = get_hardened_db_connection(db_path)
    if progress_cb: progress_cb("discovering", "Searching for articles...")
    logger.info("STEP 1/7: Discovering articles via SERP API")
    serp_data = discover_articles(keyword, serp_zone, api_key)
    logger.info("STEP 1/7 done — %.1fs", time.time() - _t)

    _t = time.time()
    if progress_cb: progress_cb("ingesting", "Fetching article content...")
    logger.info("STEP 2/7: Building ingestion manifest (fetching articles)")
    manifest = build_ingestion_manifest(
        keyword, serp_data, unlocker_zone, api_key,
        db_conn=db_conn,
        logger_func=write_ingestion_log,
        progress_cb=progress_cb,
    )

    if "validation_tracking" in manifest:
        db_conn.close()
        logger.info("Corpus floor gate — %.1fs", time.time() - _t)
        return manifest

    logger.info("STEP 2/7 done — %.1fs", time.time() - _t)

    documents = manifest["documents"]
    corp_count = manifest["corpus_count"]
    reputation_records = {}
    logger.info("STEP 3/7: Registering outlets + spawning backtest threads ...")
    for doc in documents:
        status = handle_outlet_registration(
            doc["source_domain"], vertical, db_conn,
            outlet_name=doc.get("source_name", ""),
        )
        rep = read_outlet_reputation(doc["source_domain"], vertical, db_conn)
        reputation_records[doc["source_domain"]] = rep or {"rating_status": "UNRATED"}
        if status == "UNRATED":
            threading.Thread(
                target=execute_historical_backtest,
                args=(doc["source_domain"], vertical),
                daemon=True,
            ).start()
    db_conn.close()
    logger.info("STEP 3/7 done — %.1fs", time.time() - _t)

    _t = time.time()
    if progress_cb: progress_cb("analyzing", "Running entity and graph analysis...")
    logger.info("STEP 4/7: Entity normalization (LLM call 1/4)")
    canonical_map = run_entity_normalization(documents, serp_data, llm_config)
    logger.info("STEP 4/7 done — %.1fs", time.time() - _t)

    _t = time.time()
    logger.info("STEP 5/7: Linguistic neutralization (LLM call 2/4)")
    neutralized = run_linguistic_neutralization(documents, llm_config)
    logger.info("STEP 5/7 done — %.1fs", time.time() - _t)

    _t = time.time()
    raw_texts = [d["raw_text_content"] for d in documents]
    logger.info("STEP 6/7: Graph extraction (LLM call 3/4, parallel)")
    all_graphs = extract_all_graphs(documents, neutralized, canonical_map, llm_config,
                                    progress_cb=progress_cb)
    logger.info("STEP 6/7 done — %.1fs", time.time() - _t)

    consensus_nodes = compute_consensus_baseline(all_graphs, canonical_map)

    analysis_degraded = not consensus_nodes

    omission_results = []
    for i, graph in enumerate(all_graphs):
        if graph.get("_parse_error"):
            omission_results.append((1.0, [], "HIGH"))
            continue
        source_nodes = set(graph.get("nodes", []))
        oi, missing = compute_omission_index(consensus_nodes, source_nodes, canonical_map)
        omission_results.append((oi, missing, omission_label(oi)))

    vf_scores, vf_labels = compute_framing_volatility(raw_texts, neutralized)

    _t = time.time()
    if progress_cb: progress_cb("synthesizing", "Generating forensic report...")
    logger.info("STEP 7/7: Forensic synthesis (LLM call 4/4)")
    pre_context = compute_pre_synthesis_context(
        all_graphs, raw_texts, canonical_map, consensus_nodes
    )

    context_bundle = {
        "consensus_nodes": list(consensus_nodes),
        "corpus_count": corp_count,
        "search_query": keyword,
        "per_source": [
            {
                "domain": g.get("_source_domain", ""),
                "name": g.get("_source_name", ""),
                "graph": g,
                "omission_index": omission_results[i][0] if i < len(omission_results) else 0.0,
                "omission_label": omission_results[i][2] if i < len(omission_results) else "LOW",
                "missing_nodes": omission_results[i][1] if i < len(omission_results) else [],
                "framing_volatility": vf_scores[i] if i < len(vf_scores) else 0.0,
                "framing_volatility_label": vf_labels[i] if i < len(vf_labels) else "MED",
                "raw_text": raw_texts[i] if i < len(raw_texts) else "",
                "neutralized_text": neutralized[i] if i < len(neutralized) else "",
            }
            for i, g in enumerate(all_graphs)
        ],
        "reputation_records": reputation_records,
        "narrative_clusters": pre_context["narrative_clusters"],
        "fracture_candidates": pre_context["fracture_candidates"],
        "term_shifts": pre_context["term_shifts"],
        "corpus_capped": manifest.get("corpus_capped", False),
    }

    if analysis_degraded:
        context_bundle["_degraded"] = "INSUFFICIENT_CONSENSUS"

    report = synthesize_forensic_report(context_bundle, llm_config)

    report = inject_labels(report)
    report.setdefault("event_meta", {}).update({
        "cluster_id": manifest.get("cluster_id", "unknown"),
        "search_query": manifest.get("search_query", ""),
        "industry_vertical": manifest.get("industry_vertical", "UNKNOWN"),
        "timestamp_utc": manifest.get("timestamp_utc", ""),
        "corpus_count": manifest.get("corpus_count", 0),
        "corpus_capped": manifest.get("corpus_capped", False),
    })

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
    logger.info("STEP 7/7 done — %.1fs", time.time() - _t)
    logger.info("Pipeline complete — total %.1fs", time.time() - _pipeline_start)

    return report
