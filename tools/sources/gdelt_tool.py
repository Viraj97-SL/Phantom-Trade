"""
tools/sources/gdelt_tool.py
GDELT v2 Doc API — free, no API key required.
Queries global news coverage for a keyword and timespan.
"""
from typing import List

import aiohttp

from utils.logging import get_logger

log = get_logger(__name__)

_GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_TIMEOUT_S = 4


async def search(query: str, timespan: str = "1d", max_results: int = 25) -> List[dict]:
    """
    Search GDELT for articles matching query in the given timespan.

    Returns list of raw article dicts with keys: url, domain, seendate, title,
    sourcecountry, language, tone.
    Returns [] on any error or timeout.
    """
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_results),
        "timespan": timespan,
        "sort": "DateDesc",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _GDELT_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=_TIMEOUT_S),
            ) as resp:
                if resp.status != 200:
                    log.warning("GDELT non-200 response", status=resp.status, query=query[:50])
                    return []
                data = await resp.json(content_type=None)
                articles = data.get("articles", [])
                log.info("GDELT search complete", count=len(articles), query=query[:50])
                return articles
    except asyncio.TimeoutError:
        log.warning("GDELT request timed out", query=query[:50])
        return []
    except Exception as e:
        log.warning("GDELT search failed", error=str(e), query=query[:50])
        return []


import asyncio  # noqa: E402  (needed for TimeoutError reference above)