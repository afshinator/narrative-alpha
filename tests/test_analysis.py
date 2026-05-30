"""Tests for narrative/analysis.py — Layer 3: Graph extraction, metrics, synthesis."""

import json

import pytest

from narrative.analysis import (
    compute_consensus_baseline,
    compute_consensus_stability,
    compute_framing_volatility,
    compute_omission_index,
    compute_pre_synthesis_context,
    compute_sa_for_outlet,
    extract_all_graphs,
    extract_graph,
    framing_volatility_label,
    inject_labels,
    omission_label,
    resolve_to_canonical,
    scatter_shot_label,
    sync_label,
    synthesize_forensic_report,
)


class TestResolveToCanonical:
    def test_maps_lowercased_surface_form(self):
        result = resolve_to_canonical("Apple", {"apple": "Apple Inc."})
        assert result == "Apple Inc."

    def test_case_insensitive_match(self):
        result = resolve_to_canonical("APPLE", {"apple": "Apple Inc."})
        assert result == "Apple Inc."

    def test_mixed_case_surface_form(self):
        result = resolve_to_canonical("  ApPlE  ", {"apple": "Apple Inc."})
        assert result == "Apple Inc."

    def test_returns_original_when_not_in_map(self):
        result = resolve_to_canonical("Microsoft", {"apple": "Apple Inc."})
        assert result == "Microsoft"

    def test_empty_map_returns_original(self):
        result = resolve_to_canonical("Apple", {})
        assert result == "Apple"

    def test_empty_string_not_in_map(self):
        result = resolve_to_canonical("", {"": "EMPTY"})
        assert result == "EMPTY"

    def test_whitespace_only_stripped(self):
        result = resolve_to_canonical("   ", {"": "EMPTY"})
        assert result == "EMPTY"


class TestOmissionLabel:
    def test_low_below_25(self):
        assert omission_label(0.0) == "LOW"
        assert omission_label(0.24) == "LOW"

    def test_med_start_at_25(self):
        assert omission_label(0.25) == "MED"
        assert omission_label(0.49) == "MED"

    def test_high_at_50_and_above(self):
        assert omission_label(0.50) == "HIGH"
        assert omission_label(0.75) == "HIGH"
        assert omission_label(1.0) == "HIGH"


class TestFramingVolatilityLabel:
    def test_low_below_25(self):
        assert framing_volatility_label(0.0) == "LOW"
        assert framing_volatility_label(0.24) == "LOW"

    def test_med_start_at_25(self):
        assert framing_volatility_label(0.25) == "MED"
        assert framing_volatility_label(0.54) == "MED"

    def test_high_at_55_and_above(self):
        assert framing_volatility_label(0.55) == "HIGH"
        assert framing_volatility_label(0.80) == "HIGH"
        assert framing_volatility_label(1.0) == "HIGH"


class TestScatterShotLabel:
    def test_low_below_35(self):
        assert scatter_shot_label(0.0) == "LOW"
        assert scatter_shot_label(0.34) == "LOW"

    def test_med_start_at_35(self):
        assert scatter_shot_label(0.35) == "MED"
        assert scatter_shot_label(0.59) == "MED"

    def test_high_at_60_and_above(self):
        assert scatter_shot_label(0.60) == "HIGH"
        assert scatter_shot_label(0.80) == "HIGH"
        assert scatter_shot_label(1.0) == "HIGH"


class TestSyncLabel:
    def test_high_at_65_and_above(self):
        assert sync_label(0.65) == "HIGH"
        assert sync_label(0.80) == "HIGH"
        assert sync_label(1.0) == "HIGH"

    def test_med_start_at_35(self):
        assert sync_label(0.35) == "MED"
        assert sync_label(0.64) == "MED"

    def test_low_below_35(self):
        assert sync_label(0.0) == "LOW"
        assert sync_label(0.34) == "LOW"


class TestComputeOmissionIndex:
    def test_empty_consensus_returns_zero(self):
        oi, missing = compute_omission_index(set(), {"a"}, {})
        assert oi == 0.0
        assert missing == []

    def test_no_missing_nodes(self):
        oi, missing = compute_omission_index({"a", "b"}, {"a", "b"}, {})
        assert oi == 0.0
        assert missing == []

    def test_partial_omission(self):
        oi, missing = compute_omission_index({"a", "b", "c", "d"}, {"a", "b"}, {})
        assert oi == 0.5
        assert sorted(missing) == ["c", "d"]

    def test_canonical_resolution_before_comparison(self):
        consensus = {"Apple", "Google"}
        source = {"apple"}
        canon = {"apple": "Apple", "google": "Google"}
        oi, missing = compute_omission_index(consensus, source, canon)
        assert oi == 0.5
        assert missing == ["Google"]

    def test_all_missing(self):
        oi, missing = compute_omission_index({"a", "b"}, {"c", "d"}, {})
        assert oi == 1.0
        assert sorted(missing) == ["a", "b"]

    def test_source_subset_with_canonical_overlap(self):
        consensus = {"a", "b", "c"}
        source = {"A"}
        canon = {"a": "A"}
        oi, missing = compute_omission_index(consensus, source, canon)
        assert oi == 0.6667
        assert sorted(missing) == ["b", "c"]


def _graph(nodes: list[str], domain: str = "a.com", parse_error: bool = False) -> dict:
    g: dict = {"nodes": nodes, "_source_domain": domain}
    if parse_error:
        g["_parse_error"] = True
    return g


class TestComputeConsensusBaseline:
    def test_less_than_5_sources_returns_empty(self):
        graphs = [_graph(["x"], "a.com") for _ in range(4)]
        assert compute_consensus_baseline(graphs, {}) == set()

    def test_exactly_5_sources_all_agree(self):
        graphs = [_graph(["x"], f"source-{i}.com") for i in range(5)]
        result = compute_consensus_baseline(graphs, {})
        assert result == {"x"}

    def test_node_in_4_of_5_sources(self):
        graphs = [_graph(["x"], f"source-{i}.com") for i in range(4)]
        graphs.append(_graph([], "source-4.com"))
        result = compute_consensus_baseline(graphs, {})
        assert result == {"x"}

    def test_node_in_3_of_5_sources_below_threshold(self):
        graphs = [_graph(["x"], f"source-{i}.com") for i in range(3)]
        for i in range(3, 5):
            graphs.append(_graph([], f"source-{i}.com"))
        result = compute_consensus_baseline(graphs, {})
        assert result == set()

    def test_parse_errors_excluded_from_n(self):
        graphs = [_graph(["x"], f"good-{i}.com") for i in range(5)]
        graphs.append(_graph(["x"], "bad.com", parse_error=True))
        result = compute_consensus_baseline(graphs, {})
        assert result == {"x"}  # still need 4/5 = int(0.75*5)+1 = 4

    def test_canonical_resolution_applied(self):
        graphs = [_graph(["Apple"], f"source-{i}.com") for i in range(5)]
        result = compute_consensus_baseline(graphs, {"apple": "Apple Inc."})
        assert result == {"Apple Inc."}

    def test_multiple_nodes_different_frequencies(self):
        graphs = [
            _graph(["a", "b"], f"s{i}.com")
            for i in range(4)
        ]
        graphs.append(_graph(["a"], "s4.com"))
        result = compute_consensus_baseline(graphs, {})
        # threshold = int(0.75*5)+1 = 4
        # a appears in 5 sources, b in 4
        assert result == {"a", "b"}

    def test_no_nodes_in_any_graph(self):
        graphs = [_graph([], f"source-{i}.com") for i in range(5)]
        result = compute_consensus_baseline(graphs, {})
        assert result == set()

    def test_threshold_is_ceiling_not_floor(self):
        # 5 valid sources: threshold = int(0.75*5)+1 = 3+1 = 4
        graphs = [_graph(["x"], f"s{i}.com") for i in range(4)]
        graphs.append(_graph([], "s4.com"))
        result = compute_consensus_baseline(graphs, {})
        assert result == {"x"}  # x in 4 sources, threshold is 4

    def test_threshold_with_6_sources(self):
        # 6 valid: threshold = int(4.5)+1 = 4+1 = 5
        graphs = [_graph(["x"], f"s{i}.com") for i in range(5)]
        graphs.append(_graph([], "s5.com"))
        result = compute_consensus_baseline(graphs, {})
        assert result == {"x"}  # x in 5/6, threshold is 5


class TestComputeSaForOutlet:
    def test_zero_total_returns_zero_low(self):
        sa, label = compute_sa_for_outlet("x.com", 0, 0)
        assert sa == 0.0
        assert label == "LOW"

    def test_no_decayed_nodes(self):
        sa, label = compute_sa_for_outlet("x.com", 0, 10)
        assert sa == 0.0
        assert label == "LOW"

    def test_some_decayed(self):
        sa, label = compute_sa_for_outlet("x.com", 3, 10)
        assert sa == 0.3
        assert label == "LOW"

    def test_medium_threshold(self):
        sa, label = compute_sa_for_outlet("x.com", 4, 10)
        assert sa == 0.4
        assert label == "MED"

    def test_high_threshold(self):
        sa, label = compute_sa_for_outlet("x.com", 6, 10)
        assert sa == 0.6
        assert label == "HIGH"

    def test_all_decayed(self):
        sa, label = compute_sa_for_outlet("x.com", 10, 10)
        assert sa == 1.0
        assert label == "HIGH"

    def test_rounding_to_4_decimal_places(self):
        sa, label = compute_sa_for_outlet("x.com", 1, 3)
        assert sa == 0.3333


class TestComputeConsensusStability:
    def test_zero_total_sources_returns_zero(self):
        score = compute_consensus_stability({}, 0)
        assert score == 0.0

    def test_single_structure_all_sources(self):
        score = compute_consensus_stability({"narrative_a": 5}, 5)
        assert score == 1.0

    def test_two_structures_half_and_half(self):
        score = compute_consensus_stability({"a": 3, "b": 3}, 6)
        assert score == 0.8333

    def test_three_structures(self):
        score = compute_consensus_stability({"a": 2, "b": 2, "c": 2}, 6)
        assert score == 0.6667

    def test_many_structures_low_stability(self):
        score = compute_consensus_stability({"a": 1, "b": 1, "c": 1, "d": 1, "e": 1}, 10)
        assert score == 0.6

    def test_score_clamped_at_zero(self):
        score = compute_consensus_stability({"a": 1, "b": 1, "c": 1, "d": 1, "e": 1, "f": 1}, 5)
        assert score == 0.0

    def test_single_structure_with_extra_metadata(self):
        score = compute_consensus_stability({"a_claim": 6}, 6)
        assert score == 1.0

    def test_returns_float_not_tuple(self):
        result = compute_consensus_stability({"a": 5}, 5)
        assert isinstance(result, float)

    def test_score_not_exceeding_1(self):
        score = compute_consensus_stability({"a": 10}, 10)
        assert score == 1.0


class TestExtractGraph:
    def test_returns_parsed_json_from_llm(self, monkeypatch):
        expected = {"nodes": ["A Corp", "B Ltd"], "edges": []}
        monkeypatch.setattr(
            "narrative.llm_client.call_llm",
            lambda *a, **kw: '{"nodes": ["A Corp", "B Ltd"], "edges": []}',
        )
        result = extract_graph("Some text", {}, {"call_3_graph_extraction": {}})
        assert result == expected

    def test_entity_dict_included_in_prompt(self, monkeypatch):
        captured = {}

        def _capture_call(slot_cfg, messages, json_mode):
            captured["user_msg"] = messages[1]["content"]
            return '{"nodes": [], "edges": []}'

        monkeypatch.setattr("narrative.llm_client.call_llm", _capture_call)
        extract_graph("Article body", {"apple": "Apple Inc."}, {"call_3_graph_extraction": {}})
        assert "Apple Inc." in captured["user_msg"]
        assert "Article body" in captured["user_msg"]


class TestExtractAllGraphs:
    def test_returns_graph_per_doc(self, monkeypatch):
        monkeypatch.setattr(
            "narrative.llm_client.call_llm",
            lambda *a, **kw: '{"nodes": ["X"], "edges": []}',
        )
        docs = [
            {"source_domain": "a.com", "source_name": "A"},
            {"source_domain": "b.com", "source_name": "B"},
        ]
        results = extract_all_graphs(docs, ["text a", "text b"], {}, {"call_3_graph_extraction": {}})
        assert len(results) == 2
        assert results[0]["_source_domain"] == "a.com"
        assert results[1]["_source_domain"] == "b.com"

    def test_parse_error_gets_empty_graph(self, monkeypatch):
        def _fail(*a, **kw):
            raise RuntimeError("LLM down")

        monkeypatch.setattr("narrative.llm_client.call_llm", _fail)
        docs = [{"source_domain": "a.com"}]
        results = extract_all_graphs(docs, ["text"], {}, {"call_3_graph_extraction": {}})
        assert len(results) == 1
        assert results[0].get("_parse_error") is True
        assert results[0]["nodes"] == []
        assert results[0]["edges"] == []

    def test_mixed_success_and_failure(self, monkeypatch):
        call_count = [0]

        def _alternate(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return '{"nodes": ["X"], "edges": []}'
            raise RuntimeError("fail")

        monkeypatch.setattr("narrative.llm_client.call_llm", _alternate)
        docs = [
            {"source_domain": "a.com", "source_name": "A"},
            {"source_domain": "b.com", "source_name": "B"},
        ]
        results = extract_all_graphs(docs, ["text a", "text b"], {}, {"call_3_graph_extraction": {}})
        assert len(results) == 2
        assert results[0].get("_parse_error") is None
        assert results[1].get("_parse_error") is True

    def test_uses_neutralized_text_not_raw(self, monkeypatch):
        captured_texts = []

        def _capture(slot_cfg, messages, json_mode):
            captured_texts.append(messages[1]["content"])
            return '{"nodes": [], "edges": []}'

        monkeypatch.setattr("narrative.llm_client.call_llm", _capture)
        docs = [
            {"source_domain": "a.com"},
            {"source_domain": "b.com"},
        ]
        extract_all_graphs(docs, ["neut_a", "neut_b"], {}, {"call_3_graph_extraction": {}})
        assert "neut_a" in captured_texts[0]
        assert "neut_b" in captured_texts[1]


class TestComputeFramingVolatility:
    def test_identical_texts_produce_vf_zero(self, monkeypatch):
        monkeypatch.setattr(
            "narrative.llm_client.get_embedding",
            lambda text, retries=1: [0.5, 0.5, 0.5] if "identical" in text else [0.5, 0.5, 0.5],
        )
        scores, labels = compute_framing_volatility(
            ["identical text"], ["identical text"]
        )
        assert scores == [0.0]

    def test_orthogonal_vectors_produce_vf_one(self, monkeypatch):
        embeddings = iter([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ])

        def _mock_embed(text, retries=1):
            return next(embeddings)

        monkeypatch.setattr("narrative.llm_client.get_embedding", _mock_embed)
        scores, labels = compute_framing_volatility(
            ["orthogonal raw"], ["orthogonal neut"]
        )
        assert scores[0] == 1.0

    def test_multiple_docs_return_parallel_lists(self, monkeypatch):
        monkeypatch.setattr(
            "narrative.llm_client.get_embedding",
            lambda text, retries=1: [0.6, 0.8],
        )
        scores, labels = compute_framing_volatility(
            ["raw1", "raw2", "raw3"],
            ["neut1", "neut2", "neut3"],
        )
        assert len(scores) == 3
        assert len(labels) == 3

    def test_labels_match_vf_ranges(self, monkeypatch):
        monkeypatch.setattr(
            "narrative.llm_client.get_embedding",
            lambda text, retries=1: [1.0, 0.0],
        )
        scores, labels = compute_framing_volatility(
            ["raw1", "raw2", "raw3"],
            ["neut1", "neut2", "neut3"],
        )
        assert all(l == "LOW" for l in labels)


def _cluster_graph(
    edges: list[tuple[str, str, str]],
    domain: str,
    nodes: list[str] | None = None,
) -> dict:
    all_nodes = list({e[0] for e in edges} | {e[1] for e in edges})
    if nodes:
        all_nodes = list(set(all_nodes) | set(nodes))
    return {
        "_source_domain": domain,
        "nodes": all_nodes,
        "edges": [
            {"source": s, "target": t, "relationship_verb": v}
            for s, t, v in edges
        ],
    }


class TestComputePreSynthesisContext:
    def test_narrative_clusters_groups_edges_by_topic(self):
        graphs = [
            _cluster_graph([("CompanyA", "Profits rose", "reports")], "source1.com"),
            _cluster_graph([("CompanyA", "Profits rose", "reports")], "source2.com"),
        ]
        result = compute_pre_synthesis_context(
            graphs, [], [], {}, {"CompanyA"},
        )
        clusters = result["narrative_clusters"]
        assert "CompanyA" in clusters
        assert clusters["CompanyA"]["Profits rose (reports)"] == ["source1.com", "source2.com"]

    def test_fracture_candidates_detected(self):
        graphs = [
            _cluster_graph([("CompanyA", "Profits rose", "reports")], "source1.com"),
            _cluster_graph([("CompanyA", "Stock fell", "contradicts")], "source2.com"),
        ]
        result = compute_pre_synthesis_context(
            graphs, [], [], {}, {"CompanyA"},
        )
        assert len(result["fracture_candidates"]) >= 1
        topic, claim_a, outlets_a, claim_b, outlets_b = result["fracture_candidates"][0]
        assert topic == "CompanyA"

    def test_no_fractures_when_all_agree(self):
        graphs = [
            _cluster_graph([("CompanyA", "Profits rose", "reports")], "s1.com"),
            _cluster_graph([("CompanyA", "Profits rose", "reports")], "s2.com"),
            _cluster_graph([("CompanyA", "Profits rose", "reports")], "s3.com"),
        ]
        result = compute_pre_synthesis_context(
            graphs, [], [], {}, {"CompanyA"},
        )
        assert result["fracture_candidates"] == []

    def test_term_shifts_scans_raw_texts(self):
        graphs = [
            _cluster_graph([("CompanyA", "good", "says")], "s1.com"),
            _cluster_graph([("CompanyA", "good", "says")], "s2.com"),
        ]
        raw_texts = [
            "The enterprise reported strong earnings.",
            "The enterprise posted record revenue.",
        ]
        canonical_map = {"enterprise": "company", "firm": "company"}
        result = compute_pre_synthesis_context(
            graphs, [], raw_texts, canonical_map, {"CompanyA"},
        )
        assert len(result["term_shifts"]) >= 1
        shift = result["term_shifts"][0]
        assert shift["replacement_term"] == "enterprise"
        assert shift["observed_across"] == 2

    def test_edge_not_in_consensus_excluded(self):
        graphs = [
            _cluster_graph([("OtherTopic", "Something", "says")], "s1.com"),
        ]
        result = compute_pre_synthesis_context(
            graphs, [], [], {}, set(),
        )
        assert result["narrative_clusters"] == {}
        assert result["fracture_candidates"] == []
        assert result["term_shifts"] == []

    def test_no_edges_empty_results(self):
        result = compute_pre_synthesis_context(
            [], [], [], {}, set(),
        )
        assert result["narrative_clusters"] == {}
        assert result["fracture_candidates"] == []
        assert result["term_shifts"] == []

    def test_canonical_resolution_for_topic_matching(self):
        graphs = [
            _cluster_graph([("Apple", "Profits rose", "reports")], "s1.com"),
            _cluster_graph([("apple", "Profits rose", "reports")], "s2.com"),
        ]
        result = compute_pre_synthesis_context(
            graphs, [], [], {"apple": "Apple"}, {"Apple"},
        )
        clusters = result["narrative_clusters"]
        assert "Apple" in clusters


class TestSynthesizeForensicReport:
    def test_returns_parsed_json_from_llm(self, monkeypatch):
        fake_response = json.dumps({
            "event_meta": {"cluster_id": "cl-001", "search_query": "test", "industry_vertical": "TECH", "timestamp_utc": "2026-05-29T00:00:00Z", "corpus_count": 3, "corpus_capped": False},
            "consensus_reality_graph": {"consensus_summary": "All agreed.", "verified_anchor_nodes": [], "primary_verifications": []},
            "distortion_matrix": [],
            "outlier_signals": [],
            "reputation_warnings": [],
            "reality_divergence_zones": [],
            "reality_fractures": [],
            "narrative_regime_shifts": [],
        })
        monkeypatch.setattr(
            "narrative.llm_client.call_llm",
            lambda *a, **kw: fake_response,
        )
        result = synthesize_forensic_report(
            {"test": "data"}, {"call_4_forensic_synthesis": {}}
        )
        assert result["event_meta"]["cluster_id"] == "cl-001"
        assert result["distortion_matrix"] == []

    def test_context_bundle_included_in_prompt(self, monkeypatch):
        captured = {}

        def _capture(slot_cfg, messages, json_mode):
            captured["content"] = messages[1]["content"]
            return '{"event_meta": {}, "consensus_reality_graph": {"consensus_summary":"","verified_anchor_nodes":[],"primary_verifications":[]}, "distortion_matrix": [], "outlier_signals": [], "reputation_warnings": [], "reality_divergence_zones": [], "reality_fractures": [], "narrative_regime_shifts": []}'

        monkeypatch.setattr("narrative.llm_client.call_llm", _capture)
        synthesize_forensic_report(
            {"key": "value"}, {"call_4_forensic_synthesis": {}}
        )
        assert "key" in captured["content"]
        assert "value" in captured["content"]

    def test_llm_failure_raises(self, monkeypatch):
        def _fail(*a, **kw):
            raise RuntimeError("LLM unavailable")

        monkeypatch.setattr("narrative.llm_client.call_llm", _fail)
        with pytest.raises(RuntimeError):
            synthesize_forensic_report(
                {}, {"call_4_forensic_synthesis": {}}
            )


class TestInjectLabels:
    def test_adds_omission_and_framing_labels(self):
        report = {
            "distortion_matrix": [
                {"outlet_name": "A", "source_domain": "a.com", "omission_index": 0.1, "framing_volatility_score": 0.3, "identifiable_omissions": [], "linguistic_camouflage": []},
                {"outlet_name": "B", "source_domain": "b.com", "omission_index": 0.6, "framing_volatility_score": 0.7, "identifiable_omissions": [], "linguistic_camouflage": []},
            ],
        }
        result = inject_labels(report)
        assert result["distortion_matrix"][0]["omission_label"] == "LOW"
        assert result["distortion_matrix"][0]["framing_volatility_label"] == "MED"
        assert result["distortion_matrix"][1]["omission_label"] == "HIGH"
        assert result["distortion_matrix"][1]["framing_volatility_label"] == "HIGH"

    def test_adds_scatter_shot_label(self):
        report = {
            "outlier_signals": [
                {"signal_id": "s1", "origin_outlet": "A", "origin_domain": "a.com", "extracted_claim": "X", "timestamp_first_seen": "now", "outlier_origin_provenance": {"classification": "SINGLE_SOURCE", "historical_origin_validation_rate": 0.5, "scatter_shot_anomaly_factor": 0.4, "reputation_warning_triggered": False, "echo_chamber_mimics": []}, "validation_tracking": {"current_state": "PENDING", "last_checked_timestamp": "now", "consensus_absorption_status": "PENDING", "evaluation_window_days": 30}},
                {"signal_id": "s2", "origin_outlet": "B", "origin_domain": "b.com", "extracted_claim": "Y", "timestamp_first_seen": "now", "outlier_origin_provenance": {"classification": "SINGLE_SOURCE", "historical_origin_validation_rate": 0.5, "scatter_shot_anomaly_factor": 0.7, "reputation_warning_triggered": False, "echo_chamber_mimics": []}, "validation_tracking": {"current_state": "PENDING", "last_checked_timestamp": "now", "consensus_absorption_status": "PENDING", "evaluation_window_days": 30}},
            ],
        }
        result = inject_labels(report)
        assert result["outlier_signals"][0]["outlier_origin_provenance"]["scatter_shot_label"] == "MED"
        assert result["outlier_signals"][1]["outlier_origin_provenance"]["scatter_shot_label"] == "HIGH"

    def test_adds_scatter_shot_label_to_reputation_warnings(self):
        report = {
            "reputation_warnings": [
                {"outlet_name": "X", "source_domain": "x.com", "warning_triggered": True,
                 "historical_origin_validation_rate": 0.3, "scatter_shot_anomaly_factor": 0.45,
                 "warning_message": "Repeated outlier claims"},
                {"outlet_name": "Y", "source_domain": "y.com", "warning_triggered": True,
                 "historical_origin_validation_rate": 0.5, "scatter_shot_anomaly_factor": 0.65,
                 "warning_message": "High anomaly rate"},
            ],
        }
        result = inject_labels(report)
        assert result["reputation_warnings"][0]["scatter_shot_label"] == "MED"
        assert result["reputation_warnings"][1]["scatter_shot_label"] == "HIGH"

    def test_adds_consensus_stability_label(self):
        report = {
            "reality_divergence_zones": [
                {"topic": "A", "consensus_stability_score": 0.8, "institutional_convergence": "RESOLVED", "observed_narrative_structures": [], "supporting_outlets": {}},
                {"topic": "B", "consensus_stability_score": 0.3, "institutional_convergence": "CONTESTED", "observed_narrative_structures": [], "supporting_outlets": {}},
            ],
        }
        result = inject_labels(report)
        assert result["reality_divergence_zones"][0]["consensus_stability"] == "HIGH"
        assert result["reality_divergence_zones"][1]["consensus_stability"] == "LOW"

    def test_adds_synchronization_label(self):
        report = {
            "narrative_regime_shifts": [
                {"shift_id": "sh1", "topic": "A", "detected_shift": {"previous_term": "old", "replacement_term": "new"}, "observed_across": 5, "total_sources": 10, "synchronization_score": 0.8, "interpretive_note": ""},
                {"shift_id": "sh2", "topic": "B", "detected_shift": {"previous_term": "old", "replacement_term": "new"}, "observed_across": 2, "total_sources": 10, "synchronization_score": 0.2, "interpretive_note": ""},
            ],
        }
        result = inject_labels(report)
        assert result["narrative_regime_shifts"][0]["synchronization_label"] == "HIGH"
        assert result["narrative_regime_shifts"][1]["synchronization_label"] == "LOW"

    def test_adds_classification_method_to_fractures(self):
        report = {
            "reality_fractures": [
                {"fracture_id": "f1", "topic": "A", "claim_a": {"statement": "X", "supporting_outlets": ["a.com"]}, "claim_b": {"statement": "Y", "supporting_outlets": ["b.com"]}, "relationship": "STRUCTURALLY_CONTRADICTORY", "resolution_status": "UNRESOLVED"},
            ],
        }
        result = inject_labels(report)
        assert result["reality_fractures"][0].get("classification_method") == "LLM_ASSISTED"

    def test_preserves_existing_classification_method(self):
        report = {
            "reality_fractures": [
                {"fracture_id": "f1", "topic": "A", "claim_a": {"statement": "X", "supporting_outlets": ["a.com"]}, "claim_b": {"statement": "Y", "supporting_outlets": ["b.com"]}, "relationship": "STRUCTURALLY_CONTRADICTORY", "resolution_status": "UNRESOLVED", "classification_method": "MANUAL"},
            ],
        }
        result = inject_labels(report)
        assert result["reality_fractures"][0]["classification_method"] == "MANUAL"

    def test_empty_sections_no_errors(self):
        report = {
            "distortion_matrix": [],
            "outlier_signals": [],
            "reputation_warnings": [],
            "reality_divergence_zones": [],
            "reality_fractures": [],
            "narrative_regime_shifts": [],
        }
        result = inject_labels(report)
        assert result is not None
