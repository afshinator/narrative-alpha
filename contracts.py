"""Data contracts for Narrative Alpha — typed Pydantic models for all layers."""

from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Strict base: reject unknown fields to catch LLM key drift ──

class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── Contract A: Ingestion Manifest (Layer 1 → Layer 2) ──


class IngestionDocument(_Strict):
    doc_id: str
    source_name: str
    source_domain: str
    source_url: str
    title: str
    scrape_timestamp: str
    author: str = "Staff"
    raw_text_content: str


class IngestionManifest(_Strict):
    cluster_id: str
    trigger_type: str
    search_query: str
    timestamp_utc: str
    corpus_count: int = Field(ge=0)
    documents: List[IngestionDocument]

    @model_validator(mode="after")
    def _corpus_count_matches_documents(self):
        if self.corpus_count != len(self.documents):
            raise ValueError(
                f"corpus_count={self.corpus_count} != len(documents)={len(self.documents)}"
            )
        return self


# ── Contract B: Forensic Report (Layer 3 → Layer 4) ──


class EventMeta(_Strict):
    cluster_id: str
    search_query: str
    industry_vertical: str
    timestamp_utc: str
    corpus_count: int = Field(ge=0)
    corpus_capped: bool = False


class PrimaryVerification(_Strict):
    authority: str
    reference_id: str
    status: str  # "VERIFIED" | "UNVERIFIED" | ...


class ConsensusRealityGraph(_Strict):
    consensus_summary: str
    verified_anchor_nodes: List[str]
    primary_verifications: List[PrimaryVerification] = []

    @field_validator("verified_anchor_nodes", "primary_verifications", mode="before")
    @classmethod
    def _null_to_empty(cls, v):
        return v if v is not None else []


class LinguisticCamouflage(_Strict):
    raw_expression: str
    clinical_translation: str


class DistortionMatrixEntry(_Strict):
    outlet_name: str
    source_domain: str
    omission_index: float = Field(ge=0.0, le=1.0)
    omission_label: str = "UNLABELED"  # injected by Python after Call 4
    framing_volatility_score: float = Field(ge=0.0, le=1.0)
    framing_volatility_label: str = "UNLABELED"  # injected by Python after Call 4
    identifiable_omissions: List[str] = []
    linguistic_camouflage: List[LinguisticCamouflage] = []

    @field_validator("identifiable_omissions", "linguistic_camouflage", mode="before")
    @classmethod
    def _null_to_empty(cls, v):
        return v if v is not None else []


class OutlierProvenance(_Strict):
    classification: str  # "SINGLE_SOURCE_ORIGIN" | ...
    historical_origin_validation_rate: float = Field(ge=0.0, le=1.0)
    scatter_shot_anomaly_factor: float = Field(ge=0.0, le=1.0)
    scatter_shot_label: str = "UNLABELED"  # injected by Python after Call 4
    reputation_warning_triggered: bool = False
    echo_chamber_mimics: List[str] = []

    @field_validator("echo_chamber_mimics", mode="before")
    @classmethod
    def _null_to_empty(cls, v):
        return v if v is not None else []


class OutlierValidation(_Strict):
    current_state: str  # "PENDING" | "VERIFIED" | "DECAYED" | "UNVERIFIED_BY_CONSENSUS"
    last_checked_timestamp: str
    consensus_absorption_status: str  # "PENDING" | "ABSORBED" | "DECAYED"
    evaluation_window_days: int = 30


class OutlierSignal(_Strict):
    signal_id: str
    origin_outlet: str
    origin_domain: str
    extracted_claim: str
    timestamp_first_seen: str
    outlier_origin_provenance: OutlierProvenance
    validation_tracking: OutlierValidation


class ReputationWarning(_Strict):
    outlet_name: str
    source_domain: str
    warning_triggered: bool
    historical_origin_validation_rate: float = Field(ge=0.0, le=1.0)
    scatter_shot_anomaly_factor: float = Field(ge=0.0, le=1.0)
    scatter_shot_label: str
    warning_message: str


class RealityDivergenceZone(_Strict):
    topic: str
    consensus_stability: str = "UNLABELED"  # injected by Python after Call 4
    consensus_stability_score: float = Field(ge=0.0, le=1.0)
    institutional_convergence: str  # "RESOLVED" | "CONTESTED" | "UNRESOLVED"
    observed_narrative_structures: List[str]
    supporting_outlets: Dict[str, List[str]]  # narrative → [domain, ...]

    @field_validator("observed_narrative_structures", mode="before")
    @classmethod
    def _null_to_empty(cls, v):
        return v if v is not None else []


class RealityFractureClaim(_Strict):
    statement: str
    supporting_outlets: List[str]

    @field_validator("supporting_outlets", mode="before")
    @classmethod
    def _null_to_empty(cls, v):
        return v if v is not None else []


class RealityFracture(_Strict):
    fracture_id: str
    topic: str
    claim_a: RealityFractureClaim
    claim_b: RealityFractureClaim
    relationship: str  # "STRUCTURALLY_CONTRADICTORY" | "ORTHOGONAL"
    resolution_status: str  # "UNRESOLVED" | "PARTIALLY_RESOLVED"
    classification_method: str = "LLM_ASSISTED"


class DetectedShift(_Strict):
    previous_term: str
    replacement_term: str


class NarrativeRegimeShift(_Strict):
    shift_id: str
    topic: str
    detected_shift: DetectedShift
    observed_across: int
    total_sources: int
    synchronization_score: float = Field(ge=0.0, le=1.0)
    synchronization_label: str = "UNLABELED"  # injected by Python after Call 4
    interpretive_note: str


class ForensicReport(_Strict):
    event_meta: EventMeta
    consensus_reality_graph: ConsensusRealityGraph
    distortion_matrix: List[DistortionMatrixEntry]
    outlier_signals: List[OutlierSignal]
    reputation_warnings: List[ReputationWarning]
    reality_divergence_zones: List[RealityDivergenceZone]
    reality_fractures: List[RealityFracture]
    narrative_regime_shifts: List[NarrativeRegimeShift]


# ── LLM Config Schema (llm_config.json) ──


class LLMSlotConfig(_Strict):
    provider: str  # "deepseek" | "openai" | "google" | "groq"
    model: str
    thinking: bool = False
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)


class LLMConfig(_Strict):
    call_1_entity_normalization: LLMSlotConfig
    call_2_linguistic_neutralization: LLMSlotConfig
    call_3_graph_extraction: LLMSlotConfig
    call_4_forensic_synthesis: LLMSlotConfig


# ── Pipeline Input / Floor Gate Response ──


class PipelineInput(_Strict):
    keyword: str
    vertical: str  # "TECHNOLOGY" | "FINANCE" | ...


class FloorGateTracking(_Strict):
    current_state: Literal["INSUFFICIENT_CORPUS_FLOOR"]
    minimum_required: int
    current_count: int


class FloorGateResponse(_Strict):
    status: Literal["INSUFFICIENT_CORPUS_FLOOR"]
    validation_tracking: FloorGateTracking
