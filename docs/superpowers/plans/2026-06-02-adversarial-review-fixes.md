# Adversarial Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 issues found in adversarial review of synthesis context overflow changes: duplication bug in bundle serialization, coverage hole in compact JSON test, missing edge-case tests for fracture cap, cosmetic test data mismatch.

**Architecture:** Three independent fixes — (1) remove `fracture_candidates` from context bundle after enrichment to eliminate wasteful double-serialization, (2) add a real integration test that calls `synthesize_forensic_report` through the actual code path and verifies compact JSON output and key structure, (3) fill test coverage gaps for the fracture cap. Each fix has its own TDD cycle in the existing test files.

**Tech Stack:** Python 3.11, FastAPI, pytest, monkeypatch

**Pre-verification done (see agent session):**
- Confirmed `fracture_candidates` key persists in serialized bundle alongside `prepared_fractures` (717-char bundle: 120 chars duplicated)
- Confirmed `test_compact_json_is_smaller_than_indented` does NOT call `synthesize_forensic_report` — tests only Python stdlib `json.dumps` behavior
- Confirmed multi-topic fracture cap works (2 topics × 50 claims → 60 total, 30/topic) but untested
- Confirmed sub-cap case (10 claims → 30 pairs capped from 45) and 0/1 claim edges all work but untested
- Confirmed search_query `"bitcoin regulation test"` doesn't match test data about "The Clarity Act"

---

### Task 1: Remove fracture_candidates from bundle after enrichment

**Files:**
- Modify: `narrative/analysis.py:165`

**Context:** `synthesize_forensic_report` enriches raw `fracture_candidates` tuples into `prepared_fractures` dicts, but never removes the raw tuples from the bundle. The serialized payload then contains BOTH keys — doubling fracture data. The LLM schema only references the enriched `prepared_fractures` (via `reality_fractures`), so the raw tuples are dead weight.

- [ ] **Step 1: Write the failing test — add assertion to existing integration test**

In `tests/test_analysis.py`, add a new test method to the existing `TestSynthesizeForensicReport` class that verifies the bundle structure in the serialized prompt:

```python
    def test_prepared_fractures_replaces_raw_in_bundle(self, monkeypatch):
        """After enrichment, prepared_fractures appears but fracture_candidates is removed."""
        captured = {}

        def _capture(slot_cfg, messages, json_mode):
            captured["content"] = messages[1]["content"]
            return ('{"event_meta": {}, "consensus_reality_graph": {"consensus_summary":"",'
                    '"verified_anchor_nodes":[],"primary_verifications":[]}, '
                    '"distortion_matrix": [], "outlier_signals": [], '
                    '"reputation_warnings": [], "reality_divergence_zones": [], '
                    '"reality_fractures": [], "narrative_regime_shifts": []}')

        monkeypatch.setattr("narrative.llm_client.call_llm", _capture)

        bundle_with_fractures = {
            "fracture_candidates": [
                ("topic1", "claim A", ["outlet1.com"], "claim B", ["outlet2.com"]),
            ],
        }
        synthesize_forensic_report(
            bundle_with_fractures, {"call_4_forensic_synthesis": {}}
        )

        content = captured["content"]

        assert '"prepared_fractures"' in content, \
            "prepared_fractures should be present in serialized output"

        assert '"fracture_candidates"' not in content, \
            "fracture_candidates should be removed after enrichment"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analysis.py::TestSynthesizeForensicReport::test_prepared_fractures_replaces_raw_in_bundle -v`
Expected: FAIL with `"fracture_candidates should be removed after enrichment"` — the raw tuples are still present in the serialized output

- [ ] **Step 3: Implement the fix in synthesize_forensic_report**

In `narrative/analysis.py`, change line 165 from:
```python
        context_bundle = {**context_bundle, "prepared_fractures": enriched_fractures}
```
to:
```python
        context_bundle = {**context_bundle, "prepared_fractures": enriched_fractures}
        context_bundle.pop("fracture_candidates")
```

This removes `fracture_candidates` after creating `prepared_fractures`, preventing the key from appearing in the serialized JSON sent to the LLM.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_analysis.py::TestSynthesizeForensicReport::test_prepared_fractures_replaces_raw_in_bundle -v`
Expected: PASS

- [ ] **Step 5: Run all analysis tests to verify no regressions**

Run: `pytest tests/test_analysis.py -v 2>&1 | tail -10`
Expected: 85 passed (same as before)

- [ ] **Step 6 (optional): Commit**

```bash
git add narrative/analysis.py tests/test_analysis.py
git commit -m "fix: remove fracture_candidates from bundle after enrichment to avoid double serialization"
```

---

### Task 2: Fix coverage hole — verify compact JSON through actual code path

**Files:**
- Modify: `tests/test_analysis.py` (add to existing `TestSynthesizeForensicReport` class)
- Modify: `tests/test_synthesis_payload.py` (fix existing test)

**Context:** `test_compact_json_is_smaller_than_indented` only tests Python's stdlib `json.dumps` with a hand-rolled bundle — it never calls `synthesize_forensic_report`. If someone re-adds `indent=2` inside the function, the test won't catch it. We need a test that verifies compact JSON output through the actual code path.

- [ ] **Step 1: Write the failing test — add assertion to verify compact JSON from actual function**

In `tests/test_analysis.py`, add a new test method to `TestSynthesizeForensicReport`:

```python
    def test_serialized_bundle_uses_compact_json(self, monkeypatch):
        """The serialized context bundle sent to the LLM should not contain indentation."""
        captured = {}

        def _capture(slot_cfg, messages, json_mode):
            captured["content"] = messages[1]["content"]
            return ('{"event_meta": {}, "consensus_reality_graph": {"consensus_summary":"",'
                    '"verified_anchor_nodes":[],"primary_verifications":[]}, '
                    '"distortion_matrix": [], "outlier_signals": [], '
                    '"reputation_warnings": [], "reality_divergence_zones": [], '
                    '"reality_fractures": [], "narrative_regime_shifts": []}')

        monkeypatch.setattr("narrative.llm_client.call_llm", _capture)
        synthesize_forensic_report(
            {"key": "value"}, {"call_4_forensic_synthesis": {}}
        )

        content = captured["content"]

        # Compact JSON has no leading whitespace on lines (no \n followed by spaces)
        # Indented JSON would contain patterns like \n  "key"
        assert '\n ' not in content, \
            "Serialized content should use compact JSON, not indented"

        # Also verify it's valid JSON
        parsed = json.loads(content)
        assert parsed["key"] == "value"
```

- [ ] **Step 2: Run test to verify it passes** (the fix is already in place from the previous session)

Run: `pytest tests/test_analysis.py::TestSynthesizeForensicReport::test_serialized_bundle_uses_compact_json -v`
Expected: PASS (the `indent=2` was already removed)

- [ ] **Step 3: Fix the existing stdlib-only test to also verify through the actual function**

Replace the existing `test_compact_json_is_smaller_than_indented` in `tests/test_synthesis_payload.py` with a test that calls `synthesize_forensic_report` directly:

```python
def test_compact_json_via_synthesize_forensic_report():
    """Calling synthesize_forensic_report should produce compact JSON in the prompt."""
    import json
    import unittest.mock as mock

    captured = {}

    def _fake_llm(slot_cfg, messages, json_mode):
        captured["content"] = messages[1]["content"]
        return ('{"event_meta": {}, "consensus_reality_graph": {"consensus_summary":"",'
                '"verified_anchor_nodes":[],"primary_verifications":[]}, '
                '"distortion_matrix": [], "outlier_signals": [], '
                '"reputation_warnings": [], "reality_divergence_zones": [], '
                '"reality_fractures": [], "narrative_regime_shifts": []}')

    with mock.patch("narrative.analysis.call_llm", _fake_llm):
        from narrative.analysis import synthesize_forensic_report

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

        synthesize_forensic_report(bundle, {"call_4_forensic_synthesis": {}})

    content = captured["content"]

    assert '\n ' not in content, "Output should use compact JSON (no indentation)"

    # Verify the serialized bundle still contains expected keys
    parsed = json.loads(content)
    assert parsed["consensus_nodes"] == ["node_a", "node_b"]
    assert parsed["search_query"] == "test"
    assert "per_source" in parsed
```

- [ ] **Step 4: Run the updated test**

Run: `pytest tests/test_synthesis_payload.py::test_compact_json_via_synthesize_forensic_report -v`
Expected: PASS

- [ ] **Step 5: Run both test files to verify no regressions**

Run: `pytest tests/test_synthesis_payload.py tests/test_analysis.py -v 2>&1 | tail -15`
Expected: All tests pass

- [ ] **Step 6 (optional): Commit**

```bash
git add tests/test_synthesis_payload.py tests/test_analysis.py
git commit -m "test: add integration test verifying compact JSON through synthesize_forensic_report"
```

---

### Task 3: Add missing edge-case tests for fracture cap

**Files:**
- Modify: `tests/test_synthesis_payload.py`

**Context:** The fracture cap test only covers the single-topic >30 case. Multi-topic, sub-cap (where all pairs pass through), and edge cases (0, 1 claims) are uncovered.

- [ ] **Step 1: Write the failing tests — add 3 new test functions**

Add these tests to `tests/test_synthesis_payload.py`:

```python
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

    # C(5,2) = 10 pairs, all should pass through since 10 < 30
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
```

- [ ] **Step 2: Run all fracture cap tests to verify they pass**

Run: `pytest tests/test_synthesis_payload.py::test_fracture_candidates_multi_topic tests/test_synthesis_payload.py::test_fracture_candidates_below_cap_pass_through tests/test_synthesis_payload.py::test_fracture_candidates_edge_zero_and_one_claims -v`
Expected: All 3 PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/test_synthesis_payload.py tests/test_analysis.py -v 2>&1 | tail -25`
Expected: All tests pass

- [ ] **Step 4 (optional): Commit**

```bash
git add tests/test_synthesis_payload.py
git commit -m "test: add edge-case tests for fracture cap (multi-topic, sub-cap, zero/one claims)"
```

---

### Task 4: Fix search_query mismatch in worst-case regression test

**Files:**
- Modify: `tests/test_synthesis_payload.py:128`

**Context:** The worst-case payload test generates articles about "The Clarity Act" (a bitcoin regulation bill) but uses `search_query: "bitcoin regulation test"`. While functionally harmless, this is confusing and could mask a bug if someone later adds logic that reads `search_query` from the data.

- [ ] **Step 1: Fix the mismatch — change search_query to match test data**

In `tests/test_synthesis_payload.py`, change line 128:
```python
        "search_query": "bitcoin regulation test",
```
to:
```python
        "search_query": "Clarity Act",
```

- [ ] **Step 2: Run the test to verify it still passes**

Run: `pytest tests/test_synthesis_payload.py::test_worst_case_payload_fits_within_token_limit -v`
Expected: PASS (search_query doesn't affect token counting)

- [ ] **Step 3 (optional): Commit**

```bash
git add tests/test_synthesis_payload.py
git commit -m "chore: fix search_query to match test data in worst-case payload test"
```

---

### Self-Review

**1. Spec coverage:**
- Task 1: Remove `fracture_candidates` from bundle after enrichment ✅
- Task 2: Fix coverage hole — test compact JSON through `synthesize_forensic_report` ✅
- Task 3: Add edge-case tests for fracture cap (multi-topic, sub-cap, 0/1) ✅
- Task 4: Fix search_query mismatch in worst-case test ✅

**2. Placeholder scan:** No TBDs, no TODOs, no "handle edge cases" without code. All code blocks complete and runnable. File paths exact.

**3. Type consistency:** All functions referenced (`synthesize_forensic_report`, `compute_pre_synthesis_context`, `call_llm`) have the same signatures as the existing codebase. Test method names follow the existing `TestSynthesizeForensicReport` pattern. No type mismatches.
