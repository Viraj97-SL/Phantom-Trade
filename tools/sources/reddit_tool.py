"""
tools/sources/reddit_tool.py
Reddit public JSON API — no authentication required for public search.
Searches supply-chain-relevant subreddits for corroboration or scepticism.
"""
from typing import List, Optional

import aiohttp

from utils.logging import get_logger

log = get_logger(__name__)

_SEARCH_URL = "https://www.reddit.com/search.json"
_TIMEOUT_S = 4
_DEFAULT_SUBREDDITS = "supplychain+investing+worldnews+commodities+economics"
_USER_AGENT = (
    "PhantomTrade/1.0 (supply-chain-disinformation-research; "
    "contact: research@phantomtrade.example.com)"
)


async def search(
    query: str,
    subreddit: Optional[str] = None,
    max_results: int = 25,
) -> List[dict]:
    """
    Search Reddit for posts matching query.

    Returns list of post dicts: title, url, selftext, subreddit, score,
    num_comments, created_utc, permalink.
    Returns [] on any failure or rate limit.
    """
    params = {
        "q": query,
        "sort": "new",
        "limit": min(max_results, 25),
        "type": "link,self",
    }

    if subreddit:
        search_url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params["restrict_sr"] = "1"
    else:
        search_url = _SEARCH_URL

    try:
        async with aiohttp.ClientSession(headers={"User-Agent": _USER_AGENT}) as session:
            async with session.get(
                search_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=_TIMEOUT_S),
            ) as resp:
                if resp.status == 429:
                    log.warning("Reddit rate limited")
                    return []
                if resp.status != 200:
                    log.warning("Reddit non-200 response", status=resp.status)
                    return []
                data = await resp.json()

        children = data.get("data", {}).get("children", [])
        results: List[dict] = []
        for child in children:
            d = child.get("data", {})
            results.append(
                {
                    "title": d.get("title", ""),
                    "url": d.get("url", ""),
                    "selftext": (d.get("selftext") or "")[:300],
                    "subreddit": d.get("subreddit", ""),
                    "score": d.get("score", 0),
                    "num_comments": d.get("num_comments", 0),
                    "created_utc": d.get("created_utc", 0),
                    "permalink": f"https://reddit.com{d.get('permalink', '')}",
                }
            )
        log.info("Reddit search complete", count=len(results), query=query[:50])
        return results
    except Exception as e:
        log.warning("Reddit search failed", error=str(e))
        return []
