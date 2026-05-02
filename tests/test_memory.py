"""
tests/test_memory.py
Tests for all three memory layers.
Run: pytest tests/test_memory.py -v
"""
import pytest
from datetime import datetime, timedelta
from memory import short_term, long_term, reasoning_bank
from models.schemas import ReasoningEntry
from utils.logging import setup_logging

setup_logging()


@pytest.mark.asyncio
async def test_short_term_create_and_retrieve():
    session = await short_term.create_session(
        agent_id="test_agent",
        session_type="oracle_run",
        material="soybeans",
    )
    assert session.session_id is not None
    assert session.current_phase == "PLAN"

    retrieved = await short_term.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.active_material == "soybeans"

    await short_term.expire_session(session.session_id)


@pytest.mark.asyncio
async def test_short_term_phase_transition():
    session = await short_term.create_session("test_agent", "oracle_run")
    await short_term.set_phase(session.session_id, "ACT")
    updated = await short_term.get_session(session.session_id)
    assert updated.current_phase == "ACT"
    await short_term.expire_session(session.session_id)


@pytest.mark.asyncio
async def test_long_term_upsert_and_retrieve():
    entity = "test_entity_pytest"
    await long_term.upsert_fact(
        entity=entity,
        entity_type="test_type",
        facts={"key": "value", "score": 0.9},
        confidence=0.9,
        source_session_id="test_session",
    )
    fact = await long_term.get_fact(entity)
    assert fact is not None
    assert fact.entity == entity
    assert fact.facts["key"] == "value"
    assert fact.valid_to is None  # currently active


@pytest.mark.asyncio
async def test_long_term_bitemporal():
    """Verify bi-temporal: old version closed, new version active."""
    entity = "test_bitemporal_pytest"

    await long_term.upsert_fact(entity, "test_type", {"version": 1}, 0.7, "s1")
    await long_term.upsert_fact(entity, "test_type", {"version": 2}, 0.9, "s2")

    # Current should be version 2
    current = await long_term.get_fact(entity)
    assert current is not None
    assert current.facts["version"] == 2

    # History should have 2 entries
    history = await long_term.get_fact_history(entity)
    assert len(history) >= 2


@pytest.mark.asyncio
async def test_reasoning_bank_store_and_retrieve():
    entry = ReasoningEntry(
        pipeline="oracle",
        material="soybeans",
        task_signature="soybeans_thesis_update_test",
        strategy_summary="Test strategy for pytest",
        tools_used=["brave_news"],
        tool_priority_order=["brave_news"],
        outcome="SUCCESS",
        accuracy_delta=0.15,
    )
    entry_id = await reasoning_bank.store_entry(entry)
    assert entry_id is not None

    # Retrieve without embedding (text fallback)
    strategies = await reasoning_bank.retrieve_strategies(
        task_signature="soybeans_thesis",
        material="soybeans",
        pipeline="oracle",
        top_k=5,
    )
    assert len(strategies) >= 1


@pytest.mark.asyncio
async def test_reasoning_bank_decay():
    stats = await reasoning_bank.run_nightly_decay()
    assert "decayed" in stats
    assert "pruned" in stats
    assert "boosted" in stats


@pytest.mark.asyncio
async def test_reasoning_bank_stats():
    stats = await reasoning_bank.get_bank_stats()
    assert "total_entries" in stats
    assert "hit_rate" in stats
