"""
utils/metrics.py
Write agent performance and commodity price data to MongoDB time-series collections.
Both calls are fire-and-forget — errors are caught and logged, never raised.
"""
from datetime import datetime, timezone
from typing import Optional
from utils.logging import get_logger

log = get_logger(__name__)


async def record_agent_metric(
    agent_id: str,
    pipeline: str,
    outcome: str,
    latency_ms: int,
    confidence: Optional[float] = None,
    material: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Insert one document into agent_metrics_ts."""
    try:
        from db.connection import get_db
        db = get_db()
        doc = {
            "timestamp": datetime.now(tz=timezone.utc),
            "metadata": {
                "agent_id": agent_id,
                "pipeline": pipeline,
                "material": material,
            },
            "latency_ms": latency_ms,
            "outcome": outcome,
            "confidence": confidence,
        }
        if extra:
            doc.update(extra)
        await db.agent_metrics_ts.insert_one(doc)
    except Exception as exc:
        log.warning("agent_metrics_ts write failed", agent_id=agent_id, error=str(exc))


async def store_price_point(
    material: str,
    price: float,
    change_pct: Optional[float],
    fred_date: str,
) -> None:
    """Insert one document into commodity_prices_ts."""
    try:
        from db.connection import get_db
        db = get_db()
        await db.commodity_prices_ts.insert_one({
            "timestamp": datetime.now(tz=timezone.utc),
            "metadata": {"material": material, "source": "FRED"},
            "price": price,
            "change_pct": change_pct,
            "fred_date": fred_date,
        })
    except Exception as exc:
        log.warning("commodity_prices_ts write failed", material=material, error=str(exc))