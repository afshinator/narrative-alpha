"""Modal orchestration — single-entry-point forensic pipeline + settings."""

import os
import json
import modal

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


# ── Core pipeline logic (testable without Modal runtime) ──

def _run_pipeline(
    keyword: str,
    vertical: str,
    api_key: str,
    unlocker_zone: str,
    db_path: str,
) -> dict:
    """
    Execute the full forensic pipeline synchronously.

    All dependencies are parameterized so this function can be tested
    by mocking the narrative module imports, without requiring a Modal
    container or live API keys.

    Execution order (14 steps, see Section 8):
    1.  SERP API → discover articles
    2.  Web Unlocker → fetch article bodies + log all attempts
    3.  Corpus floor gate (min 5 unique source domains)
    4.  Outlet reputation check (UNRATED + spawn back-test if new)
    5.  Call 1: entity normalization → canonical_map
    6.  Call 2: linguistic neutralization per article
    7.  Call 3: graph extraction per source
    8.  Python: resolve nodes → Gc → Oi per source
    9.  Vf: embed raw + neutralized texts → cosine distances
    10. Pre-synthesis: narrative clusters, fractures, term shifts
    11. Call 4: forensic synthesis → Contract B JSON
    12. Python: inject labels via threshold rules
    13. Write outlier signals to SQLite
    14. Return report
    """
    llm_config = load_llm_config()

    # ── Step 1-2: Ingestion + ingestion log ──
    db_conn = get_hardened_db_connection(db_path)
    serp_data = discover_articles(keyword, api_key)
    manifest = build_ingestion_manifest(
        keyword, serp_data, unlocker_zone, api_key,
        db_conn=db_conn,
        logger_func=write_ingestion_log,
    )

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

    analysis_degraded = not consensus_nodes

    omission_results = []
    for i, graph in enumerate(all_graphs):
        if graph.get("_parse_error"):
            omission_results.append((1.0, [], "HIGH"))
            continue
        source_nodes = set(graph.get("nodes", []))
        oi, missing = compute_omission_index(consensus_nodes, source_nodes, canonical_map)
        omission_results.append((oi, missing, omission_label(oi)))

    # ── Step 9: Vf — Framing volatility ──
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

    return report


# ── Main endpoint ──

@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
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

    if not api_key or not unlocker_zone:
        return {"status": "ERROR", "error": "BRIGHTDATA_API_KEY and BRIGHTDATA_UNLOCKER_ZONE must be set"}

    db_path = os.path.join(
        os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha"),
        "outlet_reputation.db",
    )

    report = _run_pipeline(keyword, vertical, api_key, unlocker_zone, db_path)
    vol.commit()
    return report


# ── Settings endpoint ──

@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
)
@modal.fastapi_endpoint(method="POST")
async def update_llm_config(payload: dict) -> dict:
    """
    Accepts updated llm_config.json from settings UI.
    Validates required slots + slot structure via LLMConfig model, writes to volume, commits.

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

    from narrative.contracts import LLMConfig

    try:
        LLMConfig(**payload)
    except Exception as e:
        return {"error": f"Invalid config: {e}"}

    config_path = os.path.join(
        os.environ.get("NARRATIVE_ALPHA_ROOT", "/root/.narrative_alpha"),
        "llm_config.json",
    )
    with open(config_path, "w") as f:
        json.dump(payload, f, indent=2)
    vol.commit()

    return {"status": "ok", "config": payload}


# ── Background back-test Modal function (Section 7) ──

@app.function(
    image=image_recipe,
    volumes={"/root/.narrative_alpha": vol},
    secrets=[modal.Secret.from_dotenv(".env.production")],
    timeout=600,
)
def run_historical_backtest(domain: str, vertical: str) -> None:
    """
    Non-blocking background task. Runs after main pipeline returns.
    Imports execute_historical_backtest from narrative.backtest.
    On completion: writes reputation metrics to SQLite and commits volume.
    """
    from narrative.backtest import execute_historical_backtest

    execute_historical_backtest(domain, vertical)
    vol.commit()
