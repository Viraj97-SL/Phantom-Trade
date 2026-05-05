"""
tools/ml/templates.py
Fabrication template pattern matching.
Known structural patterns that appear in market-manipulation disinformation.
"""
import re
from typing import List, Tuple

# (pattern, weight, description)
_PATTERNS: List[tuple] = [
    (
        r"^BREAKING[\s:]",
        0.25,
        "BREAKING prefix — standard fabrication template opener",
    ),
    (
        r"\bSources?\s*:\s*(Reuters|Bloomberg|BBC|FT|Financial Times|Associated Press|AP|WSJ|CNBC)\b",
        0.30,
        "Unverifiable source attribution — prestigious outlet cited without URL",
    ),
    (
        r"#\w+[\s]+#\w+",
        0.15,
        "Multiple hashtag cluster — viral amplification / trending manipulation pattern",
    ),
    (
        r"\b(URGENT|CONFIRMED|EXCLUSIVE|DEVELOPING|ALERT)\b",
        0.15,
        "Urgency keyword — psychological pressure tactic to bypass scepticism",
    ),
    (
        r"\b(indefinite(ly)?|immediate(ly)?|all\s+\w+\s+(halted|suspended|stopped|banned))\b",
        0.15,
        "Absolute disruption language — over-claim pattern typical in fabricated crises",
    ),
]


def match_fabrication_templates(claim_text: str) -> Tuple[float, List[str]]:
    """
    Check claim_text against weighted fabrication template patterns.

    Returns:
        (score, flags) where score 1.0 = matches all templates (definite fabrication pattern).
        Score is sum of matched pattern weights, clamped to [0, 1].
    """
    flags: List[str] = []
    total_weight = 0.0

    for pattern, weight, description in _PATTERNS:
        if re.search(pattern, claim_text, re.IGNORECASE | re.MULTILINE):
            total_weight += weight
            flags.append(description)

    score = min(1.0, total_weight)

    if score >= 0.6:
        flags.insert(0, f"High template match score ({score:.2f}) — claim follows known fabrication structure")

    return round(score, 3), flags
