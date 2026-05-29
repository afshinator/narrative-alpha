"""Data contracts for Narrative Alpha — typed Pydantic models for all layers."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ── Contract A: Ingestion Manifest (Layer 1 → Layer 2) ──


class IngestionDocument(BaseModel):
    doc_id: str
    source_name: str
    source_domain: str
    source_url: str
    title: str
    scrape_timestamp: str
    author: str = "Staff"
    raw_text_content: str


class IngestionManifest(BaseModel):
    cluster_id: str
    trigger_type: str
    search_query: str
    timestamp_utc: str
    corpus_count: int
    documents: List[IngestionDocument]


# ── Contract B: Forensic Report (Layer 3 → Layer 4) ──


class EventMeta(BaseModel):
    cluster_id: str
    search_query: str
    industry_vertical: str
    timestamp_utc: str
    corpus_count: int
    corpus_capped: bool = False


class PrimaryVerification(BaseModel):
    authority: str
    reference_id: str
    status: str  # "VERIFIED" | "UNVERIFIED" | ...


class ConsensusRealityGraph(BaseModel):
    consensus_summary: str
    verified_anchor_nodes: List[str]
    primary_verifications: List[PrimaryVerification] = []


class LinguisticCamouflage(BaseModel):
    raw_expression: str
    clinical_translation: str


class DistortionMatrixEntry(BaseModel):
    outlet_name: str
    source_domain: str
    omission_index: float
    omission_label: str = "MED"  # injected by Python after Call 4
    framing_volatility_score: float
    framing_volatility_label: str = "MED"
    identifiable_omissions: List[str] = []
    linguistic_camouflage: List[LinguisticCamouflage] = []


class OutlierProvenance(BaseModel):
    classification: str  # "SINGLE_SOURCE_ORIGIN" | ...
    historical_origin_validation_rate: float
    scatter_shot_anomaly_factor: float
    scatter_shot_label: str = "LOW"
    reputation_warning_triggered: bool = False
    echo_chamber_mimics: List[str] = []


class OutlierValidation(BaseModel):
    current_state: str  # "PENDING" | "VERIFIED" | "DECAYED" | "UNVERIFIED_BY_CONSENSUS"
    last_checked_timestamp: str
    consensus_absorption_status: str  # "PENDING" | "ABSORBED" | "DECAYED"
    evaluation_window_days: int = 30


class OutlierSignal(BaseModel):
    signal_id: str
    origin_outlet: str
    origin_domain: str
    extracted_claim: str
    timestamp_first_seen: str
    outlier_origin_provenance: OutlierProvenance
    validation_tracking: OutlierValidation


class ReputationWarning(BaseModel):
    outlet_name: str
    source_domain: str
    warning_triggered: bool
    historical_origin_validation_rate: float
    scatter_shot_anomaly_factor: float
    scatter_shot_label: str
    warning_message: str


class RealityDivergenceZone(BaseModel):
    topic: str
    consensus_stability: str  # "HIGH" | "MED" | "LOW"
    consensus_stability_score: float
    institutional_convergence: str  # "RESOLVED" | "CONTESTED" | "UNRESOLVED"
    observed_narrative_structures: List[str]
    supporting_outlets: Dict[str, List[str]]  # narrative → [domain, ...]


class RealityFractureClaim(BaseModel):
    statement: str
    supporting_outlets: List[str]


class RealityFracture(BaseModel):
    fracture_id: str
    topic: str
    claim_a: RealityFractureClaim
    claim_b: RealityFractureClaim
    relationship: str  # "STRUCTURALLY_CONTRADICTORY" | "ORTHOGONAL"
    resolution_status: str  # "UNRESOLVED" | "PARTIALLY_RESOLVED"
    classification_method: str = "LLM_ASSISTED"


class NarrativeRegimeShift(BaseModel):
    shift_id: str
    topic: str
    detected_shift: Dict[str, str]  # { "previous_term": str, "replacement_term": str }
    observed_across: int
    total_sources: int
    synchronization_score: float
    synchronization_label: str  # "HIGH" | "MED" | "LOW"
    interpretive_note: str


class ForensicReport(BaseModel):
    event_meta: EventMeta
    consensus_reality_graph: ConsensusRealityGraph
    distortion_matrix: List[DistortionMatrixEntry]
    outlier_signals: List[OutlierSignal]
    reputation_warnings: List[ReputationWarning]
    reality_divergence_zones: List[RealityDivergenceZone]
    reality_fractures: List[RealityFracture]
    narrative_regime_shifts: List[NarrativeRegimeShift]


# ── LLM Config Schema (llm_config.json) ──


class LLMSlotConfig(BaseModel):
    provider: str  # "deepseek" | "openai" | "google" | "groq"
    model: str
    thinking: bool = False
    temperature: float = 0.1


class LLMConfig(BaseModel):
    call_1_entity_normalization: LLMSlotConfig
    call_2_linguistic_neutralization: LLMSlotConfig
    call_3_graph_extraction: LLMSlotConfig
    call_4_forensic_synthesis: LLMSlotConfig


# ── Pipeline Input / Floor Gate Response ──


class PipelineInput(BaseModel):
    keyword: str
    vertical: str  # "TECHNOLOGY" | "FINANCE" | ...


class FloorGateResponse(BaseModel):
    validation_tracking: dict  # { current_state, minimum_required, current_count }
