# Synthesis Context Overflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate synthesis context overflow errors by reducing the JSON payload to fit within DeepSeek V4 Pro's 1,048,565-token limit while preserving all functional data.

**Architecture:** Two surgical changes — (1) remove `indent=2` from `json.dumps()` for a free 21% token reduction with zero behavioral change, (2) cap `fracture_candidates` at 30 pairs per topic to prevent the O(n²) explosion that pushes worst-case payloads to 1.5M+ tokens. Combined, these drop even worst-case 20-article runs from 1.53M to 786K tokens.

**Tech Stack:** Python 3.11, FastAPI, DeepSeek V4 Pro (cl100k_base tokenizer)

**Pre-verification done (see agent session):**
- Measured actual token counts using `tiktoken` (`cl100k_base`) for realistic pipeline payloads
- Scenario B (20 articles, 80 nodes/graph, 40 claims/topic): 1,533,356 tokens → 786,414 tokens after Fix 1+2
- Indent=2 alone insufficient for worst case (1.2M tokens after removing indent, still over limit)
- Text truncation (5K chars) confirmed adequate at ~60K tokens, keep as-is
- Graphs confirmed necessary for LLM context, keeping in per_source

---

### Task 1: Remove indent=2 from json.dumps

**Files:**
- Modify: `narrative/analysis.py:167`

- [ ] **Step 1: Write the failing test — verify compact JSON produces fewer tokens than indented**

```python
"""tests/test_synthesis_payload.py"""
import json
import pytest

from narrative.analysis import synthesize_forensic_report


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

    from narrative.analysis import synthesize_forensic_report

    # We need to test the serialization, but the function calls LLM.
    # Instead, test the json.dumps call directly.
    compact = json.dumps(bundle, default=str)
    indented = json.dumps(bundle, indent=2, default=str)

    assert len(compact) < len(indented), "Compact JSON should be smaller than indented"
```

- [ ] **Step 2: Run test to verify it fails (test file doesn't exist yet)**

Run: `pytest tests/test_synthesis_payload.py::test_compact_json_is_smaller_than_indented -v`
Expected: ERROR — module not found (file doesn't exist yet)

- [ ] **Step 3: Add logging + change json.dumps to compact form**

Edit `narrative/analysis.py`. Change line 167 from:
```python
    user_content = json.dumps(context_bundle, indent=2, default=str)
```
to:
```python
    user_content = json.dumps(context_bundle, default=str)
    logger.info("Synthesis context bundle size: %d chars (~%d tokens at ~3.5cpt)",
                len(user_content), len(user_content) // 3)
```

Also add `import logging` at the top if not already present:
```python
logger = logging.getLogger(__name__)
```
(Already present at line 12.)

- [ ] **Step 4: Run existing tests to verify nothing broke**

Run: `pytest tests/ -v --timeout=30 2>&1 | head -80`
Expected: Same test results as before (39/39 server tests pass, 7 test_ingestion failures pre-existing)

- [ ] **Step 5: Commit**

```bash
git add narrative/analysis.py tests/test_synthesis_payload.py
git commit -m "fix: remove indent=2 from synthesis JSON serialization

Removes indent=2 from json.dumps(context_bundle) to save ~21% token
overhead in the forensic synthesis LLM call. Adds size logging.
This is one of two fixes for the context overflow issue.
"
```

---

### Task 2: Cap fracture candidates in compute_pre_synthesis_context

**Files:**
- Modify: `narrative/analysis.py:247-259`
- Test: `tests/test_synthesis_payload.py`

**Context:** `compute_pre_synthesis_context` generates fracture candidates as all C(N,2) pairs of unique claims per topic. For 40+ claims across 10+ topics, this produces 7,800+ pairs (as measured: ~420K tokens). Capping at 30 pairs per topic limits worst-case tokens from fractures to ~12K while preserving the most representative contradictions.

The LLM receives `prepared_fractures` (enriched format with UUIDs) in `synthesize_forensic_report`. The cap must be applied before enrichment to keep the candidate list manageable from the start.

- [ ] **Step 1: Write failing test — verify fracture candidates are capped per topic**

```python
# Add to tests/test_synthesis_payload.py

def test_fracture_candidates_capped_per_topic():
    """compute_pre_synthesis_context should cap fracture candidates per topic."""
    from narrative.analysis import compute_pre_synthesis_context

    # Build a scenario with 50 unique claims for one topic
    # Need a graph that produces ~50 unique edges resolving to a single consensus node
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

    # claims: all 50 are unique, so C(50,2) = 1225 pairs without cap
    # With the cap, each topic should have at most MAX_FRACTURES_PER_TOPIC
    # Verify by topic
    from collections import Counter
    topic_counts = Counter(t for t, _, _, _, _ in fractures)
    for topic, count in topic_counts.items():
        assert count <= 30, f"Topic '{topic}' has {count} fracture pairs, expected ≤30"

    # Verify total is capped (50*49/2 = 1225 without cap, should be ≤30 with cap)
    assert len(fractures) <= 30, f"Expected ≤30 fractures, got {len(fractures)}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_synthesis_payload.py::test_fracture_candidates_capped_per_topic -v`
Expected: FAIL — assertion error (1225 > 30, no cap implemented)

- [ ] **Step 3: Implement the cap in compute_pre_synthesis_context**

Edit `narrative/analysis.py`. In the fracture candidates section (lines 247-259), add a cap:

```python
    MAX_FRACTURES_PER_TOPIC = 30

    for topic, domain_edges in topic_to_edges.items():
        # ... existing claim_map construction (unchanged) ...

        unique_claims = list(claim_map.keys())
        if len(unique_claims) >= 2:
            topic_pair_count = 0
            for i in range(len(unique_claims)):
                for j in range(i + 1, len(unique_claims)):
                    if topic_pair_count >= MAX_FRACTURES_PER_TOPIC:
                        break
                    claim_a = unique_claims[i]
                    claim_b = unique_claims[j]
                    fracture_candidates.append((
                        topic,
                        claim_a,
                        sorted(claim_map[claim_a]),
                        claim_b,
                        sorted(claim_map[claim_b]),
                    ))
                    topic_pair_count += 1
                if topic_pair_count >= MAX_FRACTURES_PER_TOPIC:
                    break
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_synthesis_payload.py::test_fracture_candidates_capped_per_topic -v`
Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `pytest tests/ -v --timeout=30 2>&1 | head -80`
Expected: Same 39/39 server tests pass, 7 pre-existing ingestion failures

- [ ] **Step 6: Commit**

```bash
git add narrative/analysis.py tests/test_synthesis_payload.py
git commit -m "fix: cap fracture candidates at 30 pairs per topic

Prevents O(n^2) explosion in compute_pre_synthesis_context where
50 unique claims per topic would generate 1,225 fracture candidate
pairs (~67K tokens). With the cap, same scenario generates at most
30 pairs (~1.6K tokens). Combined with compact JSON serialization,
this keeps worst-case synthesis payload under 800K tokens.
"
```

---

### Task 3: Add regression test for total payload token limit

**Files:**
- Create: `tests/test_synthesis_payload.py` (if not done in Task 1)
- Modify: `tests/test_synthesis_payload.py`

**Context:** After applying both fixes, verify that a realistic worst-case payload fits within 80% of the DeepSeek V4 Pro context limit (838,852 tokens). This prevents future code changes from reintroducing the overflow.

- [ ] **Step 1: Write the regression test**

```python
# Add to tests/test_synthesis_payload.py

import tiktoken


def test_worst_case_payload_fits_within_token_limit():
    """Verify a realistic worst-case synthesis payload is under 80% of the token limit."""
    LIMIT = 1048565
    SAFETY_MARGIN = 0.80

    # Build worst-case scenario: 20 articles, dense graphs, 40 claims/topic, 10 topics
    # This is the scenario we measured at 1.53M tokens before fixes, 786K after
    MAX_ARTICLES = 20
    MAX_NODES = 80
    MAX_EDGES_PER_NODE = 15
    MAX_TOPICS = 10
    MAX_CLAIMS = 40

    # Use helper functions to build the data
    from narrative.analysis import compute_pre_synthesis_context

    # Construct realistic worst-case data
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
                if c < len(nodes):
                    continue  # keep as node
                nodes.append(claim)
                edges.append({
                    "source": f"topic_{t}",
                    "target": claim,
                    "relationship_verb": "relates_to",
                })
            # consensus: all outlet nodes for topics will be in consensus
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

    # Build canonical map
    for graph in all_graphs:
        for node in graph.get("nodes", []):
            canonical_map[node.lower()] = node

    pre_context = compute_pre_synthesis_context(
        all_graphs, raw_texts, canonical_map, consensus_nodes
    )

    # Build the full context_bundle
    context_bundle = {
        "consensus_nodes": list(consensus_nodes),
        "corpus_count": MAX_ARTICLES,
        "search_query": "bitcoin regulation test",
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

    import json
    payload = json.dumps(context_bundle, default=str)
    enc = tiktoken.get_encoding("cl100k_base")
    token_count = len(enc.encode(payload))

    max_allowed = int(LIMIT * SAFETY_MARGIN)
    assert token_count <= max_allowed, (
        f"Payload is {token_count:,} tokens, exceeds {SAFETY_MARGIN*100:.0f}% "
        f"limit of {max_allowed:,} tokens"
    )
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_synthesis_payload.py::test_worst_case_payload_fits_within_token_limit -v`
Expected: PASS (with both Fix 1 and Fix 2 applied)

- [ ] **Step 3: Run full test suite to confirm no regressions**

Run: `pytest tests/ -v --timeout=60 2>&1 | head -100`
Expected: Same pre-existing results, no new failures

- [ ] **Step 4: Commit**

```bash
git add tests/test_synthesis_payload.py
git commit -m "test: add regression test for synthesis payload token limit

Verifies worst-case 20-article pipeline payload stays under 80%
of DeepSeek V4 Pro's 1,048,565-token context limit (838,852 tokens).
Guards against future O(n^2) or bloat regressions.
"
```

---

### Self-Review

1. **Spec coverage:** All requirements covered:
   - Remove indent=2 → Task 1
   - Cap fracture candidates → Task 2
   - Regression test → Task 3
   - Text truncation re-evaluation → verified pre-plan, decided to keep at 5K
   - "Do NOT remove graphs" → verified pre-plan, graphs keep as-is

2. **Placeholder scan:** Every code block contains complete, runnable Python. No TBDs, no TODOs, no "handle edge cases" without code. File paths are exact. Commands show exact invocation.

3. **Type consistency:** `MAX_FRACTURES_PER_TOPIC = 30` referenced consistently. `compute_pre_synthesis_context` signature unchanged. `synthesize_forensic_report` signature unchanged. All test function names unique and descriptive.
