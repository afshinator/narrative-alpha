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
