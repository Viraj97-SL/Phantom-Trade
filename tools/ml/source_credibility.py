"""
tools/ml/source_credibility.py
Score fabrication likelihood based on which sources are corroborating the claim.
Low-credibility corroboration = high fabrication signal.
"""
import re
from typing import List, Tuple

from tools.ml.credibility_db import get_credibility


def _extract_domain(outlet_or_url: str) -> str:
    """Extract clean domain from outlet name or URL."""
    cleaned = re.sub(r"https?://(www\.)?", "", outlet_or_url or "").split("/")[0].lower()
    return cleaned.strip()


def score_sources(news_context: dict) -> Tuple[float, List[str]]:
    """
    Score based on which sources are corroborating the claim.

    Returns:
        (score, flags) where score 1.0 = only fringe/unreliable sources corroborate
        (strong fabrication signal), 0.0 = major trusted outlets corroborate (authentic).
    """
    flags: List[str] = []
    corroborating = news_context.get("corroborating_sources", [])

    if not corroborating:
        return 0.7, ["No corroborating coverage found — absence is a fabrication signal"]

    credibility_scores: List[float] = []
    for source in corroborating:
        outlet = source.get("outlet", "") or source.get("url", "")
        domain = _extract_domain(outlet)
        cred = get_credibility(domain)
        credibility_scores.append(cred)

        if cred < 0.40:
            flags.append(
                f"Corroborating source '{domain}' has low credibility score ({cred:.2f}) — "
                "fringe/unreliable outlet"
            )

    mean_cred = sum(credibility_scores) / len(credibility_scores) if credibility_scores else 0.5

    if all(c < 0.50 for c in credibility_scores) and len(credibility_scores) >= 2:
        flags.append(
            "All corroborating sources are fringe/unreliable — "
            "no tier-1 outlet has independently confirmed this claim"
        )

    # score = inverse of mean credibility (low credibility → high fabrication score)
    score = round(max(0.0, min(1.0, 1.0 - mean_cred)), 3)
    return score, flags
