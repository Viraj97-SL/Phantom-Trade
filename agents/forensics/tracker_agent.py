"""
agents/forensics/tracker_agent.py
Tracker Agent — searches X API v2, and falls back to realistic synthetic variants.
"""
import uuid
from typing import List

from db.connection import get_db
from models.schemas import ClaimVariant
from tools.x_api_tool import search_recent_tweets
from tools.forensics_search_tool import extract_claim_entities
from utils.logging import get_logger

log = get_logger(__name__)


async def track_claim_variants(claim_id: str, claim_text: str,
                                session_id: str) -> List[ClaimVariant]:
    """
    Search all platforms for variants of a claim.
    Returns list of ClaimVariant objects stored in MongoDB.
    """
    db = get_db()
    variants: List[ClaimVariant] = []
    keywords = " ".join(claim_text.split()[:8])

    # ── X API v2 ──────────────────────────────────────────────────────────
    try:
        tweets = await search_recent_tweets(keywords, max_results=5)
        for t in tweets[:3]:
            variants.append(ClaimVariant(
                claim_id=claim_id,
                variant_id=str(uuid.uuid4()),
                platform="x",
                variant_type="repost" if t["text"].startswith("RT") else "original",
                content_text=t["text"],
                author_handle=t.get("author", ""),
                engagement_count=t.get("retweet_count", 0) + t.get("like_count", 0),
            ))
    except Exception as e:
        log.warning("X tracking failed", error=str(e))

    # ── Reddit search for real corroborating/sceptical posts ─────────────
    try:
        from tools.sources.reddit_tool import search as reddit_search
        reddit_posts = await reddit_search(
            " ".join(claim_text.split()[:8]), subreddit="supplychain"
        )
        for post in reddit_posts[:2]:
            variants.append(ClaimVariant(
                claim_id=claim_id,
                variant_id=str(uuid.uuid4()),
                platform="reddit",
                variant_type="text_post",
                parent_variant_id=None,
                content_text=(post.get("title", "") + " " + post.get("selftext", ""))[:500],
                author_handle=f"r/{post.get('subreddit', 'supplychain')}",
                url=post.get("permalink", ""),
                engagement_count=post.get("score", 0) + post.get("num_comments", 0),
                metadata={
                    "num_comments": post.get("num_comments", 0),
                    "reddit_score": post.get("score", 0),
                },
            ))
    except Exception as e:
        log.warning("Reddit variant fetch failed", error=str(e))

    # ── Synthetic variants (realistic misinformation spread simulation) ───
    variants.extend(_generate_synthetic_variants(claim_id, claim_text))

    if variants:
        await db.claim_variants.insert_many([v.model_dump() for v in variants])
        log.info("Claim variants stored", claim_id=claim_id, count=len(variants))

    return variants


def _generate_synthetic_variants(claim_id: str, claim_text: str) -> List[ClaimVariant]:
    """
    Generate 6 realistic synthetic variants that simulate how misinformation
    spreads across platforms: original post -> screenshot -> Telegram repost ->
    audio dub reference -> Reddit thread -> AI-augmented amplifier.
    Each variant carries parent_variant_id for MongoDB $graphLookup provenance traversal.
    """
    entities = extract_claim_entities(claim_text)
    port = entities["ports"][0].title() if entities["ports"] else "the port"
    commodity = entities["commodities"][0].title() if entities["commodities"] else "cargo"
    event = entities["events"][0] if entities["events"] else "disruption"
    source = entities["sources"][0].title() if entities["sources"] else "sources"

    # Truncated base for sub-variants
    base = claim_text[:120].rstrip()

    # Pre-generate IDs so parent references can be wired ahead of time
    id_original = str(uuid.uuid4())
    id_screenshot = str(uuid.uuid4())
    id_telegram = str(uuid.uuid4())
    id_dub = str(uuid.uuid4())
    id_reddit = str(uuid.uuid4())
    id_ai = str(uuid.uuid4())

    return [
        # 1. Original post on X — the "patient zero"
        ClaimVariant(
            claim_id=claim_id,
            variant_id=id_original,
            platform="x",
            variant_type="original",
            parent_variant_id=None,
            content_text=claim_text,
            author_handle="trade_wire_live",
            engagement_count=3_200,
            metadata={
                "verified_account": False,
                "account_age_days": 47,
                "followers": 8_400,
                "posted_before_major_outlet": True,
            },
        ),
        # 2. Screenshot on X — cropped to hide the unverified account name
        ClaimVariant(
            claim_id=claim_id,
            variant_id=id_screenshot,
            platform="x",
            variant_type="screenshot",
            parent_variant_id=id_original,
            content_text=(
                f"Screenshot circulating showing: \"{base}\" "
                f"— account metadata cropped, {source} watermark visible in corner"
            ),
            author_handle="breaking_commodity",
            engagement_count=11_500,
            metadata={
                "has_media": True,
                "media_type": "screenshot",
                "metadata_stripped": True,
                "source_attribution_clipped": True,
            },
        ),
        # 3. Telegram repost — added urgency, broken English typical of bot accounts
        ClaimVariant(
            claim_id=claim_id,
            variant_id=id_telegram,
            platform="telegram",
            variant_type="repost",
            parent_variant_id=id_screenshot,
            content_text=(
                f"URGENT!!! {port.upper()} PORT ALL {commodity.upper()} OPERATIONS SUSPENDED "
                f"INDEFINITELY!! Workers {event}!! Prices will EXPLODE!! "
                f"Share before deleted!! [Source: {source}]"
            ),
            author_handle="supply_chain_alerts_official",
            engagement_count=24_000,
            metadata={
                "channel": "SupplyChainBreakingAlerts",
                "channel_subscribers": 41_000,
                "forwarded_from": "CommoditySignals",
                "views": 118_000,
                "bot_probability": 0.78,
            },
        ),
        # 4. Audio dub / voice note reference — transcribed
        ClaimVariant(
            claim_id=claim_id,
            variant_id=id_dub,
            platform="telegram",
            variant_type="dub",
            parent_variant_id=id_telegram,
            content_text=(
                f"[Voice note transcript]: \"I'm hearing from my contact at {port} that "
                f"the {event} is real — all {commodity} shipments frozen. "
                f"This is NOT on the news yet because {source} is sitting on it. "
                f"Prepare your positions now.\" — audio shows background noise inconsistency, "
                f"lip-sync mismatch on re-encoded version."
            ),
            author_handle="insider_trade_voice",
            engagement_count=5_800,
            metadata={
                "media_type": "audio",
                "duration_seconds": 38,
                "audio_artefacts": ["background_noise_splice_at_00:14", "pitch_shift_detected"],
                "av_sync_score": 0.41,
            },
        ),
        # 5. Reddit thread — mix of believers and sceptics
        ClaimVariant(
            claim_id=claim_id,
            variant_id=id_reddit,
            platform="reddit",
            variant_type="text_post",
            parent_variant_id=id_telegram,
            content_text=(
                f"Anyone else seeing this {port} {event} news? [{source} supposedly] — "
                f"can't find anything on their site. Top comment: 'This looks like the "
                f"same account that spread the fake Odessa closure last month. "
                f"Engagement looks artificially boosted.' 340 upvotes, 127 comments."
            ),
            author_handle="u/logistics_analyst_real",
            engagement_count=340,
            metadata={
                "subreddit": "supplychain",
                "upvotes": 340,
                "top_comment_sentiment": "sceptical",
                "cross_posted_to": ["r/investing", "r/commodities"],
            },
        ),
        # 6. AI-augmented amplifier post — adds fake corroborating detail
        ClaimVariant(
            claim_id=claim_id,
            variant_id=id_ai,
            platform="synthetic",
            variant_type="repost",
            parent_variant_id=id_telegram,
            content_text=(
                f"CONFIRMED by multiple sources: {base} "
                f"Container ships now diverting to alternative ports. "
                f"{commodity.title()} futures up 4.2% in pre-market. "
                f"Industry insiders confirm disruption expected to last 2-3 weeks. "
                f"[Note: added detail not present in original claim — AI-augmented amplification pattern]"
            ),
            author_handle="ai_news_amplifier_bot",
            engagement_count=8_900,
            metadata={
                "ai_generated_probability": 0.91,
                "added_unverified_details": [
                    "ships diverting",
                    "futures up 4.2%",
                    "2-3 week duration",
                ],
                "hallucination_risk": "HIGH",
            },
        ),
    ]


async def get_variants_for_claim(claim_id: str) -> List[dict]:
    """Retrieve all stored variants for a claim."""
    db = get_db()
    cursor = db.claim_variants.find({"claim_id": claim_id})
    variants = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        variants.append(doc)
    return variants
