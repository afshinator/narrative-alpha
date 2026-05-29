"""Tests for contracts.py — Pydantic data contracts for Narrative Alpha.

Run with: python -m pytest test_contracts.py -v
"""

import pytest


# ── Test 10: import check (first, so failures are obvious) ──

def test_import():
    """Contracts module exports the three root models without error."""
    from contracts import IngestionManifest, ForensicReport, LLMConfig, PipelineInput, FloorGateResponse  # noqa: F401


# ── Helpers: minimal valid payloads ──

def _ingestion_document_payload(**overrides):
    base = {
        "doc_id": "doc-001",
        "source_name": "Reuters",
        "source_domain": "reuters.com",
        "source_url": "https://reuters.com/article/1",
        "title": "Test Article",
        "scrape_timestamp": "2026-05-29T10:00:00Z",
        "raw_text_content": "Body text here.",
    }
    base.update(overrides)
    return base


def _ingestion_manifest_payload(**overrides):
    base = {
        "cluster_id": "cluster-001",
        "trigger_type": "SCHEDULED",
        "search_query": "AI regulation",
        "timestamp_utc": "2026-05-29T10:00:00Z",
        "corpus_count": 1,
        "documents": [_ingestion_document_payload()],
    }
    base.update(overrides)
    return base


def _event_meta_payload(**overrides):
    base = {
        "cluster_id": "cluster-001",
        "search_query": "AI regulation",
        "industry_vertical": "TECHNOLOGY",
        "timestamp_utc": "2026-05-29T10:00:00Z",
        "corpus_count": 5,
    }
    base.update(overrides)
    return base


def _distortion_matrix_entry_payload(**overrides):
    base = {
        "outlet_name": "Reuters",
        "source_domain": "reuters.com",
        "omission_index": 0.3,
        "framing_volatility_score": 0.5,
    }
    base.update(overrides)
    return base


def _outlier_provenance_payload(**overrides):
    base = {
        "classification": "SINGLE_SOURCE_ORIGIN",
        "historical_origin_validation_rate": 0.4,
        "scatter_shot_anomaly_factor": 0.2,
    }
    base.update(overrides)
    return base


def _outlier_validation_payload(**overrides):
    base = {
        "current_state": "PENDING",
        "last_checked_timestamp": "2026-05-29T10:00:00Z",
        "consensus_absorption_status": "PENDING",
    }
    base.update(overrides)
    return base


def _outlier_signal_payload(**overrides):
    base = {
        "signal_id": "sig-001",
        "origin_outlet": "Fringe Post",
        "origin_domain": "fringepost.io",
        "extracted_claim": "Everything is fake.",
        "timestamp_first_seen": "2026-05-29T08:00:00Z",
        "outlier_origin_provenance": _outlier_provenance_payload(),
        "validation_tracking": _outlier_validation_payload(),
    }
    base.update(overrides)
    return base


def _forensic_report_payload(**overrides):
    from contracts import (
        EventMeta,
        ConsensusRealityGraph,
        DistortionMatrixEntry,
        OutlierSignal,
        ReputationWarning,
        RealityDivergenceZone,
        RealityFracture,
        RealityFractureClaim,
        NarrativeRegimeShift,
    )

    base = {
        "event_meta": EventMeta(**_event_meta_payload()),
        "consensus_reality_graph": ConsensusRealityGraph(
            consensus_summary="The bill passed.",
            verified_anchor_nodes=["node-1"],
        ),
        "distortion_matrix": [
            DistortionMatrixEntry(**_distortion_matrix_entry_payload())
        ],
        "outlier_signals": [OutlierSignal(**_outlier_signal_payload())],
        "reputation_warnings": [
            ReputationWarning(
                outlet_name="Fringe Post",
                source_domain="fringepost.io",
                warning_triggered=True,
                historical_origin_validation_rate=0.1,
                scatter_shot_anomaly_factor=0.9,
                scatter_shot_label="HIGH",
                warning_message="Unreliable source.",
            )
        ],
        "reality_divergence_zones": [
            RealityDivergenceZone(
                topic="AI safety",
                consensus_stability="HIGH",
                consensus_stability_score=0.9,
                institutional_convergence="RESOLVED",
                observed_narrative_structures=["pro-regulation"],
                supporting_outlets={"pro-regulation": ["reuters.com"]},
            )
        ],
        "reality_fractures": [
            RealityFracture(
                fracture_id="frac-001",
                topic="AI safety",
                claim_a=RealityFractureClaim(
                    statement="AI is safe.", supporting_outlets=["reuters.com"]
                ),
                claim_b=RealityFractureClaim(
                    statement="AI is dangerous.", supporting_outlets=["fringepost.io"]
                ),
                relationship="STRUCTURALLY_CONTRADICTORY",
                resolution_status="UNRESOLVED",
            )
        ],
        "narrative_regime_shifts": [
            NarrativeRegimeShift(
                shift_id="shift-001",
                topic="AI regulation",
                detected_shift={"previous_term": "AI safety", "replacement_term": "AI governance"},
                observed_across=3,
                total_sources=10,
                synchronization_score=0.7,
                synchronization_label="HIGH",
                interpretive_note="Framing shifted after summit.",
            )
        ],
    }
    base.update(overrides)
    return base


# ── Test 1: IngestionDocument and IngestionManifest instantiate ──

def test_ingestion_document_instantiates():
    from contracts import IngestionDocument
    doc = IngestionDocument(**_ingestion_document_payload())
    assert doc.doc_id == "doc-001"


def test_ingestion_manifest_instantiates():
    from contracts import IngestionManifest
    manifest = IngestionManifest(**_ingestion_manifest_payload())
    assert manifest.cluster_id == "cluster-001"


# ── Test 2: IngestionDocument.author defaults to "Staff" ──

def test_ingestion_document_author_default():
    from contracts import IngestionDocument
    doc = IngestionDocument(**_ingestion_document_payload())
    assert doc.author == "Staff"


# ── Test 3: EventMeta.corpus_capped defaults to False ──

def test_event_meta_corpus_capped_default():
    from contracts import EventMeta
    meta = EventMeta(**_event_meta_payload())
    assert meta.corpus_capped is False


# ── Test 4: DistortionMatrixEntry label defaults ──

def test_distortion_matrix_omission_label_default():
    from contracts import DistortionMatrixEntry
    entry = DistortionMatrixEntry(**_distortion_matrix_entry_payload())
    assert entry.omission_label == "UNLABELED"


def test_distortion_matrix_framing_volatility_label_default():
    from contracts import DistortionMatrixEntry
    entry = DistortionMatrixEntry(**_distortion_matrix_entry_payload())
    assert entry.framing_volatility_label == "UNLABELED"


# ── Test 5: OutlierProvenance defaults ──

def test_outlier_provenance_scatter_shot_label_default():
    from contracts import OutlierProvenance
    prov = OutlierProvenance(**_outlier_provenance_payload())
    assert prov.scatter_shot_label == "UNLABELED"


def test_outlier_provenance_reputation_warning_triggered_default():
    from contracts import OutlierProvenance
    prov = OutlierProvenance(**_outlier_provenance_payload())
    assert prov.reputation_warning_triggered is False


# ── Test 6: OutlierValidation.evaluation_window_days defaults to 30 ──

def test_outlier_validation_evaluation_window_days_default():
    from contracts import OutlierValidation
    val = OutlierValidation(**_outlier_validation_payload())
    assert val.evaluation_window_days == 30


# ── Test 7: RealityFracture.classification_method defaults to "LLM_ASSISTED" ──

def test_reality_fracture_classification_method_default():
    from contracts import RealityFracture, RealityFractureClaim
    fracture = RealityFracture(
        fracture_id="frac-001",
        topic="AI safety",
        claim_a=RealityFractureClaim(
            statement="Safe.", supporting_outlets=["reuters.com"]
        ),
        claim_b=RealityFractureClaim(
            statement="Unsafe.", supporting_outlets=["fringepost.io"]
        ),
        relationship="STRUCTURALLY_CONTRADICTORY",
        resolution_status="UNRESOLVED",
    )
    assert fracture.classification_method == "LLM_ASSISTED"


# ── Test 8: LLMSlotConfig defaults ──

def test_llm_slot_config_thinking_default():
    from contracts import LLMSlotConfig
    slot = LLMSlotConfig(provider="openai", model="gpt-4o")
    assert slot.thinking is False


def test_llm_slot_config_temperature_default():
    from contracts import LLMSlotConfig
    slot = LLMSlotConfig(provider="openai", model="gpt-4o")
    assert slot.temperature == 0.1


# ── Test 9: ForensicReport instantiates with all nested models ──

def test_forensic_report_instantiates():
    from contracts import ForensicReport
    report = ForensicReport(**_forensic_report_payload())
    assert report.event_meta.cluster_id == "cluster-001"
    assert len(report.distortion_matrix) == 1
    assert len(report.outlier_signals) == 1
    assert len(report.reality_fractures) == 1
    assert len(report.narrative_regime_shifts) == 1


def test_pipeline_input_instantiates():
    from contracts import PipelineInput
    pi = PipelineInput(keyword="AI safety", vertical="TECHNOLOGY")
    assert pi.keyword == "AI safety"
    assert pi.vertical == "TECHNOLOGY"


def test_floor_gate_response_instantiates():
    from contracts import FloorGateResponse, FloorGateTracking
    fgr = FloorGateResponse(
        status="INSUFFICIENT_CORPUS_FLOOR",
        validation_tracking=FloorGateTracking(
            current_state="INSUFFICIENT_CORPUS_FLOOR",
            minimum_required=5,
            current_count=3,
        ),
    )
    assert fgr.status == "INSUFFICIENT_CORPUS_FLOOR"
    assert fgr.validation_tracking.current_count == 3


# ── Adversarial tests ──

def test_omission_index_rejects_out_of_range():
    from contracts import DistortionMatrixEntry
    import pytest
    with pytest.raises(Exception):
        DistortionMatrixEntry(outlet_name="x", source_domain="x", omission_index=1.5, framing_volatility_score=0.5)
    with pytest.raises(Exception):
        DistortionMatrixEntry(outlet_name="x", source_domain="x", omission_index=-0.1, framing_volatility_score=0.5)


def test_detected_shift_rejects_wrong_keys():
    from contracts import NarrativeRegimeShift
    import pytest
    with pytest.raises(Exception):
        NarrativeRegimeShift(
            shift_id="s1", topic="t",
            detected_shift={"wrong_key": "x"},
            observed_across=3, total_sources=10,
            synchronization_score=0.7,
            interpretive_note="note",
        )


def test_corpus_count_must_match_documents():
    from contracts import IngestionManifest
    import pytest
    with pytest.raises(Exception):
        IngestionManifest(
            cluster_id="c", trigger_type="t", search_query="q",
            timestamp_utc="2026-01-01", corpus_count=99, documents=[],
        )


def test_extra_fields_rejected():
    from contracts import DistortionMatrixEntry
    import pytest
    with pytest.raises(Exception):
        DistortionMatrixEntry(
            outlet_name="x", source_domain="x",
            omission_index=0.5, framing_volatility_score=0.5,
            totally_unexpected_field="surprise",
        )


def test_temperature_rejects_out_of_range():
    from contracts import LLMSlotConfig
    import pytest
    with pytest.raises(Exception):
        LLMSlotConfig(provider="deepseek", model="v4", temperature=5.0)


def test_null_list_coerced_to_empty():
    from contracts import DistortionMatrixEntry
    entry = DistortionMatrixEntry(
        outlet_name="x", source_domain="x",
        omission_index=0.5, framing_volatility_score=0.5,
        identifiable_omissions=None,
    )
    assert entry.identifiable_omissions == []


def test_floor_gate_rejects_arbitrary_dict():
    from contracts import FloorGateResponse
    import pytest
    with pytest.raises(Exception):
        FloorGateResponse(validation_tracking={"anything": "goes"})
