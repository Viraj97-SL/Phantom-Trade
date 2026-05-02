"""
tools/commodity_price_tool.py
Commodity price signal tool for Oracle pipeline.
Uses public FRED API (free, no key needed for most series).
"""
import httpx
from typing import Optional
from langchain_core.tools import tool
from utils.logging import get_logger

log = get_logger(__name__)

# FRED series IDs for tracked materials (free, public)
FRED_SERIES = {
    "soybeans": "PSOYBUSDM",     # Soybeans price USD/metric ton
    "palladium": "PPALLASDM",    # Palladium price USD/troy oz
    "lithium": "LITHIUMPRICE",   # Lithium carbonate price
}

FRED_BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


async def get_commodity_price(material: str) -> Optional[dict]:
    """Fetch latest commodity price from FRED."""
    series_id = FRED_SERIES.get(material.lower())
    if not series_id:
        log.warning("No FRED series for material", material=material)
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                FRED_BASE_URL,
                params={"id": series_id, "vintage_date": ""},
            )
            response.raise_for_status()
            lines = response.text.strip().split("\n")
            # Last line is most recent
            if len(lines) >= 2:
                latest = lines[-1].split(",")
                prev = lines[-2].split(",") if len(lines) >= 3 else lines[-1].split(",")
                date, price = latest[0], latest[1]
                prev_price = prev[1]
                price_float = float(price) if price != "." else None
                prev_float = float(prev_price) if prev_price != "." else None
                change = None
                if price_float and prev_float:
                    change = round(((price_float - prev_float) / prev_float) * 100, 2)
                result = {
                    "material": material,
                    "price": price_float,
                    "date": date,
                    "change_pct": change,
                    "source": "FRED",
                }
                # Persist to time-series collection (non-blocking)
                if price_float is not None:
                    try:
                        from utils.metrics import store_price_point
                        await store_price_point(material, price_float, change, date)
                    except Exception:
                        pass
                return result
    except Exception as e:
        log.warning("FRED fetch failed", material=material, error=str(e))
        return None


@tool
async def get_material_price_signal(material: str) -> str:
    """
    Get latest commodity price signal for a material.
    Returns formatted price info for LLM analysis.
    """
    data = await get_commodity_price(material)
    if not data:
        return f"Price data unavailable for {material}. Use news signals instead."

    direction = "▲" if (data.get("change_pct") or 0) > 0 else "▼"
    return (
        f"{material.upper()} Price Signal:\n"
        f"  Latest: ${data['price']:,.2f} ({data['date']})\n"
        f"  Change: {direction} {abs(data.get('change_pct', 0))}% from previous period\n"
        f"  Source: {data['source']}\n"
    )
