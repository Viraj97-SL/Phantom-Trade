"""
agents/forensics/orchestrator.py
Forensics Pipeline Orchestrator.
Coordinates: Tracker → News Cross-Ref → LLM Forensics → MutationGraph → Debate → Verdict
"""
import asyncio
import json
import uuid
from typing import Optional, List

from langsmith import traceable

from db.connection import get_db
from agents.forensics.tracker_agent import track_claim_variants, get_variants_for_claim
from agents.forensics.debate_agent import run_debate
from models.schemas import ClaimVariant, ClaimVerdict, EvidenceItem, ForensicsReport
from tools.forensics_search_tool import search_claim_in_news
from utils.llm import get_haiku
from utils.logging import get_logger
from middleware.guardrails import check_prompt_injection
from langchain_core.messages import HumanMessage, SystemMessage

log = get_logger(__name__)

_FORENSICS_SYSTEM = """Disinformation forensics analyst. Return ONLY this JSON (no other text):
{"inconsistency_flags":["flag1"],"credibility_score":0.0,"source_attribution_valid":null,"viral_anomaly":false,"key_finding":"one sentence"}
credibility_score: 1.0=credible, 0.0=fabricated. Be concise."""


@traceable(name="forensics_analyse_claim")
async def analyse_claim(claim_text: str, media_url: Optional[str] = None) -> ClaimVerdict:
    """Full Forensics pipeline for a single claim. Returns a ClaimVerdict stored in MongoDB."""
    claim_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    db = get_db()
    log.info("Forensics pipeline started", claim_id=claim_id)

    # ── Safety check ──────────────────────────────────────────────────────
    try:
        check_prompt_injection(claim_text)
    except ValueError as e:
        log.warning("Claim rejected  -  prompt injection", error=str(e))
        return _build_inconclusive_verdict(claim_id, claim_text, str(e))

    # ── STEP 1: Track variants ────────────────────────────────────────────
    variants = await track_claim_variants(claim_id, claim_text, session_id)
    log.info("Variants tracked", claim_id=claim_id, count=len(variants))

    # ── STEP 2: News cross-reference ──────────────────────────────────────
    topics = _classify_supply_chain_topics(claim_text)
    news_context = await search_claim_in_news(claim_text, topics)
    log.info("News cross-reference complete",
             major_outlets=news_context.get("major_outlets_reporting"),
             total_coverage=news_context.get("total_coverage"))

    # ── STEP 3: LLM forensics on each variant ────────────────────────────
    forensics_reports = await _run_llm_forensics(variants, claim_text, news_context)

    # ── STEP 4: Mutation graph (MongoDB $graphLookup provenance traversal) ───
    mutation_summary = await _build_mutation_graph_summary(claim_id, variants, news_context)

    # ── STEP 5: MAD-Sherlock debate with full context ────────────────────
    variant_dicts = [v.model_dump() for v in variants]
    report_dicts = [r.model_dump() for r in forensics_reports]

    debate_verdict = await run_debate(
        claim_id=claim_id,
        claim_text=claim_text,
        forensics_reports=report_dicts,
        variants=variant_dicts,
        news_context=news_context,
    )

    # ── STEP 6: Build evidence items ─────────────────────────────────────
    evidence = _build_evidence(forensics_reports, news_context)

    # ── STEP 7: Write ClaimVerdict to MongoDB ─────────────────────────────
    verdict = ClaimVerdict(
        claim_id=claim_id,
        claim_text=claim_text,
        verdict=debate_verdict.consensus_verdict,
        confidence=debate_verdict.confidence,
        evidence=evidence,
        mutation_graph_summary=mutation_summary,
        variants_analysed=len(variants),
        debate_transcript=(
            f"PRO-AUTHENTIC ({debate_verdict.pro_authentic_score:.2f}): "
            f"{debate_verdict.pro_authentic_reasoning[:300]}\n\n"
            f"PRO-FABRICATED ({debate_verdict.pro_fabricated_score:.2f}): "
            f"{debate_verdict.pro_fabricated_reasoning[:300]}"
        ),
        supply_chain_topics=topics,
    )

    await db.claim_verdicts.insert_one(verdict.model_dump())
    log.info("Claim verdict written",
             claim_id=claim_id, verdict=verdict.verdict, confidence=verdict.confidence)

    # Store audit artifact in S3 (non-blocking)
    try:
        from utils.s3 import store_forensics_artifact
        await store_forensics_artifact(claim_id, verdict.model_dump())
    except Exception:
        pass

    return verdict


def _extract_json(text: str) -> dict:
    """
    Robustly extract JSON from an LLM response.
    Tries: code block → braces scan → partial repair.
    """
    import re
    text = text.strip()
    # Strip markdown code fences
    if "```" in text:
        blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if blocks:
            text = blocks[0].strip()
    # Find first { ... } block
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")
    # Walk to find matching brace, tolerating truncation
    depth = 0
    end = start
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    else:
        # Truncated JSON  -  attempt to close open braces
        text = text[start:] + "}" * depth
        return json.loads(text)
    return json.loads(text[start:end + 1])


async def _run_llm_forensics(
    variants: List[ClaimVariant],
    claim_text: str,
    news_context: dict,
) -> List[ForensicsReport]:
    """
    Use Gemini Haiku to analyse each variant for credibility signals.
    Runs all variants in parallel for speed.
    """
    llm = get_haiku()
    news_summary = news_context.get("summary", "No news cross-reference available.")
    fabrication_signals = news_context.get("fabrication_signals", [])
    news_block = (
        f"NEWS CROSS-REFERENCE:\n{news_summary}\n"
        + ("\n".join(f"- {s}" for s in fabrication_signals) if fabrication_signals else "")
    )

    async def analyse_one(variant: ClaimVariant) -> ForensicsReport:
        meta = variant.metadata or {}
        prompt = (
            f'Claim: "{claim_text[:200]}"\n'
            f"Platform:{variant.platform} Type:{variant.variant_type} "
            f"Engagement:{variant.engagement_count:,} Author:{variant.author_handle or 'unknown'}\n"
            f"Text:{variant.content_text[:200]}\n"
            f"Meta:{json.dumps({k: v for k, v in meta.items() if k not in ('views','channel')}, default=str)[:200]}\n"
            f"{news_block[:400]}\nReturn JSON only."
        )

        try:
            response = await llm.ainvoke([
                SystemMessage(content=_FORENSICS_SYSTEM),
                HumanMessage(content=prompt),
            ])
            result = _extract_json(response.content)
        except Exception as e:
            log.warning("LLM forensics failed for variant", error=str(e),
                        variant_id=variant.variant_id)
            result = {
                "inconsistency_flags": ["LLM analysis unavailable"],
                "credibility_score": 0.5,
                "source_attribution_valid": None,
                "viral_anomaly": variant.engagement_count > 10_000,
                "key_finding": "Analysis fallback  -  pattern-based only",
            }

        # Supplement with pattern-based flags
        flags: List[str] = list(result.get("inconsistency_flags", []))
        credibility: float = float(result.get("credibility_score", 0.5))
        text_lower = variant.content_text.lower()

        if variant.variant_type == "screenshot":
            flags.append("Screenshot variant  -  metadata stripped, provenance unclear")
            credibility -= 0.1
        if variant.variant_type == "dub":
            av_score = float(meta.get("av_sync_score", 1.0))
            if av_score < 0.6:
                flags.append(f"Audio-visual sync score {av_score:.2f}  -  splice/dub likely")
                credibility -= 0.25
        if variant.engagement_count > 20_000 and variant.platform in ("telegram",):
            flags.append(f"Viral on Telegram ({variant.engagement_count:,} views) before major outlet pickup")
            credibility -= 0.1
        if meta.get("bot_probability", 0) > 0.6:
            flags.append(f"High bot probability ({meta['bot_probability']:.0%}) on posting account")
            credibility -= 0.15
        if meta.get("ai_generated_probability", 0) > 0.7:
            flags.append("AI-generated content detected  -  hallucinated corroborating details")
            credibility -= 0.2
        if not news_context.get("major_outlets_reporting"):
            flags.append("Zero major outlet corroboration (Reuters, Bloomberg, BBC, FT, AP)")
        src = news_context.get("source_claimed")
        if src and news_context.get("source_claimed_verified") is False and src.lower() in text_lower:
            flags.append(f"Claim attributes to {src} but no matching article found in their archive")
            credibility -= 0.2

        key_finding = result.get("key_finding", "")
        if key_finding:
            flags.insert(0, key_finding)

        sync_score = max(0.0, min(1.0, credibility))
        return ForensicsReport(
            variant_id=variant.variant_id,
            inconsistency_flags=list(dict.fromkeys(flags)),  # deduplicate
            audio_visual_sync_score=sync_score,
            raw_confidence=1.0 - sync_score,
        )

    tasks = [analyse_one(v) for v in variants]
    reports = await asyncio.gather(*tasks, return_exceptions=True)

    clean: List[ForensicsReport] = []
    for i, r in enumerate(reports):
        if isinstance(r, Exception):
            log.warning("Forensics report failed", index=i, error=str(r))
            clean.append(ForensicsReport(
                variant_id=variants[i].variant_id,
                inconsistency_flags=["Analysis error"],
                audio_visual_sync_score=0.5,
                raw_confidence=0.5,
            ))
        else:
            clean.append(r)
    return clean


def _build_evidence(reports: List[ForensicsReport], news_context: dict) -> List[EvidenceItem]:
    """Consolidate evidence items from forensics reports + news cross-reference."""
    evidence: List[EvidenceItem] = []

    for report in reports:
        for flag in report.inconsistency_flags[:3]:  # top 3 per variant
            etype = (
                "audio_artefact" if any(w in flag.lower() for w in ("audio", "av sync", "dub", "sync"))
                else "visual_anomaly" if any(w in flag.lower() for w in ("screenshot", "visual", "image"))
                else "metadata_inconsistency" if any(w in flag.lower() for w in ("metadata", "bot", "ai-generated"))
                else "platform_signal" if any(w in flag.lower() for w in ("viral", "telegram", "engagement"))
                else "platform_signal"
            )
            evidence.append(EvidenceItem(
                evidence_type=etype,
                description=flag,
                confidence=1.0 - report.audio_visual_sync_score,
                source_variant_id=report.variant_id,
            ))

    # Add news cross-reference as evidence
    if not news_context.get("major_outlets_reporting"):
        evidence.append(EvidenceItem(
            evidence_type="prior_pattern",
            description="No major outlet (Reuters, Bloomberg, BBC, FT, AP) coverage of this event",
            confidence=0.82,
        ))
    src = news_context.get("source_claimed")
    if src and news_context.get("source_claimed_verified") is False:
        evidence.append(EvidenceItem(
            evidence_type="metadata_inconsistency",
            description=f"Claim attributes to {src} but no matching article found in archive",
            confidence=0.88,
        ))

    return evidence[:10]  # cap at 10 items


async def _build_mutation_graph_summary(
    claim_id: str, variants: List[ClaimVariant], news_context: dict
) -> str:
    """
    Traverse the provenance chain via MongoDB $graphLookup and build a narrative.
    Falls back to text-only summary if graph traversal fails.
    """
    try:
        db = get_db()
        # $graphLookup: start from root variants (no parent) and traverse children
        pipeline = [
            {"$match": {"claim_id": claim_id, "parent_variant_id": None}},
            {
                "$graphLookup": {
                    "from": "claim_variants",
                    "startWith": "$variant_id",
                    "connectFromField": "variant_id",
                    "connectToField": "parent_variant_id",
                    "as": "propagation_chain",
                    "maxDepth": 10,
                    "depthField": "depth",
                }
            },
        ]
        roots = await db.claim_variants.aggregate(pipeline).to_list(length=10)
        if roots:
            root = roots[0]
            chain = sorted(root.get("propagation_chain", []), key=lambda x: x.get("depth", 0))
            platforms = [root["platform"]] + [n["platform"] for n in chain]
            platforms_dedup = list(dict.fromkeys(platforms))
            max_eng_node = max(
                [root] + chain, key=lambda x: x.get("engagement_count", 0)
            )
            total_eng = sum(n.get("engagement_count", 0) for n in [root] + chain)
            depth = len(chain)
            path_desc = " -> ".join(
                f"{n.get('platform')}({n.get('variant_type')})"
                for n in ([root] + chain)[:6]
            )
            news_note = (
                " No major news outlet has reported this event."
                if not news_context.get("major_outlets_reporting")
                else " Official sources contradict the claim."
                if news_context.get("contradicting_sources")
                else ""
            )
            log.info("Mutation graph traversed via $graphLookup",
                     claim_id=claim_id, depth=depth, platforms=platforms_dedup)
            return (
                f"Provenance graph ({depth + 1} nodes, depth {depth}): {path_desc}. "
                f"Spread across {len(platforms_dedup)} platforms ({', '.join(platforms_dedup)}). "
                f"Total engagement: {total_eng:,}. "
                f"Peak amplification: {max_eng_node.get('platform')} "
                f"({max_eng_node.get('engagement_count', 0):,} interactions).{news_note}"
            )
    except Exception as exc:
        log.warning("$graphLookup mutation traversal failed, using text fallback",
                    claim_id=claim_id, error=str(exc))
    return _build_mutation_summary(variants, news_context)


def _build_mutation_summary(variants: List[ClaimVariant], news_context: dict) -> str:
    platforms = list(dict.fromkeys(v.platform for v in variants))
    types = list(dict.fromkeys(v.variant_type for v in variants))
    total_eng = sum(v.engagement_count for v in variants)
    max_eng = max((v.engagement_count for v in variants), default=0)
    max_platform = next(
        (v.platform for v in variants if v.engagement_count == max_eng), "unknown"
    )

    news_note = ""
    if not news_context.get("major_outlets_reporting"):
        news_note = " No major news outlet has reported this event."
    elif news_context.get("contradicting_sources"):
        news_note = f" Official sources contradict the claim."

    return (
        f"Claim detected on {len(platforms)} platforms ({', '.join(platforms)}) "
        f"with {len(variants)} variants ({', '.join(types)}). "
        f"Total cross-platform engagement: {total_eng:,}. "
        f"Peak propagation on {max_platform} ({max_eng:,} interactions). "
        f"Spread pattern: Original post → Screenshot → Telegram amplification → Reddit scepticism.{news_note}"
    )


def _classify_supply_chain_topics(claim_text: str) -> List[str]:
    text = claim_text.lower()
    topic_keywords = {
        "port": ["port", "harbour", "harbor", "dock", "shipping", "vessel", "cargo", "container"],
        "soybeans": ["soybean", "soy", "grain", "oilseed"],
        "neon": ["neon", "semiconductor", "chip", "ukraine", "odessa"],
        "palladium": ["palladium", "catalytic", "russia", "south africa", "autocatalyst"],
        "lithium": ["lithium", "battery", "ev", "electric vehicle", "chile", "argentina"],
        "strike": ["strike", "workers", "labour", "labor", "union", "walkout"],
        "sanctions": ["sanction", "embargo", "export ban", "trade restriction"],
        "geopolitical": ["war", "conflict", "invasion", "military", "blockade"],
    }
    topics = [topic for topic, keywords in topic_keywords.items()
              if any(kw in text for kw in keywords)]
    return topics if topics else ["supply_chain_general"]


def _build_inconclusive_verdict(claim_id: str, claim_text: str,
                                reason: str) -> ClaimVerdict:
    return ClaimVerdict(
        claim_id=claim_id,
        claim_text=claim_text,
        verdict="INCONCLUSIVE",
        confidence=0.0,
        supply_chain_topics=[],
    )


async def get_recent_verdicts(limit: int = 10) -> List[dict]:
    db = get_db()
    cursor = db.claim_verdicts.find().sort("created_at", -1).limit(limit)
    verdicts = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        verdicts.append(doc)
    return verdicts
