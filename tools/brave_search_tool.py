"""
tools/brave_search_tool.py
News signal retrieval for Oracle pipeline.
Uses Tavily as primary (key was mislabeled as Brave). Falls back gracefully.
Keeps the original brave_news_search signature for backward compatibility.
"""
from typing import List
from langchain_core.tools import tool
from utils.logging import get_logger

log = get_logger(__name__)


async def brave_news_search(query: str, count: int = 5) -> List[dict]:
    """
    Search for recent news. Uses Tavily (primary) with graceful fallback.
    Returns list of {title, url, description, age, source} dicts.
    """
    from tools.tavily_search_tool import tavily_search
    try:
        raw = await tavily_search(query, max_results=count, topic="news")
        results = [
            {
                "title": r["title"],
                "url": r["url"],
                "description": r["content"],
                "age": r.get("published_date", ""),
                "source": "tavily_news",
            }
            for r in raw
        ]
        log.info("News search completed", query=query[:50], results=len(results))
        return results
    except Exception as e:
        log.warning("News search failed", error=str(e))
        return []


@tool
async def search_supply_chain_news(material: str) -> str:
    """
    Search for recent supply chain news about a material.
    Returns formatted news results for LLM consumption.
    """
    queries = [
        f"{material} supply chain disruption 2026",
        f"{material} price shortage mine strike",
    ]
    all_results: List[dict] = []
    for q in queries[:2]:
        results = await brave_news_search(q, count=3)
        all_results.extend(results)

    if not all_results:
        return f"No recent news found for {material} supply chain."

    formatted = f"Recent {material} supply chain news:\n\n"
    for i, r in enumerate(all_results[:5], 1):
        formatted += f"{i}. {r['title']}\n   {r['description'][:150]}\n   Source: {r['url']}\n\n"
    return formatted


@tool
async def search_port_disruption_news(port_name: str) -> str:
    """Search for recent port disruption news."""
    results = await brave_news_search(
        f"{port_name} port strike disruption closure 2026", count=5
    )
    if not results:
        return f"No recent disruption news found for {port_name} port."
    formatted = f"Recent {port_name} port news:\n\n"
    for i, r in enumerate(results[:4], 1):
        formatted += f"{i}. {r['title']}\n   {r['description'][:150]}\n\n"
    return formatted
