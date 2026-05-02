"""
tools/tavily_search_tool.py
Tavily web/news search for PHANTOM TRADE.
Primary news source for both Forensics pipeline and Oracle signal retrieval.
"""
import os
import httpx
from typing import List
from utils.logging import get_logger

log = get_logger(__name__)

TAVILY_BASE = "https://api.tavily.com/search"


async def tavily_search(query: str, max_results: int = 5, topic: str = "news") -> List[dict]:
    """
    Search Tavily for recent news articles.
    Returns list of {title, url, content, score, published_date}.
    Raises ValueError if TAVILY_API_KEY not set.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set")

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "topic": topic,
        "include_answer": False,
        "search_depth": "basic",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(TAVILY_BASE, json=payload)
        response.raise_for_status()
        data = response.json()

    results = []
    for r in data.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:500],
            "score": r.get("score", 0.5),
            "published_date": r.get("published_date", ""),
        })

    log.info("Tavily search completed", query=query[:60], results=len(results))
    return results
