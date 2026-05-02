"""
memory/long_term.py
Long-term memory — bi-temporal knowledge facts.
Every fact has valid_from / valid_to for time-travel queries.
"""
from datetime import datetime
from typing import Optional, List
from db.connection import get_db
from models.schemas import KnowledgeFact
from utils.logging import get_logger

log = get_logger(__name__)


async def upsert_fact(entity: str, entity_type: str, facts: dict,
                      confidence: float, source_session_id: str) -> None:
    """Insert a new fact version. Old version gets valid_to=now."""
    db = get_db()
    now = datetime.utcnow()

    # Close existing active fact for this entity
    await db.agent_knowledge.update_many(
        {"entity": entity, "valid_to": None},
        {"$set": {"valid_to": now}}
    )

    # Insert new version
    fact = KnowledgeFact(
        entity=entity,
        entity_type=entity_type,
        facts=facts,
        valid_from=now,
        valid_to=None,
        confidence=confidence,
        source_session_ids=[source_session_id],
        last_updated=now,
    )
    await db.agent_knowledge.insert_one(fact.model_dump())
    log.info("Knowledge fact upserted", entity=entity, confidence=confidence)


async def get_fact(entity: str, as_of: Optional[datetime] = None) -> Optional[KnowledgeFact]:
    """Get the fact valid at a given point in time (defaults to now)."""
    db = get_db()
    as_of = as_of or datetime.utcnow()
    doc = await db.agent_knowledge.find_one({
        "entity": entity,
        "valid_from": {"$lte": as_of},
        "$or": [{"valid_to": None}, {"valid_to": {"$gt": as_of}}]
    })
    if doc:
        doc.pop("_id", None)
        return KnowledgeFact(**doc)
    return None


async def get_facts_by_type(entity_type: str, limit: int = 20) -> List[KnowledgeFact]:
    """Get all currently active facts of a given type."""
    db = get_db()
    cursor = db.agent_knowledge.find(
        {"entity_type": entity_type, "valid_to": None}
    ).limit(limit)
    facts = []
    async for doc in cursor:
        doc.pop("_id", None)
        facts.append(KnowledgeFact(**doc))
    return facts


async def get_fact_history(entity: str) -> List[KnowledgeFact]:
    """Get full version history for an entity — for the bi-temporal demo slider."""
    db = get_db()
    cursor = db.agent_knowledge.find(
        {"entity": entity}
    ).sort("valid_from", -1)
    history = []
    async for doc in cursor:
        doc.pop("_id", None)
        history.append(KnowledgeFact(**doc))
    return history


async def search_facts(query_text: str, limit: int = 10) -> List[KnowledgeFact]:
    """Text search over currently valid facts."""
    db = get_db()
    cursor = db.agent_knowledge.find(
        {"$text": {"$search": query_text}, "valid_to": None}
    ).limit(limit)
    facts = []
    async for doc in cursor:
        doc.pop("_id", None)
        facts.append(KnowledgeFact(**doc))
    return facts
