"""
tools/x_api_tool.py
X (Twitter) API v2 tool  -  claim search for Forensics pipeline.
Falls back to synthetic data if bearer token not set.
"""
import httpx
from typing import List, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
from config.settings import settings
from utils.logging import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

log = get_logger(__name__)
X_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=5, max=30))
async def search_recent_tweets(query: str, max_results: int = 10) -> List[dict]:
    """Search X API v2 for recent tweets matching a query."""
    if not settings.x_bearer_token:
        log.warning("X Bearer token not set  -  returning empty")
        return []

    headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
    params = {
        "query": f"{query} -is:retweet lang:en",
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "username,verified",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(X_SEARCH_URL, headers=headers, params=params)
        if response.status_code == 429:
            raise Exception("X API rate limited")
        response.raise_for_status()
        data = response.json()

    tweets = []
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    for tweet in data.get("data", []):
        author = users.get(tweet.get("author_id", ""), {})
        metrics = tweet.get("public_metrics", {})
        tweets.append({
            "tweet_id": tweet["id"],
            "text": tweet["text"],
            "author": author.get("username", "unknown"),
            "verified": author.get("verified", False),
            "retweet_count": metrics.get("retweet_count", 0),
            "like_count": metrics.get("like_count", 0),
            "reply_count": metrics.get("reply_count", 0),
            "created_at": tweet.get("created_at", ""),
            "platform": "x",
        })

    log.info("X search completed", query=query[:50], results=len(tweets))
    return tweets


@tool
async def search_supply_chain_claim_x(claim_keywords: str) -> str:
    """
    Search X for posts matching supply chain claim keywords.
    Returns formatted results for LLM analysis.
    """
    tweets = await search_recent_tweets(claim_keywords, max_results=10)
    if not tweets:
        return f"No recent X posts found matching: {claim_keywords}"

    formatted = f"X posts matching '{claim_keywords}':\n\n"
    for i, t in enumerate(tweets[:5], 1):
        formatted += (
            f"{i}. @{t['author']} {'[VERIFIED]' if t['verified'] else ''}\n"
            f"   {t['text'][:200]}\n"
            f"   Engagement: {t['retweet_count']} RTs, {t['like_count']} likes\n\n"
        )
    return formatted
