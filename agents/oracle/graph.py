"""
agents/oracle/graph.py
LangGraph StateGraph for Oracle MaterialAgent.
Implements Plan->Act->Observe->React as proper LangGraph nodes with
MemorySaver checkpointer (durable execution for the Prolonged Coordination
hackathon theme).

Each node independently loads memory so no non-serialisable objects are
stored in the state dict. This keeps the graph checkpoint-safe.
"""
from __future__ import annotations

import uuid
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
    _MONGO_CHECKPOINTER_AVAILABLE = True
except ImportError:
    _MONGO_CHECKPOINTER_AVAILABLE = False

from memory import short_term
from utils.logging import get_logger

log = get_logger(__name__)

MAX_REPLAN_CYCLES = 3
MIN_CONFIDENCE = 0.3


class OracleState(TypedDict):
    """
    LangGraph state for the Oracle MaterialAgent loop.
    All fields are JSON-serialisable so MemorySaver (and any future
    MongoDB checkpointer) can persist them between nodes.
    """
    material: str
    task: dict
    plan: Optional[dict]
    act_result: Optional[dict]
    observation: Optional[dict]
    react_result: Optional[dict]
    replan_count: int
    phase: str
    error: Optional[str]
    session_id: Optional[str]


def _make_oracle_graph(material_agent) -> StateGraph:
    """
    Build the LangGraph StateGraph that wraps a MaterialAgent's
    Plan -> Act -> Observe -> React loop as discrete, checkpointable nodes.
    """

    async def _ensure_session(state: OracleState) -> str:
        if state.get("session_id"):
            return state["session_id"]
        session = await short_term.create_session(
            agent_id=material_agent.agent_id,
            session_type=state["task"].get("session_type", "oracle_run"),
            claim_id=state["task"].get("claim_id"),
            material=state["material"],
        )
        return session.session_id

    async def plan_node(state: OracleState) -> OracleState:
        """PLAN phase — load 3-layer memory, choose tool order, build plan."""
        log.info("LangGraph node: PLAN", material=state["material"])
        try:
            session_id = await _ensure_session(state)
            material_agent.session_id = session_id
            await short_term.set_phase(session_id, "PLAN")

            task_sig = state["task"].get("task_signature", material_agent.agent_id)
            memory = await material_agent._load_memory(task_sig, state["task"])
            plan = await material_agent._plan(state["task"], memory)

            log.info("PLAN node complete", material=state["material"],
                     steps=len(plan.get("steps", [])),
                     strategy_source=plan.get("strategy_source", "default"))
            return {**state, "plan": plan, "phase": "ACT",
                    "session_id": session_id, "error": None}
        except Exception as exc:
            log.error("PLAN node failed", material=state["material"], error=str(exc))
            return {**state, "error": str(exc), "phase": "ERROR"}

    async def act_node(state: OracleState) -> OracleState:
        """ACT phase — execute tool calls in priority order."""
        log.info("LangGraph node: ACT", material=state["material"])
        try:
            session_id = state["session_id"]
            material_agent.session_id = session_id
            await short_term.set_phase(session_id, "ACT")

            task_sig = state["task"].get("task_signature", material_agent.agent_id)
            memory = await material_agent._load_memory(task_sig, state["task"])
            act_result = await material_agent._act(state["task"], state["plan"], memory)

            log.info("ACT node complete", material=state["material"],
                     signals=act_result.get("signal_count", 0),
                     tools_used=act_result.get("tools_used", []))
            return {**state, "act_result": act_result, "phase": "OBSERVE", "error": None}
        except Exception as exc:
            log.error("ACT node failed", material=state["material"], error=str(exc))
            return {**state, "error": str(exc), "phase": "ERROR"}

    async def observe_node(state: OracleState) -> OracleState:
        """OBSERVE phase — evaluate signal quality, compute confidence."""
        log.info("LangGraph node: OBSERVE", material=state["material"])
        try:
            session_id = state["session_id"]
            material_agent.session_id = session_id
            await short_term.set_phase(session_id, "OBSERVE")

            task_sig = state["task"].get("task_signature", material_agent.agent_id)
            memory = await material_agent._load_memory(task_sig, state["task"])
            observation = await material_agent._observe(
                state["task"], state["act_result"], memory
            )
            confidence = observation.get("confidence", 0.0)
            await short_term.update_session(session_id, {"confidence_current": confidence})

            log.info("OBSERVE node complete", material=state["material"],
                     confidence=confidence)
            return {**state, "observation": observation, "phase": "REACT", "error": None}
        except Exception as exc:
            log.error("OBSERVE node failed", material=state["material"], error=str(exc))
            return {**state, "error": str(exc), "phase": "ERROR"}

    async def react_node(state: OracleState) -> OracleState:
        """REACT phase — commit thesis to MongoDB and update reasoning bank."""
        log.info("LangGraph node: REACT", material=state["material"])
        try:
            session_id = state["session_id"]
            material_agent.session_id = session_id
            await short_term.set_phase(session_id, "REACT")

            task_sig = state["task"].get("task_signature", material_agent.agent_id)
            memory = await material_agent._load_memory(task_sig, state["task"])
            react_result = await material_agent._react(
                state["task"], state["act_result"], state["observation"], memory
            )

            # Write reasoning bank entry (mirrors BaseAgent._update_memory)
            await material_agent._update_memory(
                task_sig, react_result, state["observation"]
            )

            await short_term.set_phase(session_id, "COMPLETE")
            log.info("REACT node complete", material=state["material"],
                     status=react_result.get("status"),
                     risk_level=react_result.get("risk_level"))
            return {**state, "react_result": react_result,
                    "phase": "COMPLETE", "error": None}
        except Exception as exc:
            log.error("REACT node failed", material=state["material"], error=str(exc))
            return {**state, "error": str(exc), "phase": "ERROR"}

    async def replan_node(state: OracleState) -> OracleState:
        """REPLAN — increment counter and patch task for another cycle."""
        replan_count = state.get("replan_count", 0) + 1
        log.warning("LangGraph node: REPLAN", material=state["material"],
                    replan_count=replan_count)
        session_id = state.get("session_id")
        if session_id:
            material_agent.session_id = session_id
            await short_term.set_phase(session_id, "REPLAN")
            await short_term.increment_replan(session_id)

        obs = state.get("observation") or {}
        updated_task = {
            **state["task"],
            "replan_count": replan_count,
            "previous_failure_reason": obs.get("failure_reason", "low_confidence"),
        }
        return {
            **state,
            "task": updated_task,
            "replan_count": replan_count,
            "phase": "PLAN",
            "plan": None,
            "act_result": None,
            "observation": None,
            "error": None,
        }

    def route_after_observe(state: OracleState) -> str:
        """
        Conditional edge after OBSERVE:
        - error/ERROR phase → end
        - confidence >= threshold OR max replans hit → react
        - otherwise → replan (re-enter PLAN)
        """
        if state.get("error") or state.get("phase") == "ERROR":
            return "end"

        obs = state.get("observation") or {}
        confidence = obs.get("confidence", 0.0)
        replan_count = state.get("replan_count", 0)

        if confidence >= MIN_CONFIDENCE or replan_count >= MAX_REPLAN_CYCLES:
            return "react"
        return "replan"

    # Build the graph
    workflow = StateGraph(OracleState)
    workflow.add_node("plan", plan_node)
    workflow.add_node("act", act_node)
    workflow.add_node("observe", observe_node)
    workflow.add_node("react", react_node)
    workflow.add_node("replan", replan_node)

    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "act")
    workflow.add_edge("act", "observe")
    workflow.add_conditional_edges(
        "observe",
        route_after_observe,
        {"react": "react", "replan": "replan", "end": END},
    )
    workflow.add_edge("replan", "plan")
    workflow.add_edge("react", END)

    return workflow


async def run_oracle_graph(
    material: str,
    task: dict,
    use_checkpointer: bool = True,
) -> dict:
    """
    Run the Oracle LangGraph StateGraph for a single material.
    Uses MemorySaver for durable in-memory checkpointing.
    Each invocation gets its own thread_id for isolated state.
    """
    from agents.oracle.material_agent import MaterialAgent

    agent = MaterialAgent(material)
    workflow = _make_oracle_graph(agent)

    checkpointer = None
    if use_checkpointer:
        if _MONGO_CHECKPOINTER_AVAILABLE:
            try:
                from db.connection import get_async_client
                client = get_async_client()
                from config.settings import settings
                db_name = settings.mongodb_db
                checkpointer = AsyncMongoDBSaver(client[db_name]["agent_checkpoints"])
                log.info("Using AsyncMongoDBSaver for LangGraph checkpoints")
            except Exception as exc:
                log.warning("AsyncMongoDBSaver init failed, falling back to MemorySaver",
                            error=str(exc))
                checkpointer = MemorySaver()
        else:
            checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)

    thread_id = f"oracle_{material}_{task.get('trigger', 'run')}_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: OracleState = {
        "material": material,
        "task": task,
        "plan": None,
        "act_result": None,
        "observation": None,
        "react_result": None,
        "replan_count": 0,
        "phase": "PLAN",
        "error": None,
        "session_id": None,
    }

    log.info("LangGraph Oracle run started", material=material,
             thread_id=thread_id, trigger=task.get("trigger"))

    final_state = await graph.ainvoke(initial_state, config=config)

    result = final_state.get("react_result") or {
        "status": "error",
        "material": material,
        "error": final_state.get("error", "unknown_error"),
        "phase": final_state.get("phase"),
    }

    log.info("LangGraph Oracle run complete", material=material,
             status=result.get("status"), phase=final_state.get("phase"))
    return result
