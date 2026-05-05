"""
tools/sources/newsapi_tool.py
NewsAPI — requires NEWSAPI_KEY env var (optional).
Falls back to empty list when key is absent or daily quota is reached.
"""
import os
from typing import List

import aiohttp

from utils.logging import get_logger

log = get_logger(__name__)

_NEWSAPI_URL = "https://newsapi.org/v2/everything"
_TIMEOUT_S = 4
_DAILY_LIMIT = 95

_daily_count: int = 0


async def search(query: str, max_results: int = 25) -> List[dict]:
    """
    Search NewsAPI for articles matching query.

    Returns list of article dicts with: title, description, url, source.name, publishedAt.
    Returns [] if NEWSAPI_KEY is absent or daily limit is reached.
    """
    global _daily_count

    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return []

    if _daily_count >= _DAILY_LIMIT:
        log.warning("NewsAPI daily quota reached — skipping")
        return []

    params = {
        "q": query,
        "pageSize": min(max_results, 25),
        "sortBy": "publishedAt",
        "apiKey": api_key,
        "language": "en",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _NEWSAPI_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=_TIMEOUT_S),
            ) as resp:
                if resp.status == 429:
                    log.warning("NewsAPI rate limited")
                    return []
                if resp.status != 200:
                    log.warning("NewsAPI non-200 response", status=resp.status)
                    return []
                data = await resp.json()
                articles = data.get("articles", [])
                _daily_count += 1
                log.info("NewsAPI search complete", count=len(articles), query=query[:50])
                return articles
    except Exception as e:
        log.warning("NewsAPI search failed", error=str(e))
        return []
