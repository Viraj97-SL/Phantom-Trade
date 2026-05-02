"""
db/indexes.py
Creates all non-vector compound indexes programmatically.
Vector search indexes are created in Atlas UI (already done).
Run once: python -m db.indexes
"""
import asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel
from db.connection import get_db, ping_db
from utils.logging import get_logger

log = get_logger(__name__)


async def create_all_indexes() -> None:
    db = get_db()

    # ── agent_sessions (TTL already set in Atlas UI) ────────────────────
    await db.agent_sessions.create_indexes([
        IndexModel([("agent_id", ASCENDING), ("session_type", ASCENDING)]),
    ])
    log.info("agent_sessions indexes created")

    # ── agent_knowledge ──────────────────────────────────────────────────
    await db.agent_knowledge.create_indexes([
        IndexModel([("entity_type", ASCENDING), ("valid_to", ASCENDING)]),
        IndexModel([("entity", ASCENDING)]),
        IndexModel([("valid_from", DESCENDING)]),
    ])
    log.info("agent_knowledge indexes created")

    # ── reasoning_bank ───────────────────────────────────────────────────
    await db.reasoning_bank.create_indexes([
        IndexModel([("material", ASCENDING), ("pipeline", ASCENDING), ("decay_score", DESCENDING)]),
        IndexModel([("task_signature", ASCENDING), ("outcome", ASCENDING)]),
        IndexModel([("decay_score", ASCENDING)]),
        IndexModel([("last_used_at", DESCENDING)]),
    ])
    log.info("reasoning_bank indexes created")

    # ── skill_library ────────────────────────────────────────────────────
    await db.skill_library.create_indexes([
        IndexModel([("agent_type", ASCENDING), ("version", DESCENDING)]),
    ])
    log.info("skill_library indexes created")

    # ── claim_variants (TTL already set in Atlas UI) ─────────────────────
    await db.claim_variants.create_indexes([
        IndexModel([("claim_id", ASCENDING), ("platform", ASCENDING)]),
        IndexModel([("claim_id", ASCENDING), ("variant_type", ASCENDING)]),
    ])
    log.info("claim_variants indexes created")

    # ── claim_verdicts ───────────────────────────────────────────────────
    await db.claim_verdicts.create_indexes([
        IndexModel([("verdict", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("claim_id", ASCENDING)], unique=True),
        IndexModel([("pipeline", ASCENDING)]),
    ])
    log.info("claim_verdicts indexes created")

    # ── material_thesis (bi-temporal) ────────────────────────────────────
    await db.material_thesis.create_indexes([
        IndexModel([("material", ASCENDING), ("valid_from", DESCENDING), ("valid_to", ASCENDING)]),
        IndexModel([("material", ASCENDING), ("valid_to", ASCENDING)]),
        IndexModel([("risk_level", DESCENDING)]),
    ])
    log.info("material_thesis indexes created")

    # ── agent_checkpoints ────────────────────────────────────────────────
    await db.agent_checkpoints.create_indexes([
        IndexModel([("thread_id", ASCENDING), ("checkpoint_id", DESCENDING)]),
    ])
    log.info("agent_checkpoints indexes created")

    # ── procurement_advisories ───────────────────────────────────────────
    await db.procurement_advisories.create_indexes([
        IndexModel([("material", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])
    log.info("procurement_advisories indexes created")

    log.info("All compound indexes created successfully")


async def main():
    ok = await ping_db()
    if not ok:
        log.error("Cannot reach MongoDB Atlas  -  check MONGODB_URI in .env")
        return
    await create_all_indexes()
    log.info("Index setup complete")


if __name__ == "__main__":
    asyncio.run(main())
