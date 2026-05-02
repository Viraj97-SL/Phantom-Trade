"""
memory/reasoning_bank.py
Reasoning memory — the RL improvement layer.
Stores strategy cards with decay scoring, similarity embeddings, outcome tracking.
This is what makes agents visibly improve over time.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from db.connection import get_db
from models.schemas import ReasoningEntry
from utils.logging import get_logger
import numpy as np

log = get_logger(__name__)

# Thresholds
SIMILARITY_THRESHOLD = 0.75
FRESHNESS_THRESHOLD = 0.5
ACCURACY_FLOOR = 0.6
DECAY_RATE = 0.98
DECAY_FLOOR = 0.3


async def store_entry(entry: ReasoningEntry) -> str:
    """Store a new reasoning bank entry after task completion."""
    db = get_db()
    doc = entry.model_dump()
    result = await db.reasoning_bank.insert_one(doc)
    log.info(
        "ReasoningBank entry stored",
        task_signature=entry.task_signature,
        outcome=entry.outcome,
        accuracy_delta=entry.accuracy_delta,
    )
    return str(result.inserted_id)


async def retrieve_strategies(
    task_signature: str,
    embedding: Optional[List[float]] = None,
    material: Optional[str] = None,
    pipeline: Optional[str] = None,
    top_k: int = 5,
) -> List[ReasoningEntry]:
    """
    Retrieve top-k relevant strategies from reasoning bank.
    Uses vector similarity if embedding provided, else text match.
    Applies decay and similarity threshold gates.
    """
    db = get_db()

    if embedding:
        # Vector search pipeline
        pipeline_stages = [
            {
                "$vectorSearch": {
                    "index": "reasoning_vector",
                    "path": "similarity_embedding",
                    "queryVector": embedding,
                    "numCandidates": top_k * 10,
                    "limit": top_k * 3,
                    "filter": {"decay_score": {"$gt": DECAY_FLOOR}}
                }
            },
            {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            {"$match": {"score": {"$gte": SIMILARITY_THRESHOLD}}},
            {"$sort": {"accuracy_delta": -1}},
            {"$limit": top_k},
        ]

        if material:
            pipeline_stages[0]["$vectorSearch"]["filter"]["material"] = material
        if pipeline:
            pipeline_stages[0]["$vectorSearch"]["filter"]["pipeline"] = pipeline

        cursor = db.reasoning_bank.aggregate(pipeline_stages)
    else:
        # Fallback: text match + decay filter
        query: dict = {
            "task_signature": {"$regex": task_signature[:20], "$options": "i"},
            "decay_score": {"$gt": DECAY_FLOOR},
        }
        if material:
            query["material"] = material
        if pipeline:
            query["pipeline"] = pipeline

        cursor = db.reasoning_bank.find(query).sort("accuracy_delta", -1).limit(top_k)

    entries = []
    async for doc in cursor:
        doc.pop("_id", None)
        doc.pop("score", None)
        entry = ReasoningEntry(**doc)
        if _passes_quality_gates(entry):
            entries.append(entry)

    log.info(
        "ReasoningBank retrieved",
        task_signature=task_signature[:30],
        entries_found=len(entries),
    )
    return entries


def _passes_quality_gates(entry: ReasoningEntry) -> bool:
    """Anti-degradation gates — prevent bad traces from compounding."""
    if entry.decay_score < DECAY_FLOOR:
        return False
    return True


async def update_on_use(entry_id_or_signature: str) -> None:
    """Mark an entry as used — boosts recency, increments use_count."""
    db = get_db()
    await db.reasoning_bank.update_one(
        {"task_signature": entry_id_or_signature},
        {
            "$set": {"last_used_at": datetime.utcnow()},
            "$inc": {"use_count": 1},
        }
    )


async def run_nightly_decay() -> dict:
    """
    Nightly decay job — called by scheduler.
    1. Decay all scores by DECAY_RATE
    2. Prune entries below DECAY_FLOOR
    3. Boost recently used entries
    Returns summary stats.
    """
    db = get_db()
    now = datetime.utcnow()
    cutoff = now - timedelta(days=7)

    # Step 1: Decay all
    decay_result = await db.reasoning_bank.update_many(
        {"decay_score": {"$gt": 0.0}},
        {"$mul": {"decay_score": DECAY_RATE}}
    )

    # Step 2: Prune below floor
    prune_result = await db.reasoning_bank.delete_many(
        {"decay_score": {"$lt": DECAY_FLOOR}}
    )

    # Step 3: Boost recently used (cap at 1.0)
    boost_result = await db.reasoning_bank.update_many(
        {"last_used_at": {"$gt": cutoff}, "decay_score": {"$lt": 1.0}},
        {"$mul": {"decay_score": 1.05}}
    )

    # Cap at 1.0
    await db.reasoning_bank.update_many(
        {"decay_score": {"$gt": 1.0}},
        {"$set": {"decay_score": 1.0}}
    )

    stats = {
        "decayed": decay_result.modified_count,
        "pruned": prune_result.deleted_count,
        "boosted": boost_result.modified_count,
        "timestamp": now.isoformat(),
    }
    log.info("ReasoningBank nightly decay complete", **stats)
    return stats


async def get_bank_stats(pipeline: Optional[str] = None) -> dict:
    """Get summary stats for demo dashboard — shows the bank growing."""
    db = get_db()
    query = {}
    if pipeline:
        query["pipeline"] = pipeline

    total = await db.reasoning_bank.count_documents(query)
    success = await db.reasoning_bank.count_documents({**query, "outcome": "SUCCESS"})
    avg_accuracy = 0.0

    pipeline_agg = [
        {"$match": {**query, "outcome": "SUCCESS"}},
        {"$group": {"_id": None, "avg_accuracy": {"$avg": "$accuracy_delta"}}}
    ]
    async for doc in db.reasoning_bank.aggregate(pipeline_agg):
        avg_accuracy = round(doc.get("avg_accuracy", 0.0), 3)

    return {
        "total_entries": total,
        "successful_entries": success,
        "avg_accuracy_delta": avg_accuracy,
        "hit_rate": round(success / total, 2) if total > 0 else 0.0,
    }
