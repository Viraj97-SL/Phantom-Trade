"""
tools/sources/rss_tool.py
RSS feed parser for major financial and news outlets.
No API key required — uses public RSS feeds.
"""
import asyncio
from typing import Dict, List, Optional

import aiohttp

from utils.logging import get_logger

log = get_logger(__name__)

_RSS_FEEDS: Dict[str, str] = {
    "reuters": "https://feeds.reuters.com/reuters/businessNews",
    "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "ap_business": "https://rsshub.app/apnews/topics/business",
    "bloomberg_markets": "https://feeds.bloomberg.com/markets/news.rss",
    "ft_markets": "https://www.ft.com/markets?format=rss",
}

_TIMEOUT_S = 5
_UA = "PhantomTrade/1.0 (supply-chain-disinformation-research)"


async def _fetch_feed(
    name: str, url: str, session: aiohttp.ClientSession
) -> List[dict]:
    """Fetch and parse a single RSS feed. Returns list of item dicts on success, [] on failure."""
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=_TIMEOUT_S)
        ) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()

        import feedparser  # soft dependency
        feed = feedparser.parse(text)
        items: List[dict] = []
        for entry in feed.entries[:20]:
            items.append(
                {
                    "title": getattr(entry, "title", ""),
                    "url": getattr(entry, "link", ""),
                    "description": getattr(entry, "summary", "")[:300],
                    "published": getattr(entry, "published", ""),
                    "source_name": name,
                }
            )
        return items
    except Exception as e:
        log.warning("RSS feed fetch failed", feed=name, error=str(e))
        return []


async def search(
    query: str, keywords: Optional[List[str]] = None
) -> List[dict]:
    """
    Search all configured RSS feeds for items matching query keywords.

    If keywords is None, derives them from query words longer than 3 chars.
    Returns matching items with: title, url, description, published, source_name.
    """
    if keywords is None:
        keywords = [w.lower() for w in query.split() if len(w) > 3]

    try:
        async with aiohttp.ClientSession(headers={"User-Agent": _UA}) as session:
            tasks = [
                _fetch_feed(name, url, session)
                for name, url in _RSS_FEEDS.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        log.warning("RSS fan-out failed", error=str(e))
        return []

    all_items: List[dict] = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    matched = [
        item
        for item in all_items
        if any(
            kw in (item.get("title", "") + " " + item.get("description", "")).lower()
            for kw in keywords
        )
    ]

    log.info(
        "RSS search complete",
        total_fetched=len(all_items),
        matched=len(matched),
        query=query[:50],
    )
    return matched
