"""
tools/ml/scorer.py
Orchestrate all ML sub-scorers and compose a single MLForensicsResult.
Runs entirely synchronously (CPU-bound, no I/O) — wrap with asyncio.to_thread if needed.
"""
import asyncio
from typing import List

from utils.logging import get_logger

log = get_logger(__name__)


async def score_claim_ml(
    claim_id: str,
    variants: list,
    claim_text: str,
    news_context: dict,
) -> "MLForensicsResult":  # noqa: F821 — imported at call site to avoid circular
    """
    Run all ML sub-scorers and return a composite MLForensicsResult.

    Composite formula:
        composite = 0.25*spread + 0.25*similarity + 0.15*linguistic + 0.15*source_cred + 0.20*template

    coordinated_campaign_flag = spread_velocity > 0.8 AND similarity > 0.75
    """
    from models.schemas import MLForensicsResult
    from tools.ml.spread_velocity import compute_velocity
    from tools.ml.similarity import compute_variant_similarity
    from tools.ml.linguistic import compute_linguistic_features
    from tools.ml.source_credibility import score_sources
    from tools.ml.templates import match_fabrication_templates

    try:
        # Extract texts from variants
        texts: List[str] = []
        for v in variants:
            if hasattr(v, "content_text"):
                texts.append(v.content_text or "")
            elif isinstance(v, dict):
                texts.append(v.get("content_text", ""))
        texts = [t for t in texts if t.strip()]

        # Run all scorers (sync, CPU-bound — run in thread executor)
        loop = asyncio.get_event_loop()

        spread_score, spread_flags = await loop.run_in_executor(
            None, compute_velocity, variants
        )
        sim_score, sim_flags = await loop.run_in_executor(
            None, compute_variant_similarity, texts or [claim_text]
        )
        ling_score, ling_flags = await loop.run_in_executor(
            None, compute_linguistic_features, texts or [claim_text]
        )
        src_score, src_flags = await loop.run_in_executor(
            None, score_sources, news_context
        )
        tmpl_score, tmpl_flags = await loop.run_in_executor(
            None, match_fabrication_templates, claim_text
        )

        # Composite
        composite = round(
            0.25 * spread_score
            + 0.25 * sim_score
            + 0.15 * ling_score
            + 0.15 * src_score
            + 0.20 * tmpl_score,
            3,
        )

        coordinated = spread_score > 0.80 and sim_score > 0.75
        all_flags = spread_flags + sim_flags + ling_flags + src_flags + tmpl_flags

        result = MLForensicsResult(
            claim_id=claim_id,
            spread_velocity_score=spread_score,
            variant_similarity_score=sim_score,
            linguistic_score=ling_score,
            source_credibility_score=src_score,
            template_match_score=tmpl_score,
            coordinated_campaign_flag=coordinated,
            composite_ml_score=composite,
            ml_flags=all_flags,
            sub_scores={
                "spread": spread_score,
                "similarity": sim_score,
                "linguistic": ling_score,
                "source_credibility": src_score,
                "template_match": tmpl_score,
            },
        )

        log.info(
            "ML forensics scored",
            claim_id=claim_id,
            composite=composite,
            coordinated=coordinated,
            flags=len(all_flags),
        )
        return result

    except Exception as e:
        log.error("ML scoring failed — returning safe fallback", claim_id=claim_id, error=str(e))
        from models.schemas import MLForensicsResult
        return MLForensicsResult(
            claim_id=claim_id,
            spread_velocity_score=0.5,
            variant_similarity_score=0.5,
            linguistic_score=0.5,
            source_credibility_score=0.5,
            template_match_score=0.5,
            coordinated_campaign_flag=False,
            composite_ml_score=0.5,
            ml_flags=[f"ML scoring error: {e}"],
            sub_scores={},
        )
