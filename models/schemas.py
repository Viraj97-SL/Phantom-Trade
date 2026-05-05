"""
models/schemas.py
All Pydantic v2 schemas for PHANTOM TRADE.
These are the contracts between every agent and MongoDB.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId


# ── Helpers ──────────────────────────────────────────────────────────────

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            return v
        raise ValueError(f"Not a valid ObjectId: {v}")


# ── SHORT-TERM MEMORY ─────────────────────────────────────────────────────

class AgentSession(BaseModel):
    session_id: str
    agent_id: str
    session_type: Literal["claim_analysis", "oracle_run", "debate", "retrieval"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    active_claim_id: Optional[str] = None
    active_material: Optional[str] = None
    current_phase: Literal["PLAN", "ACT", "OBSERVE", "REACT", "REPLAN", "COMPLETE"] = "PLAN"
    sub_agent_results: dict = Field(default_factory=dict)
    working_hypothesis: Optional[str] = None
    tool_calls_made: List[str] = Field(default_factory=list)
    confidence_current: float = 0.0
    replan_count: int = 0
    metadata: dict = Field(default_factory=dict)

    class Config:
        populate_by_name = True


# ── LONG-TERM MEMORY ──────────────────────────────────────────────────────

class KnowledgeFact(BaseModel):
    entity: str
    entity_type: str
    facts: dict
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None
    confidence: float = Field(ge=0.0, le=1.0)
    source_session_ids: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ── REASONING MEMORY ──────────────────────────────────────────────────────

class ReasoningEntry(BaseModel):
    material: Optional[str] = None
    pipeline: Literal["forensics", "oracle", "shared"]
    task_signature: str
    strategy_summary: str
    tools_used: List[str] = Field(default_factory=list)
    tool_priority_order: List[str] = Field(default_factory=list)
    outcome: Literal["SUCCESS", "FAILURE", "PARTIAL"]
    accuracy_delta: float = 0.0
    cost_delta_tokens: int = 0
    latency_ms: int = 0
    decay_score: float = Field(default=1.0, ge=0.0, le=1.0)
    similarity_embedding: Optional[List[float]] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    use_count: int = 0

    class Config:
        populate_by_name = True


# ── FORENSICS MODELS ──────────────────────────────────────────────────────

class ClaimVariant(BaseModel):
    claim_id: str
    variant_id: str
    platform: Literal["x", "telegram", "reddit", "youtube", "synthetic"]
    variant_type: Literal["original", "dub", "crop", "text_post", "repost", "screenshot"]
    content_text: str
    media_url: Optional[str] = None
    author_handle: Optional[str] = None
    engagement_count: int = 0
    parent_variant_id: Optional[str] = None  # provenance chain for $graphLookup
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class ForensicsReport(BaseModel):
    variant_id: str
    audio_transcript: Optional[str] = None
    audio_fingerprint: Optional[str] = None
    ocr_text: Optional[str] = None
    visual_anomalies: List[str] = Field(default_factory=list)
    audio_visual_sync_score: float = Field(default=1.0, ge=0.0, le=1.0)
    inconsistency_flags: List[str] = Field(default_factory=list)
    raw_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DebateVerdict(BaseModel):
    claim_id: str
    pro_authentic_score: float = Field(ge=0.0, le=1.0)
    pro_fabricated_score: float = Field(ge=0.0, le=1.0)
    pro_authentic_reasoning: str
    pro_fabricated_reasoning: str
    consensus_verdict: Literal["FABRICATED", "AUTHENTIC", "INCONCLUSIVE"]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_hitl: bool = False


class EvidenceItem(BaseModel):
    evidence_type: Literal["audio_artefact", "visual_anomaly", "ocr_mismatch",
                           "metadata_inconsistency", "platform_signal", "prior_pattern"]
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_variant_id: Optional[str] = None


class MLForensicsResult(BaseModel):
    claim_id: str
    spread_velocity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    variant_similarity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    linguistic_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source_credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    template_match_score: float = Field(default=0.5, ge=0.0, le=1.0)
    coordinated_campaign_flag: bool = False
    composite_ml_score: float = Field(default=0.5, ge=0.0, le=1.0)
    ml_flags: List[str] = Field(default_factory=list)
    sub_scores: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClaimVerdict(BaseModel):
    claim_id: str
    claim_text: str
    verdict: Literal["FABRICATED", "AUTHENTIC", "INCONCLUSIVE"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    mutation_graph_summary: Optional[str] = None
    variants_analysed: int = 0
    debate_transcript: Optional[str] = None
    pipeline: Literal["forensics"] = "forensics"
    supply_chain_topics: List[str] = Field(default_factory=list)
    ml_result: Optional[MLForensicsResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None
    ground_truth: Optional[Literal["FABRICATED", "AUTHENTIC"]] = None

    class Config:
        populate_by_name = True


# ── ORACLE MODELS ─────────────────────────────────────────────────────────

class SignalItem(BaseModel):
    signal_type: Literal[
        "geopolitical", "commodity_price", "news", "supplier_filing",
        "claim_verdict", "weather", "sanctions", "port_status"
    ]
    source: str
    headline: str
    content_summary: str
    sentiment: Literal["bullish", "bearish", "neutral"]
    relevance_score: float = Field(ge=0.0, le=1.0)
    is_verified: bool = False
    claim_verdict_id: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialThesis(BaseModel):
    material: Literal["neon", "palladium", "soybeans", "lithium"]
    risk_level: int = Field(ge=0, le=100)
    risk_label: Literal["STABLE", "ELEVATED", "HIGH", "CRITICAL"]
    narrative: str
    key_signals: List[SignalItem] = Field(default_factory=list)
    procurement_recommendation: Optional[str] = None
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None
    triggered_by_claim_verdict_id: Optional[str] = None
    previous_risk_level: Optional[int] = None

    @field_validator("risk_label", mode="before")
    @classmethod
    def derive_label(cls, v, info):
        if "risk_level" in (info.data or {}):
            level = info.data["risk_level"]
            if level >= 80:
                return "CRITICAL"
            elif level >= 60:
                return "HIGH"
            elif level >= 40:
                return "ELEVATED"
            else:
                return "STABLE"
        return v

    class Config:
        populate_by_name = True


class ProcurementAdvisory(BaseModel):
    material: str
    risk_level: int
    risk_label: str
    recommendation: str
    key_signals_summary: List[str] = Field(default_factory=list)
    triggered_by: Literal["threshold_breach", "claim_verdict", "nightly_run"]
    status: Literal["pending_review", "approved", "rejected", "auto_sent"] = "pending_review"
    human_decision: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


# ── SKILL LIBRARY ─────────────────────────────────────────────────────────

class SkillCard(BaseModel):
    agent_type: str
    version: int = 1
    system_prompt: str
    tool_list: List[str] = Field(default_factory=list)
    tool_priority_order: List[str] = Field(default_factory=list)
    planning_instructions: str
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── DPO PAIRS ─────────────────────────────────────────────────────────────

class DPOPair(BaseModel):
    pipeline: Literal["forensics", "oracle"]
    task_type: str
    prompt: str
    chosen: str
    rejected: str
    reward_signal: float
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── SCENARIO TEMPLATES ────────────────────────────────────────────────────

ScenarioCategory = Literal[
    "port_strike", "sanctions", "weather",
    "geopolitical", "financial", "custom"
]


class ScenarioTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=3, max_length=80)
    description: str = Field(default="", max_length=500)
    claim_text: str = Field(min_length=20, max_length=2000)
    category: str = "custom"
    tags: List[str] = Field(default_factory=list)
    created_by: str = "user"
    is_builtin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
