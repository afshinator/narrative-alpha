"""Tests for synthesis context payload size optimization."""
import json


def test_compact_json_is_smaller_than_indented():
    """Removing indent=2 should produce measurably smaller JSON for same data."""
    bundle = {
        "consensus_nodes": ["node_a", "node_b"],
        "corpus_count": 2,
        "search_query": "test",
        "per_source": [
            {
                "domain": "example.com",
                "name": "Example",
                "graph": {"nodes": ["a", "b"], "edges": [{"source": "a", "target": "b", "relationship_verb": "relates"}]},
                "omission_index": 0.1,
                "omission_label": "LOW",
                "missing_nodes": [],
                "framing_volatility": 0.2,
                "framing_volatility_label": "LOW",
                "raw_text": "Some sample text for testing.",
                "neutralized_text": "Some sample text for testing.",
            }
        ],
        "reputation_records": {"example.com": {"rating_status": "STANDARD"}},
        "narrative_clusters": {},
        "fracture_candidates": [],
        "term_shifts": [],
        "corpus_capped": False,
    }

    compact = json.dumps(bundle, default=str)
    indented = json.dumps(bundle, indent=2, default=str)

    assert len(compact) < len(indented), "Compact JSON should be smaller than indented"


def test_fracture_candidates_capped_per_topic():
    """compute_pre_synthesis_context should cap fracture candidates per topic."""
    from narrative.analysis import compute_pre_synthesis_context

    consensus_node = "CLARITY_ACT"
    all_graphs = []
    for outlet_idx in range(5):
        edges = []
        for claim_idx in range(50):
            edges.append({
                "source": consensus_node,
                "target": f"claim_{claim_idx}",
                "relationship_verb": "relates_to",
            })
        all_graphs.append({
            "_source_domain": f"outlet{outlet_idx}.com",
            "_source_name": f"Outlet {outlet_idx}",
            "nodes": [consensus_node] + [f"claim_{i}" for i in range(50)],
            "edges": edges,
        })

    canonical_map = {}
    for n in [consensus_node] + [f"claim_{i}" for i in range(50)]:
        canonical_map[n.lower()] = n

    consensus_nodes = {consensus_node}

    result = compute_pre_synthesis_context(all_graphs, [], canonical_map, consensus_nodes)
    fractures = result["fracture_candidates"]

    assert len(fractures) <= 30, f"Expected ≤30 fractures, got {len(fractures)}"
