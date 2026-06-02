"""Tests for synthesis context payload size optimization."""
import json

import tiktoken


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


def test_fracture_candidates_multi_topic():
    """Multiple topics should each be capped at 30 pairs independently."""
    from narrative.analysis import compute_pre_synthesis_context

    all_graphs = []
    for outlet_idx in range(3):
        edges = []
        for t in range(2):
            for c in range(50):
                edges.append({"source": f"TOPIC_{t}", "target": f"claim_{t}_{c}", "relationship_verb": "rel"})
        all_graphs.append({
            "_source_domain": f"outlet{outlet_idx}.com",
            "_source_name": "",
            "nodes": [f"TOPIC_{t}" for t in range(2)] + [f"claim_{t}_{c}" for t in range(2) for c in range(50)],
            "edges": edges,
        })

    canon_map = {}
    for t in range(2):
        canon_map[f"topic_{t}"] = f"TOPIC_{t}"
        for c in range(50):
            canon_map[f"claim_{t}_{c}".lower()] = f"claim_{t}_{c}"
    consensus = {f"TOPIC_{t}" for t in range(2)}

    result = compute_pre_synthesis_context(all_graphs, [], canon_map, consensus)
    fractures = result["fracture_candidates"]

    from collections import Counter
    topic_counts = Counter(t for t, _, _, _, _ in fractures)

    assert len(topic_counts) == 2, f"Expected 2 topics, got {len(topic_counts)}"
    for topic, count in topic_counts.items():
        assert count == 30, f"Topic '{topic}' has {count} pairs, expected 30"
    assert len(fractures) == 60, f"Expected 60 total, got {len(fractures)}"


def test_fracture_candidates_below_cap_pass_through():
    """With fewer claims than the cap threshold, all pairs should pass through."""
    from narrative.analysis import compute_pre_synthesis_context

    all_graphs = []
    for outlet_idx in range(3):
        edges = [{"source": "TOPIC", "target": f"claim_{c}", "relationship_verb": "rel"} for c in range(5)]
        all_graphs.append({
            "_source_domain": f"outlet{outlet_idx}.com",
            "_source_name": "",
            "nodes": ["TOPIC"] + [f"claim_{c}" for c in range(5)],
            "edges": edges,
        })

    canon_map = {}
    for c in range(5):
        canon_map[f"claim_{c}".lower()] = f"claim_{c}"
    canon_map["topic"] = "TOPIC"
    consensus = {"TOPIC"}

    result = compute_pre_synthesis_context(all_graphs, [], canon_map, consensus)
    fractures = result["fracture_candidates"]

    assert len(fractures) == 10, f"Expected 10 pairs (C(5,2)), got {len(fractures)}"


def test_fracture_candidates_edge_zero_and_one_claims():
    """With 0 or 1 unique claims, no fracture candidates should be generated."""
    from narrative.analysis import compute_pre_synthesis_context

    for n in [0, 1]:
        all_graphs = []
        for outlet_idx in range(2):
            edges = [{"source": "TOPIC", "target": f"claim_{c}", "relationship_verb": "rel"} for c in range(n)]
            all_graphs.append({
                "_source_domain": f"outlet{outlet_idx}.com",
                "_source_name": "",
                "nodes": ["TOPIC"] + [f"claim_{c}" for c in range(n)],
                "edges": edges,
            })

        canon_map = {}
        for c in range(n):
            canon_map[f"claim_{c}".lower()] = f"claim_{c}"
        canon_map["topic"] = "TOPIC"
        consensus = {"TOPIC"}

        result = compute_pre_synthesis_context(all_graphs, [], canon_map, consensus)
        assert len(result["fracture_candidates"]) == 0, \
            f"Expected 0 fractures for {n} claim(s), got {len(result['fracture_candidates'])}"


def test_worst_case_payload_fits_within_token_limit():
    """Verify a realistic worst-case synthesis payload is under 80% of the token limit."""
    # DeepSeek V4 Pro context window (from API error: "maximum context length is 1048565 tokens")
    LIMIT = 1048565
    SAFETY_MARGIN = 0.80

    MAX_ARTICLES = 20
    MAX_TOPICS = 10
    MAX_CLAIMS = 40

    from narrative.analysis import compute_pre_synthesis_context

    all_graphs = []
    consensus_nodes = set()
    raw_texts = []
    neutralized_texts = []
    canonical_map = {}

    for i in range(MAX_ARTICLES):
        nodes = [f"topic_{t}" for t in range(MAX_TOPICS)]
        edges = []
        for t in range(MAX_TOPICS):
            for c in range(MAX_CLAIMS):
                claim = f"claim_{t}_{c}"
                nodes.append(claim)
                edges.append({
                    "source": f"topic_{t}",
                    "target": claim,
                    "relationship_verb": "relates_to",
                })
            consensus_nodes.add(f"topic_{t}")

        graph = {
            "_source_domain": f"outlet{i}.com",
            "_source_name": f"Outlet {i}",
            "nodes": nodes,
            "edges": edges,
        }
        all_graphs.append(graph)

        text = "The Clarity Act advanced through the Senate Banking Committee. " * 500
        raw_texts.append(text[:15000])
        neutralized_texts.append(text[:5000])

    for graph in all_graphs:
        for node in graph.get("nodes", []):
            canonical_map[node.lower()] = node

    pre_context = compute_pre_synthesis_context(
        all_graphs, raw_texts, canonical_map, consensus_nodes
    )

    context_bundle = {
        "consensus_nodes": list(consensus_nodes),
        "corpus_count": MAX_ARTICLES,
        "search_query": "Clarity Act",
        "per_source": [
            {
                "domain": g.get("_source_domain", ""),
                "name": g.get("_source_name", ""),
                "graph": g,
                "omission_index": 0.15,
                "omission_label": "LOW",
                "missing_nodes": [],
                "framing_volatility": 0.1,
                "framing_volatility_label": "LOW",
                "raw_text": t[:5000],
                "neutralized_text": n[:5000],
            }
            for g, t, n in zip(all_graphs, raw_texts, neutralized_texts)
        ],
        "reputation_records": {f"outlet{i}.com": {"rating_status": "STANDARD"} for i in range(MAX_ARTICLES)},
        "narrative_clusters": pre_context["narrative_clusters"],
        "fracture_candidates": pre_context["fracture_candidates"],
        "term_shifts": pre_context["term_shifts"],
        "corpus_capped": False,
    }

    payload = json.dumps(context_bundle, default=str)
    enc = tiktoken.get_encoding("cl100k_base")
    token_count = len(enc.encode(payload))

    max_allowed = int(LIMIT * SAFETY_MARGIN)
    assert token_count <= max_allowed, (
        f"Payload is {token_count:,} tokens, exceeds {SAFETY_MARGIN*100:.0f}% "
        f"limit of {max_allowed:,} tokens"
    )
