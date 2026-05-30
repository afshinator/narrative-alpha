export interface EventMeta {
  cluster_id: string;
  search_query: string;
  industry_vertical: string;
  timestamp_utc: string;
  corpus_count: number;
  corpus_capped: boolean;
}

export interface PrimaryVerification {
  authority: string;
  reference_id: string;
  status: string;
}

export interface ConsensusRealityGraph {
  consensus_summary: string;
  verified_anchor_nodes: string[];
  primary_verifications: PrimaryVerification[];
}

export interface LinguisticCamouflage {
  raw_expression: string;
  clinical_translation: string;
}

export interface DistortionMatrixEntry {
  outlet_name: string;
  source_domain: string;
  omission_index: number;
  omission_label: string;
  framing_volatility_score: number;
  framing_volatility_label: string;
  identifiable_omissions: string[];
  linguistic_camouflage: LinguisticCamouflage[];
}

export interface OutlierProvenance {
  classification: string;
  historical_origin_validation_rate: number;
  scatter_shot_anomaly_factor: number;
  scatter_shot_label: string;
  reputation_warning_triggered: boolean;
  echo_chamber_mimics: string[];
}

export interface OutlierValidation {
  current_state: string;
  last_checked_timestamp: string;
  consensus_absorption_status: string;
  evaluation_window_days: number;
}

export interface OutlierSignal {
  signal_id: string;
  origin_outlet: string;
  origin_domain: string;
  extracted_claim: string;
  timestamp_first_seen: string;
  outlier_origin_provenance: OutlierProvenance;
  validation_tracking: OutlierValidation;
}

export interface ReputationWarning {
  outlet_name: string;
  source_domain: string;
  warning_triggered: boolean;
  historical_origin_validation_rate: number;
  scatter_shot_anomaly_factor: number;
  scatter_shot_label: string;
  warning_message: string;
}

export interface RealityDivergenceZone {
  topic: string;
  consensus_stability: string;
  consensus_stability_score: number;
  institutional_convergence: string;
  observed_narrative_structures: string[];
  supporting_outlets: Record<string, string[]>;
}

export interface RealityFractureClaim {
  statement: string;
  supporting_outlets: string[];
}

export interface RealityFracture {
  fracture_id: string;
  topic: string;
  claim_a: RealityFractureClaim;
  claim_b: RealityFractureClaim;
  relationship: string;
  resolution_status: string;
  classification_method: string;
}

export interface NarrativeRegimeShift {
  shift_id: string;
  topic: string;
  detected_shift: Record<string, string>;
  observed_across: number;
  total_sources: number;
  synchronization_score: number;
  synchronization_label: string;
  interpretive_note: string;
}

export interface ForensicReport {
  event_meta: EventMeta;
  consensus_reality_graph: ConsensusRealityGraph;
  distortion_matrix: DistortionMatrixEntry[];
  outlier_signals: OutlierSignal[];
  reputation_warnings: ReputationWarning[];
  reality_divergence_zones: RealityDivergenceZone[];
  reality_fractures: RealityFracture[];
  narrative_regime_shifts: NarrativeRegimeShift[];
}

export interface LLMSlotConfig {
  provider: string;
  model: string;
  thinking: boolean;
  temperature: number;
}

export interface LLMConfig {
  call_1_entity_normalization: LLMSlotConfig;
  call_2_linguistic_neutralization: LLMSlotConfig;
  call_3_graph_extraction: LLMSlotConfig;
  call_4_forensic_synthesis: LLMSlotConfig;
}

export interface ClusterSummary {
  cluster_id: string;
  search_query: string;
  industry_vertical: string;
  timestamp_utc: string;
  corpus_count: number;
  corpus_capped: boolean;
}

export type PipelineStep =
  | "discovering"
  | "ingesting"
  | "analyzing"
  | "synthesizing"
  | "complete"
  | "error";

export interface PipelineEvent {
  step: PipelineStep;
  message: string;
  cluster_id?: string;
  detail?: string;
}

export interface EnvHealth {
  status: "ok" | "degraded";
  detail: string;
  present: string[];
  missing: string[];
}
