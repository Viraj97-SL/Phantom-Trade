"""
memory/short_term.py
Short-term memory — session-scoped, TTL 1 hour.
Stores current task context, active tool calls, working hypothesis.
"""
from datetime import datetime, timedelta
from typing import Optional
from db.connection import get_db
from models.schemas import AgentSession
from utils.logging import get_logger
import uuid

log = get_logger(__name__)
SESSION_TTL_HOURS = 1


async def create_session(
    agent_id: str,
    session_type: str,
    claim_id: Optional[str] = None,
    material: Optional[str] = None,
) -> AgentSession:
    """Create a new short-term session in MongoDB."""
    db = get_db()
    session = AgentSession(
        session_id=str(uuid.uuid4()),
        agent_id=agent_id,
        session_type=session_type,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS),
        active_claim_id=claim_id,
        active_material=material,
    )
    await db.agent_sessions.insert_one(session.model_dump())
    log.info("Session created", session_id=session.session_id, agent_id=agent_id)
    return session


async def get_session(session_id: str) -> Optional[AgentSession]:
    db = get_db()
    doc = await db.agent_sessions.find_one({"session_id": session_id})
    if doc:
        doc.pop("_id", None)
        return AgentSession(**doc)
    return None


async def update_session(session_id: str, updates: dict) -> None:
    db = get_db()
    await db.agent_sessions.update_one(
        {"session_id": session_id},
        {"$set": updates}
    )


async def push_tool_call(session_id: str, tool_name: str) -> None:
    db = get_db()
    await db.agent_sessions.update_one(
        {"session_id": session_id},
        {"$push": {"tool_calls_made": tool_name}}
    )


async def set_phase(session_id: str, phase: str) -> None:
    await update_session(session_id, {"current_phase": phase})
    log.info("Phase transition", session_id=session_id, phase=phase)


async def set_sub_agent_result(session_id: str, agent_name: str, result: dict) -> None:
    db = get_db()
    await db.agent_sessions.update_one(
        {"session_id": session_id},
        {"$set": {f"sub_agent_results.{agent_name}": result}}
    )


async def increment_replan(session_id: str) -> int:
    db = get_db()
    result = await db.agent_sessions.find_one_and_update(
        {"session_id": session_id},
        {"$inc": {"replan_count": 1}},
        return_document=True
    )
    return result.get("replan_count", 0) if result else 0


async def expire_session(session_id: str) -> None:
    db = get_db()
    await db.agent_sessions.delete_one({"session_id": session_id})
    log.info("Session expired manually", session_id=session_id)
