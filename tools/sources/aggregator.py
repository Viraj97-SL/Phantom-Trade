"""
tools/sources/aggregator.py
Parallel multi-source news aggregator.
Fans out to GDELT, NewsAPI, RSS, Reddit, and Tavily simultaneously.
Merges, deduplicates, and classifies results into a unified AggregatedNewsContext.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import List, Optional

from utils.logging import get_logger
from tools.forensics_search_tool import extract_claim_entities, MAJOR_OUTLETS

log = get_logger(__name__)

# Extended major-outlet set — adds 14 quality international outlets to the existing 11
EXPANDED_MAJOR_OUTLETS: frozenset[str] = frozenset(MAJOR_OUTLETS) | frozenset({
    "economist.com",
    "axios.com",
    "semafor.com",
    "politico.com",
    "foreignpolicy.com",
    "dw.com",
    "aljazeera.com",
    "scmp.com",
    "japantimes.co.jp",
    "nikkei.com",
    "gulfnews.com",
    "lemonde.fr",
    "spiegel.de",
    "handelsblatt.com",
    "freightwaves.com",
    "joc.com",
    "lloydslist.com",
    "supplychaindive.com",
    "tradewindsnews.com",
})


@dataclass
class AggregatedNewsContext:
    corroborating_sources: List[dict] = field(default_factory=list)
    contradicting_sources: List[dict] = field(default_factory=list)
    total_coverage: int = 0
    major_outlets_reporting: bool = False
    source_claimed: Optional[str] = None
    source_claimed_verified: Optional[bool] = None
    fabrication_signals: List[str] = field(default_factory=list)
    summary: str = ""
    # New enriched fields
    gdelt_event_count: int = 0
    rss_corroboration: int = 0
    wayback_verified: Optional[bool] = None
    reddit_sentiment: str = "absent"
    sources_breakdown: dict = field(default_factory=dict)


def _extract_domain(url_or_outlet: str) -> str:
    return re.sub(r"https?://(www\.)?", "", (url_or_outlet or "")).split("/")[0].lower().strip()


def _is_major(domain: str) -> bool:
    return any(m in domain for m in EXPANDED_MAJOR_OUTLETS)


def _classify_reddit_sentiment(posts: List[dict]) -> str:
    if not posts:
        return "absent"
    _SCEPTICAL = {"fake", "false", "debunked", "misleading", "unconfirmed", "hoax", "rumour", "rumor"}
    _SUPPORTIVE = {"confirmed", "breaking", "real", "true", "verified", "official"}
    sceptical = supportive = 0
    for p in posts:
        text = (p.get("title", "") + " " + p.get("selftext", "")).lower()
        if any(w in text for w in _SCEPTICAL):
            sceptical += 1
        if any(w in text for w in _SUPPORTIVE):
            supportive += 1
    if sceptical == 0 and supportive == 0:
        return "mixed"
    return "sceptical" if sceptical > supportive else "supportive" if supportive > sceptical else "mixed"


async def fan_out_search(
    claim_text: str,
    entities: Optional[dict] = None,
) -> AggregatedNewsContext:
    """
    Fan out news search to all configured sources in parallel with per-source timeouts.
    Results are merged, deduplicated by (domain, title[:50]), and classified.
    """
    from tools.sources import gdelt_tool, newsapi_tool, rss_tool, reddit_tool, wayback_tool
    from tools.tavily_search_tool import tavily_search

    if entities is None:
        entities = extract_claim_entities(claim_text)

    ports = entities.get("ports", [])
    commodities = entities.get("commodities", [])
    events = entities.get("events", [])
    sources = entities.get("sources", [])

    parts = (ports + commodities + events)[:3]
    query = " ".join(parts) if parts else claim_text[:100]
    keywords = [p.lower() for p in parts if p]

    async def _safe(coro, name: str):
        try:
            return await asyncio.wait_for(coro, timeout=5.0)
        except Exception as exc:
            log.warning("Source failed", source=name, error=str(exc))
            return []

    gdelt_raw, newsapi_raw, rss_raw, reddit_raw, tavily_raw = await asyncio.gather(
        _safe(gdelt_tool.search(query), "gdelt"),
        _safe(newsapi_tool.search(query), "newsapi"),
        _safe(rss_tool.search(query, keywords=keywords), "rss"),
        _safe(reddit_tool.search(query), "reddit"),
        _safe(tavily_search(query, max_results=8, topic="news"), "tavily"),
    )

    ctx = AggregatedNewsContext()
    ctx.gdelt_event_count = len(gdelt_raw)
    ctx.reddit_sentiment = _classify_reddit_sentiment(reddit_raw)

    seen: set[tuple] = set()
    all_hits: List[dict] = []

    def _add_hit(hit: dict, source_tag: str) -> None:
        key = (_extract_domain(hit.get("url", hit.get("outlet", ""))), hit.get("title", "")[:50])
        if key not in seen:
            seen.add(key)
            all_hits.append({**hit, "_source": source_tag})

    # Normalise GDELT
    for item in gdelt_raw:
        domain = _extract_domain(item.get("url", ""))
        _add_hit({
            "title": item.get("title", ""),
            "outlet": domain,
            "url": item.get("url", ""),
            "age": item.get("seendate", ""),
            "is_major": _is_major(domain),
            "description": f"tone={item.get('tone','?')} country={item.get('sourcecountry','?')}",
        }, "gdelt")

    # Normalise NewsAPI
    for item in newsapi_raw:
        url = item.get("url", "")
        domain = _extract_domain(url)
        _add_hit({
            "title": item.get("title", ""),
            "outlet": item.get("source", {}).get("name", domain),
            "url": url,
            "age": item.get("publishedAt", ""),
            "is_major": _is_major(domain),
            "description": (item.get("description") or "")[:200],
        }, "newsapi")

    # Normalise RSS
    for item in rss_raw:
        url = item.get("url", "")
        domain = _extract_domain(url)
        _add_hit({
            "title": item.get("title", ""),
            "outlet": item.get("source_name", domain),
            "url": url,
            "age": item.get("published", ""),
            "is_major": _is_major(domain),
            "description": item.get("description", "")[:200],
        }, "rss")

    ctx.rss_corroboration = sum(1 for h in all_hits if h.get("_source") == "rss")

    # Normalise Tavily
    for item in tavily_raw:
        url = item.get("url", "")
        domain = _extract_domain(url)
        _add_hit({
            "title": item.get("title", ""),
            "outlet": domain,
            "url": url,
            "age": item.get("published_date", ""),
            "is_major": _is_major(domain),
            "description": (item.get("content") or "")[:200],
        }, "tavily")

    # Classify hits into corroborating vs contradicting
    for hit in all_hits:
        title_lower = hit.get("title", "").lower()
        hit_count = sum(1 for kw in (ports + commodities) if kw in title_lower)
        has_event = any(kw in title_lower for kw in events) if events else hit_count >= 3
        if hit_count >= 2 and has_event:
            ctx.corroborating_sources.append(hit)
        else:
            ctx.contradicting_sources.append(hit)

    ctx.total_coverage = len(all_hits)
    ctx.major_outlets_reporting = any(h.get("is_major") for h in ctx.corroborating_sources)

    # Wayback verification for claimed source
    source_claimed = sources[0].title() if sources else None
    ctx.source_claimed = source_claimed
    if source_claimed:
        domain_to_check = source_claimed.lower().replace(" ", "") + ".com"
        try:
            wb = await asyncio.wait_for(wayback_tool.verify_url(domain_to_check), timeout=3.5)
            ctx.wayback_verified = wb.found
        except Exception:
            ctx.wayback_verified = None
        ctx.source_claimed_verified = any(
            source_claimed.lower() in h.get("outlet", "").lower()
            for h in ctx.corroborating_sources
        )

    # Build fabrication signals
    source_count = len({h.get("_source") for h in all_hits})
    signals: List[str] = [
        f"Aggregated {ctx.total_coverage} results from {source_count} sources "
        f"(GDELT:{len(gdelt_raw)}, RSS:{len(rss_raw)}, NewsAPI:{len(newsapi_raw)}, "
        f"Reddit:{len(reddit_raw)}, Tavily:{len(tavily_raw)})."
    ]
    if not ctx.major_outlets_reporting:
        signals.append(
            "Zero major-outlet corroboration across all sources — strong fabrication indicator."
        )
    else:
        major_n = sum(1 for h in ctx.corroborating_sources if h.get("is_major"))
        signals.append(f"{major_n} major outlet(s) corroborating.")
    if ctx.gdelt_event_count == 0:
        signals.append(
            "GDELT global news database: zero event mentions — event not in global news record."
        )
    if ctx.reddit_sentiment == "sceptical":
        signals.append("Reddit supply-chain community flagging claim as sceptical/false.")
    if source_claimed and not ctx.source_claimed_verified:
        signals.append(
            f"Claimed source '{source_claimed}' not found in any corroborating results."
        )

    ctx.fabrication_signals = signals
    ctx.summary = " ".join(signals)
    ctx.sources_breakdown = {
        "gdelt": len(gdelt_raw),
        "newsapi": len(newsapi_raw),
        "rss": len(rss_raw),
        "reddit": len(reddit_raw),
        "tavily": len(tavily_raw),
    }

    log.info(
        "Aggregator fan-out complete",
        total=ctx.total_coverage,
        corroborating=len(ctx.corroborating_sources),
        major=ctx.major_outlets_reporting,
    )
    return ctx
