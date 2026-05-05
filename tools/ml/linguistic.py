"""
tools/ml/linguistic.py
Readability, sensationalism, and linguistic uniformity analysis.
Fabricated claims tend to be simple, alarmist, and uniform across variants.
"""
import re
from typing import List, Tuple


def compute_linguistic_features(texts: List[str]) -> Tuple[float, List[str]]:
    """
    Analyse readability and sensationalism signals across variant texts.

    Returns:
        (score, flags) where score 1.0 = high fabrication linguistic signature.
    """
    if not texts:
        return 0.5, []

    flags: List[str] = []
    score_components: List[float] = []

    # ── Readability via textstat ──────────────────────────────────────────
    try:
        import textstat
        grades = [textstat.flesch_kincaid_grade(t) for t in texts if t.strip()]
        if grades:
            import statistics
            mean_grade = statistics.mean(grades)
            std_dev = statistics.stdev(grades) if len(grades) > 1 else 0.0

            # Simple text = sensational content
            if mean_grade < 6.0:
                score_components.append(0.4)
                flags.append(
                    f"Flesch-Kincaid grade {mean_grade:.1f} — unusually simple writing "
                    "(grade-school level = sensationalism/urgency pattern)"
                )
            elif mean_grade < 8.0:
                score_components.append(0.15)

            # Uniform readability across variants = AI-generated consistency
            if std_dev < 0.8 and len(grades) > 2:
                score_components.append(0.3)
                flags.append(
                    f"Variant readability uniformity σ={std_dev:.2f} — "
                    "AI-generated consistency across platforms"
                )

    except ImportError:
        flags.append("textstat unavailable — readability analysis skipped")
    except Exception as e:
        flags.append(f"Readability analysis error: {e}")

    # ── ALL-CAPS ratio ────────────────────────────────────────────────────
    combined = " ".join(texts)
    words = combined.split()
    if words:
        caps_words = [w for w in words if w.isupper() and len(w) > 2]
        caps_ratio = len(caps_words) / len(words)
        if caps_ratio > 0.08:
            score_components.append(0.3)
            flags.append(
                f"High ALL-CAPS ratio {caps_ratio:.0%} — alarm-language pattern "
                "(BREAKING, URGENT, CONFIRMED)"
            )
        elif caps_ratio > 0.04:
            score_components.append(0.1)

    # ── Urgency / absolute language ───────────────────────────────────────
    urgency_patterns = [
        r"\b(BREAKING|URGENT|EXCLUSIVE|DEVELOPING|CONFIRMED|ALERT)\b",
        r"\b(indefinite|immediately|halted|suspended|all\s+\w+\s+stopped)\b",
        r"\b(catastrophic|critical|imminent|devastating|unprecedented)\b",
    ]
    combined_lower = combined.lower()
    urgency_hits = sum(
        1 for p in urgency_patterns if re.search(p, combined, re.IGNORECASE)
    )
    if urgency_hits >= 2:
        score_components.append(0.2)
        flags.append(
            f"Multiple urgency/absolute language patterns ({urgency_hits}/3) — "
            "psychological pressure tactic"
        )

    composite = min(1.0, sum(score_components)) if score_components else 0.3
    return round(composite, 3), flags
