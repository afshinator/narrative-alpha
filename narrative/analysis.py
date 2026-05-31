"""Layer 3: Analysis — graph extraction, forensic synthesis, metric computation.

Vf (framing volatility) lives here — not in processing.py — per spec Section 2
decoupling rule: Layer 2 contains zero analysis logic.
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

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
    slot_cfg = llm_config["call_3_graph_extraction"]
    from narrative.llm_client import call_llm

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
    progress_cb=None,
) -> list[dict]:
    total = len(documents)

    def _extract_one(doc: dict, neut_text: str, idx: int) -> dict:
        _t = time.time()
        source_name = doc.get("source_name", "") or doc.get("source_domain", "unknown")
        count_str = f" ({idx + 1}/{total})" if total else ""
        try:
            graph = extract_graph(neut_text, canonical_map, llm_config)
            graph["_source_domain"] = doc.get("source_domain", "unknown")
            graph["_source_name"] = doc.get("source_name", "")
            logger.info("Doc %d graph extraction done — %.1fs", idx, time.time() - _t)
            return graph
        except Exception:
            logger.warning("Doc %d graph extraction failed — %.1fs", idx, time.time() - _t)
            return {
                "_source_domain": doc.get("source_domain", "unknown"),
                "_source_name": doc.get("source_name", ""),
                "_parse_error": True,
                "nodes": [],
                "edges": [],
            }
        finally:
            if progress_cb:
                progress_cb("analyzing", f"Graph extraction — {source_name}{count_str}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(_extract_one, doc, neut, i)
            for i, (doc, neut) in enumerate(zip(documents, neutralized_texts))
        ]
        results = [f.result() for f in futures]
        logger.info("All %d graph extractions collected", len(results))
        return results


def compute_framing_volatility(
    raw_texts: list[str],
    neutralized_texts: list[str],
) -> tuple[list[float], list[str]]:
    import numpy as np
    from narrative.llm_client import get_embedding

    def _embed_and_compare(raw: str, neut: str) -> tuple[float, str]:
        e_raw = np.array(get_embedding(raw))
        e_neut = np.array(get_embedding(neut))
        norm_product = np.linalg.norm(e_raw) * np.linalg.norm(e_neut)
        cos_sim = float(np.dot(e_raw, e_neut) / norm_product) if norm_product > 0 else 0.0
        vf = 1.0 - cos_sim
        return round(vf, 4), framing_volatility_label(vf)

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(
            executor.map(
                lambda pair: _embed_and_compare(pair[0], pair[1]),
                zip(raw_texts, neutralized_texts),
            )
        )

    scores = [r[0] for r in results]
    labels = [r[1] for r in results]
    return scores, labels


FORENSIC_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a forensic narrative analysis engine. Your task is to analyze HOW reality "
    "is being described across institutional media sources — not to determine which "
    "description is objectively correct. You map narrative topology: what all outlets "
    "agree on, who omitted which facts, who used linguistic camouflage, and which "
    "single-source outlier claims exist. "
    "Your output must reflect narrative structure, not truth arbitration. "
    "Output only valid JSON. The word 'json' must appear in your response.\n\n"
     "IMPORTANT: Use the cluster_id, search_query, industry_vertical, timestamp_utc, and corpus_count "
     "directly from the input context data — do not invent them.\n\n"
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
    import uuid as _uuid
    from narrative.llm_client import call_llm

    slot_cfg = llm_config["call_4_forensic_synthesis"]

    if "fracture_candidates" in context_bundle:
        enriched_fractures = []
        for topic, claim_a, outlets_a, claim_b, outlets_b in context_bundle.get("fracture_candidates", []):
            enriched_fractures.append({
                "fracture_id": str(_uuid.uuid4()),
                "topic": topic,
                "claim_a": {"statement": claim_a, "supporting_outlets": outlets_a},
                "claim_b": {"statement": claim_b, "supporting_outlets": outlets_b},
                "relationship": "STRUCTURALLY_CONTRADICTORY",
                "resolution_status": "UNRESOLVED",
            })
        context_bundle = {**context_bundle, "prepared_fractures": enriched_fractures}

    user_content = json.dumps(context_bundle, indent=2, default=str)

    messages = [
        {"role": "system", "content": FORENSIC_SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    raw = call_llm(slot_cfg, messages, json_mode=True)
    return json.loads(raw)


def inject_labels(report: dict) -> dict:
    for entry in report.get("distortion_matrix", []):
        entry["omission_label"] = omission_label(entry.get("omission_index", 0))
        entry["framing_volatility_label"] = framing_volatility_label(
            entry.get("framing_volatility_score", 0)
        )

    for signal in report.get("outlier_signals", []):
        prov = signal.get("outlier_origin_provenance", {})
        sa = prov.get("scatter_shot_anomaly_factor", 0)
        prov["scatter_shot_label"] = scatter_shot_label(sa)

    for warning in report.get("reputation_warnings", []):
        sa = warning.get("scatter_shot_anomaly_factor", 0)
        warning["scatter_shot_label"] = scatter_shot_label(sa)

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
        fracture.setdefault("classification_method", "LLM_ASSISTED")

    return report


def compute_pre_synthesis_context(
    all_source_graphs: list[dict],
    raw_texts: list[str],
    canonical_map: dict[str, str],
    consensus_nodes: set[str],
) -> dict:
    narrative_clusters: dict[str, dict[str, list[str]]] = {}
    fracture_candidates: list[tuple[str, str, list[str], str, list[str]]] = []
    term_shifts: list[dict] = []

    topic_to_edges: dict[str, dict[str, list[tuple[str, str, str]]]] = {}

    for graph in all_source_graphs:
        if graph.get("_parse_error"):
            continue
        domain = graph.get("_source_domain", "unknown")
        for edge in graph.get("edges", []):
            source = edge.get("source", "")
            target = edge.get("target", "")
            verb = edge.get("relationship_verb", "")
            canonical_source = resolve_to_canonical(source, canonical_map)
            if canonical_source in consensus_nodes:
                topic_to_edges.setdefault(canonical_source, {})
                topic_to_edges[canonical_source].setdefault(domain, [])
                topic_to_edges[canonical_source][domain].append((target, verb, source))

    for topic, domain_edges in topic_to_edges.items():
        claim_map: dict[str, list[str]] = {}
        for domain, edges in domain_edges.items():
            for target, verb, raw_source in edges:
                claim_text = f"{target} ({verb})"
                claim_map.setdefault(claim_text, [])
                if domain not in claim_map[claim_text]:
                    claim_map[claim_text].append(domain)
        narrative_clusters[topic] = claim_map

        unique_claims = list(claim_map.keys())
        if len(unique_claims) >= 2:
            for i in range(len(unique_claims)):
                for j in range(i + 1, len(unique_claims)):
                    claim_a = unique_claims[i]
                    claim_b = unique_claims[j]
                    fracture_candidates.append((
                        topic,
                        claim_a,
                        sorted(claim_map[claim_a]),
                        claim_b,
                        sorted(claim_map[claim_b]),
                    ))

    if raw_texts:
        total_sources = len(raw_texts)
        canonical_to_forms: dict[str, dict[str, int]] = {}
        for surface_form, canonical_target in canonical_map.items():
            count = sum(1 for text in raw_texts if surface_form.lower() in text.lower())
            if count > 0:
                canonical_to_forms.setdefault(canonical_target, {})
                canonical_to_forms[canonical_target][surface_form] = count

        for canonical_target, form_counts in canonical_to_forms.items():
            sorted_forms = sorted(form_counts.items(), key=lambda x: -x[1])
            dominant_form, dominant_count = sorted_forms[0]
            all_forms_for_target = {
                f for f, c in canonical_map.items() if c == canonical_target
            }
            # Threshold ≥0.35 aligns with the MED label boundary (§5.7).
            # Shifts below this are LOW-confidence noise; Call 4 would label
            # them LOW anyway.
            if dominant_count / total_sources >= 0.35 and len(all_forms_for_target) >= 2:
                alternative_forms = all_forms_for_target - {dominant_form}
                previous_term = min(alternative_forms, key=lambda f: form_counts.get(f, 0))
                term_shifts.append({
                    "previous_term": previous_term,
                    "replacement_term": dominant_form,
                    "observed_across": dominant_count,
                    "total_sources": total_sources,
                })

    return {
        "narrative_clusters": narrative_clusters,
        "fracture_candidates": fracture_candidates,
        "term_shifts": term_shifts,
    }


def resolve_to_canonical(node: str | int, canonical_map: dict[str, str]) -> str:
    """Map a surface-form node string to its canonical identity."""
    key = str(node).strip().lower()
    return canonical_map.get(key, str(node))


def omission_label(oi: float) -> str:
    if oi < 0.25:
        return "LOW"
    elif oi < 0.50:
        return "MED"
    else:
        return "HIGH"


def framing_volatility_label(vf: float | None) -> str:
    vf = vf if vf is not None else 0.0
    if vf < 0.25:
        return "LOW"
    elif vf < 0.55:
        return "MED"
    else:
        return "HIGH"


def scatter_shot_label(sa: float | None) -> str:
    sa = sa if sa is not None else 0.0
    if sa < 0.35:
        return "LOW"
    elif sa < 0.60:
        return "MED"
    else:
        return "HIGH"


def compute_consensus_stability(
    observed_narratives: dict[str, int],
    total_sources: int,
) -> float:
    distinct = len(observed_narratives)
    if total_sources == 0:
        return 0.0
    score = 1.0 - ((distinct - 1) / total_sources)
    return round(max(0.0, min(1.0, score)), 4)


def compute_sa_for_outlet(
    domain: str,
    decayed_count: int,
    total_produced: int,
) -> tuple[float, str]:
    if total_produced == 0:
        return 0.0, "LOW"
    sa = decayed_count / total_produced
    return round(sa, 4), scatter_shot_label(sa)


def compute_consensus_baseline(
    all_graphs: list[dict],
    canonical_map: dict[str, str],
    consensus_ratio: float = 0.60,
) -> set[str]:
    n = sum(1 for g in all_graphs if not g.get("_parse_error"))
    if n < 5:
        return set()

    threshold = int(consensus_ratio * n) + 1

    node_source_counts: dict[str, set[str]] = {}
    for graph in all_graphs:
        if graph.get("_parse_error"):
            continue
        domain = graph.get("_source_domain", "unknown")
        for node in graph.get("nodes", []):
            canonical = resolve_to_canonical(node, canonical_map)
            node_source_counts.setdefault(canonical, set()).add(domain)

    return {
        node
        for node, sources in node_source_counts.items()
        if len(sources) >= threshold
    }


def compute_omission_index(
    consensus_nodes: set[str],
    source_nodes: set[str],
    canonical_map: dict[str, str],
) -> tuple[float, list[str]]:
    canonical_consensus = {resolve_to_canonical(n, canonical_map) for n in consensus_nodes}
    canonical_source = {resolve_to_canonical(n, canonical_map) for n in source_nodes}
    missing = canonical_consensus - canonical_source

    if len(canonical_consensus) == 0:
        return 0.0, []

    omission = len(missing) / len(canonical_consensus)
    return round(omission, 4), list(missing)


def sync_label(score: float | None) -> str:
    score = score if score is not None else 0.0
    if score >= 0.65:
        return "HIGH"
    elif score >= 0.35:
        return "MED"
    else:
        return "LOW"
