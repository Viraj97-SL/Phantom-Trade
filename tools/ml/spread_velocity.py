"""
tools/ml/spread_velocity.py
Analyse cross-platform spread speed as a fabrication signal.
Authentic news spreads over hours; fabricated claims appear simultaneously across platforms.
"""
from datetime import datetime
from typing import List, Tuple


def compute_velocity(variants: list) -> Tuple[float, List[str]]:
    """
    Compute spread velocity score from variant timestamps.

    Returns:
        (score, flags) where score 1.0 = anomalously fast (fabrication signal),
        0.0 = normal organic spread.
    """
    timestamps: List[datetime] = []
    for v in variants:
        ts = None
        if hasattr(v, "created_at"):
            ts = v.created_at
        elif isinstance(v, dict):
            ts = v.get("created_at")
        if isinstance(ts, datetime):
            timestamps.append(ts)

    if len(timestamps) < 2:
        return 0.5, []

    timestamps.sort()
    flags: List[str] = []

    # Pairwise minimum delta in minutes
    min_delta_minutes = float("inf")
    max_delta_minutes = 0.0
    for i in range(len(timestamps) - 1):
        delta = (timestamps[i + 1] - timestamps[i]).total_seconds() / 60.0
        min_delta_minutes = min(min_delta_minutes, delta)
        max_delta_minutes = max(max_delta_minutes, delta)

    total_span_minutes = (timestamps[-1] - timestamps[0]).total_seconds() / 60.0

    # Score: closer to 0 minutes apart → closer to 1.0 (anomalous)
    # Baseline: authentic news spans >6h (360 min) across platforms
    score = max(0.0, min(1.0, 1.0 - (min_delta_minutes / 360.0)))

    if min_delta_minutes < 30:
        flags.append(
            f"All variants posted within {min_delta_minutes:.0f} minutes — "
            "coordinated campaign signature"
        )
    if total_span_minutes < 120 and len(timestamps) >= 3:
        flags.append(
            f"Entire cross-platform spread within {total_span_minutes:.0f} minutes — "
            "anomalous velocity (authentic news typically spans 6+ hours)"
        )
    if min_delta_minutes < 5:
        flags.append(
            "Near-simultaneous posting across platforms — automated/bot distribution likely"
        )

    return round(score, 3), flags
