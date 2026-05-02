"""
tests/test_connection.py
First tests to run — verifies all external connections work.
Run: pytest tests/test_connection.py -v
"""
import asyncio
import pytest
from db.connection import ping_db, get_db
from utils.llm import get_haiku
from utils.logging import setup_logging

setup_logging()


@pytest.mark.asyncio
async def test_mongodb_ping():
    """MongoDB Atlas is reachable."""
    result = await ping_db()
    assert result is True, "MongoDB Atlas ping failed — check MONGODB_URI in .env"


@pytest.mark.asyncio
async def test_collections_exist():
    """All required collections exist in phantom_trade database."""
    db = get_db()
    collections = await db.list_collection_names()
    required = [
        "agent_sessions", "agent_knowledge", "reasoning_bank",
        "skill_library", "claim_variants", "claim_verdicts",
        "material_thesis", "agent_checkpoints", "dpo_pairs",
    ]
    for coll in required:
        assert coll in collections, f"Collection '{coll}' missing from phantom_trade database"


@pytest.mark.asyncio
async def test_llm_basic():
    """LLM (Bedrock or Anthropic fallback) responds."""
    llm = get_haiku()
    response = await llm.ainvoke("Reply with exactly: PHANTOM_TRADE_OK")
    assert "PHANTOM_TRADE_OK" in response.content, f"Unexpected LLM response: {response.content}"


@pytest.mark.asyncio
async def test_seed_data_exists():
    """Seed data has been loaded into the database."""
    db = get_db()
    thesis_count = await db.material_thesis.count_documents({"valid_to": None})
    assert thesis_count >= 4, f"Expected 4 material theses, found {thesis_count}. Run: python -m db.seed_data"

    rb_count = await db.reasoning_bank.count_documents({})
    assert rb_count >= 5, f"Expected reasoning bank entries, found {rb_count}. Run: python -m db.seed_data"
