"""
agents/forensics/debate_agent.py
MAD-Sherlock style adversarial debate.
Two LLM agents argue opposite positions; adjudicator produces weighted verdict.
"""
import asyncio
import json
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import DebateVerdict
from utils.llm import get_sonnet
from utils.logging import get_logger

log = get_logger(__name__)

PRO_AUTHENTIC_SYSTEM = """You are a seasoned investigative journalist who believes in verifying before dismissing.
Your role: argue that the supply chain claim being analysed is AUTHENTIC — a real event that happened.

Use ALL available evidence: variants, forensics flags, AND news cross-reference data.
If major outlets ARE covering the event, cite this strongly.
If the source cited in the claim (e.g. Reuters) is verified, cite this.

Output JSON ONLY:
{
  "score": 0.0-1.0,
  "reasoning": "your full argument (2-4 sentences)",
  "key_evidence": ["strongest pro-authentic point 1", "point 2", "point 3"]
}
Score: 1.0 = definitely authentic, 0.0 = no case for authenticity."""

PRO_FABRICATED_SYSTEM = """You are a disinformation researcher specialising in supply chain misinformation.
Your role: argue that the supply chain claim being analysed is FABRICATED — manufactured to move markets.

Use ALL available evidence: variants, forensics flags, AND news cross-reference data.
If zero major outlets cover the event, cite this as a primary red flag.
If the claimed source (e.g. Reuters) cannot be verified, cite this.
Watch for: viral-before-news-pickup, screenshot provenance issues, Telegram bot amplification,
AI-generated augmentation, implausible operational detail, account age/follower anomalies.

Output JSON ONLY:
{
  "score": 0.0-1.0,
  "reasoning": "your full argument (2-4 sentences)",
  "key_evidence": ["strongest pro-fabrication point 1", "point 2", "point 3"]
}
Score: 1.0 = definitely fabricated, 0.0 = no case for fabrication."""


async def run_debate(
    claim_id: str,
    claim_text: str,
    forensics_reports: list,
    variants: list,
    news_context: Optional[dict] = None,
) -> DebateVerdict:
    """Run adversarial debate and return weighted consensus verdict."""
    context = _build_context(claim_text, forensics_reports, variants, news_context)

    auth_task = _run_agent(PRO_AUTHENTIC_SYSTEM, context, "pro_authentic")
    fab_task = _run_agent(PRO_FABRICATED_SYSTEM, context, "pro_fabricated")

    auth_result, fab_result = await asyncio.gather(auth_task, fab_task, return_exceptions=True)

    auth_score = 0.5
    fab_score = 0.5
    auth_reasoning = "Analysis unavailable"
    fab_reasoning = "Analysis unavailable"

    if not isinstance(auth_result, Exception) and auth_result:
        auth_score = float(auth_result.get("score", 0.5))
        auth_reasoning = auth_result.get("reasoning", "")
    if not isinstance(fab_result, Exception) and fab_result:
        fab_score = float(fab_result.get("score", 0.5))
        fab_reasoning = fab_result.get("reasoning", "")

    # Boost fabricated score when there is zero major-outlet coverage
    if news_context and not news_context.get("major_outlets_reporting"):
        fab_score = min(1.0, fab_score + 0.12)
        auth_score = max(0.0, auth_score - 0.08)

    # Fabricated weighted higher (precautionary — false negative is more costly)
    fab_weighted = fab_score * 0.62
    auth_weighted = auth_score * 0.38
    total = fab_weighted + auth_weighted
    fab_probability = fab_weighted / total if total > 0 else 0.5
    confidence = max(auth_score, fab_score)

    if fab_probability >= 0.63:
        consensus = "FABRICATED"
    elif fab_probability <= 0.37:
        consensus = "AUTHENTIC"
    else:
        consensus = "INCONCLUSIVE"

    requires_hitl = 0.43 <= fab_probability <= 0.63 or confidence < 0.68

    verdict = DebateVerdict(
        claim_id=claim_id,
        pro_authentic_score=round(auth_score, 3),
        pro_fabricated_score=round(fab_score, 3),
        pro_authentic_reasoning=auth_reasoning,
        pro_fabricated_reasoning=fab_reasoning,
        consensus_verdict=consensus,
        confidence=round(confidence, 3),
        requires_hitl=requires_hitl,
    )

    log.info("Debate complete",
             claim_id=claim_id, consensus=consensus,
             confidence=verdict.confidence, hitl_required=requires_hitl)
    return verdict


async def _run_agent(system_prompt: str, context: str, agent_name: str) -> dict:
    llm = get_sonnet()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=context),
        ])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception as e:
        log.error("Debate agent failed", agent=agent_name, error=str(e))
        return {"score": 0.5, "reasoning": f"Analysis failed: {e}", "key_evidence": []}


def _build_context(
    claim_text: str,
    forensics_reports: list,
    variants: list,
    news_context: Optional[dict] = None,
) -> str:
    variant_lines = "\n".join(
        f"  [{i+1}] Platform={v.get('platform')} Type={v.get('variant_type')} "
        f"Engagement={v.get('engagement_count', 0):,} "
        f"BotProb={v.get('metadata', {}).get('bot_probability', 'n/a')} "
        f"| Text: {str(v.get('content_text', ''))[:120]}"
        for i, v in enumerate(variants[:6])
    )

    report_lines = "\n".join(
        f"  [{i+1}] CredibilityScore={r.get('audio_visual_sync_score', 0.5):.2f} "
        f"| Flags: {'; '.join(r.get('inconsistency_flags', ['none'])[:4])}"
        for i, r in enumerate(forensics_reports[:6])
    ) if forensics_reports else "  No forensics available."

    news_block = ""
    if news_context:
        src = news_context.get("source_claimed")
        src_verified = news_context.get("source_claimed_verified")
        src_line = f"\n  Claimed source '{src}' verified in archive: {src_verified}" if src else ""
        corr = news_context.get("corroborating_sources", [])
        contra = news_context.get("contradicting_sources", [])
        fab_sigs = news_context.get("fabrication_signals", [])
        news_block = (
            f"\nNEWS CROSS-REFERENCE (CRITICAL EVIDENCE):\n"
            f"  Summary: {news_context.get('summary', 'N/A')}\n"
            f"  Major outlets reporting (Reuters/Bloomberg/BBC/FT/AP): "
            f"{news_context.get('major_outlets_reporting', False)}{src_line}\n"
            f"  Corroborating ({len(corr)}): "
            f"{', '.join(r.get('outlet', '') for r in corr[:3]) or 'NONE'}\n"
            f"  Contradicting ({len(contra)}): "
            f"{'; '.join(r.get('title', '')[:50] for r in contra[:2]) or 'none'}\n"
            f"  Fabrication signals:\n"
            + ("\n".join(f"    - {s}" for s in fab_sigs[:5]) if fab_sigs else "    none detected")
        )

        ml = news_context.get("ml_result")
        if ml:
            ml_flags = ml.get("ml_flags", [])[:5]
            news_block += (
                f"\n\nML FORENSICS SIGNALS (composite={ml.get('composite_ml_score', 0.5):.2f}, "
                f"coordinated={ml.get('coordinated_campaign_flag', False)}):\n"
                + ("\n".join(f"    - {f}" for f in ml_flags) if ml_flags else "    none")
            )

    return (
        f'CLAIM TO ANALYSE:\n"{claim_text}"\n\n'
        f"VARIANTS FOUND ({len(variants)} across platforms):\n{variant_lines}\n\n"
        f"LLM FORENSICS REPORTS ({len(forensics_reports)} variants analysed):\n{report_lines}\n"
        f"{news_block}\n\n"
        f"Provide your analysis as JSON only. Weigh the news cross-reference heavily."
    )
