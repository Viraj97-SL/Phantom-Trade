export type Verdict = "FABRICATED" | "AUTHENTIC" | "INCONCLUSIVE";
export type RiskLabel = "STABLE" | "ELEVATED" | "HIGH" | "CRITICAL";
export type Material = "neon" | "palladium" | "soybeans" | "lithium";

export interface ClaimVariant {
  claim_id: string;
  variant_id: string;
  platform: "x" | "telegram" | "reddit" | "youtube" | "synthetic";
  variant_type: "original" | "dub" | "crop" | "text_post" | "repost" | "screenshot";
  content_text: string;
  engagement_count: number;
  author_handle?: string;
}

export interface EvidenceItem {
  evidence_type: string;
  description: string;
  confidence: number;
  source_variant_id?: string;
}

export interface MLForensicsResult {
  claim_id: string;
  spread_velocity_score: number;
  variant_similarity_score: number;
  linguistic_score: number;
  source_credibility_score: number;
  template_match_score: number;
  composite_ml_score: number;
  coordinated_campaign_flag: boolean;
  ml_flags: string[];
  sub_scores: Record<string, unknown>;
  created_at?: string;
}

export interface ClaimVerdict {
  claim_id: string;
  claim_text: string;
  verdict: Verdict;
  confidence: number;
  evidence: EvidenceItem[];
  mutation_graph_summary?: string;
  variants_analysed: number;
  debate_transcript?: string;
  supply_chain_topics: string[];
  ml_result?: MLForensicsResult;
  created_at?: string;
}

export type ScenarioCategory =
  | "port_strike"
  | "sanctions"
  | "weather"
  | "geopolitical"
  | "financial"
  | "custom";

export interface ScenarioTemplate {
  id: string;
  name: string;
  description: string;
  claim_text: string;
  category: ScenarioCategory;
  tags: string[];
  created_by: string;
  is_builtin: boolean;
  created_at?: string;
}

export interface MaterialThesis {
  material: Material;
  risk_level: number;
  risk_label: RiskLabel;
  narrative: string;
  procurement_recommendation?: string;
  key_drivers?: string[];
  valid_from: string;
  valid_to: string | null;
  triggered_by?: string;
  triggered_by_claim_verdict_id?: string;
}

export interface ReasoningEntry {
  material?: string;
  pipeline: "forensics" | "oracle" | "shared";
  task_signature: string;
  strategy_summary: string;
  tools_used: string[];
  outcome: "SUCCESS" | "FAILURE" | "PARTIAL";
  accuracy_delta: number;
  decay_score: number;
  use_count: number;
  created_at: string;
}

export interface RBStats {
  total_entries: number;
  successful_entries: number;
  avg_accuracy_delta: number;
  hit_rate: number;
}

export type SSEEventType =
  | "pipeline_started"
  | "step"
  | "variant_found"
  | "news_crossref_complete"
  | "ml_forensics_complete"
  | "forensics_complete"
  | "debate_complete"
  | "verdict_written"
  | "oracle_triggered"
  | "thesis_updated"
  | "reasoning_bank_updated"
  | "pipeline_complete"
  | "error";

export interface SSEEvent {
  type: SSEEventType;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface HealthStatus {
  status: string;
  mongodb: boolean;
  llm: boolean;
}
