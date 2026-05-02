"""
agents/base_agent.py
Base class for ALL agents in PHANTOM TRADE.
Implements the Plan → Act → Observe → React loop with:
- 3-layer memory loading at PLAN time
- Checkpointing after every phase
- Reasoning bank update on completion
- DPO pair generation for LangSmith
"""
from __future__ import annotations
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Any

from memory import short_term, long_term, reasoning_bank
from models.schemas import AgentSession, ReasoningEntry
from utils.embeddings import embed_text
from utils.logging import get_logger

log = get_logger(__name__)

MAX_REPLAN_CYCLES = 3
MIN_CONFIDENCE = 0.3


class AgentMemoryContext:
    """Loaded at PLAN time  -  passed through the loop."""
    def __init__(self, session, knowledge, strategies):
        self.session: Optional[AgentSession] = session
        self.knowledge: List = knowledge
        self.strategies: List[ReasoningEntry] = strategies

    def best_strategy(self) -> Optional[ReasoningEntry]:
        return self.strategies[0] if self.strategies else None

    def strategy_summary(self) -> str:
        if not self.strategies:
            return "No prior strategies available - exploring fresh."
        top = self.strategies[0]
        return f"Best prior strategy: {top.strategy_summary} (accuracy_delta={top.accuracy_delta:.2f})"


class BaseAgent(ABC):
    """
    Abstract base for all PHANTOM TRADE agents.
    Subclasses implement _plan, _act, _observe, _react.
    """

    def __init__(self, agent_id: str, pipeline: str):
        self.agent_id = agent_id
        self.pipeline = pipeline
        self.session_id: Optional[str] = None
        self._start_time: float = 0.0
        self._token_count: int = 0

    # ── Entry Point ───────────────────────────────────────────────────────

    async def run(self, task: dict) -> dict:
        """
        Main entry point. Runs the full Plan → Act → Observe → React loop.
        Returns the final result dict.
        """
        self._start_time = time.time()
        task_signature = task.get("task_signature", self.agent_id)

        log.info("Agent run started", agent_id=self.agent_id, task=task_signature)

        # Create session
        session = await short_term.create_session(
            agent_id=self.agent_id,
            session_type=task.get("session_type", "oracle_run"),
            claim_id=task.get("claim_id"),
            material=task.get("material"),
        )
        self.session_id = session.session_id

        replan_count = 0
        result = {}

        while replan_count <= MAX_REPLAN_CYCLES:
            try:
                # ── PHASE 1: PLAN ─────────────────────────────────────────
                await short_term.set_phase(self.session_id, "PLAN")
                memory = await self._load_memory(task_signature, task)
                plan = await self._plan(task, memory)
                log.info("Plan created", agent_id=self.agent_id,
                         steps=len(plan.get("steps", [])),
                         strategy=memory.strategy_summary()[:80])

                # ── PHASE 2: ACT ──────────────────────────────────────────
                await short_term.set_phase(self.session_id, "ACT")
                act_result = await self._act(task, plan, memory)

                # ── PHASE 3: OBSERVE ──────────────────────────────────────
                await short_term.set_phase(self.session_id, "OBSERVE")
                observation = await self._observe(task, act_result, memory)
                confidence = observation.get("confidence", 0.0)

                await short_term.update_session(
                    self.session_id,
                    {"confidence_current": confidence}
                )

                # ── PHASE 4: REACT or REPLAN ──────────────────────────────
                if confidence >= MIN_CONFIDENCE:
                    await short_term.set_phase(self.session_id, "REACT")
                    result = await self._react(task, act_result, observation, memory)
                    await self._update_memory(task_signature, result, observation)
                    break
                else:
                    replan_count += 1
                    log.warning("Low confidence  -  replanning",
                                agent_id=self.agent_id,
                                confidence=confidence,
                                replan=replan_count)
                    await short_term.set_phase(self.session_id, "REPLAN")
                    await short_term.increment_replan(self.session_id)
                    task = await self._replan(task, observation, replan_count)

                    if replan_count > MAX_REPLAN_CYCLES:
                        log.error("Max replan cycles exceeded",
                                  agent_id=self.agent_id)
                        result = {"status": "failed",
                                  "reason": "max_replan_exceeded",
                                  "confidence": confidence}
                        break

            except Exception as e:
                log.error("Agent loop error", agent_id=self.agent_id, error=str(e))
                result = {"status": "error", "reason": str(e)}
                break

        await short_term.set_phase(self.session_id, "COMPLETE")
        elapsed = int((time.time() - self._start_time) * 1000)
        result["latency_ms"] = elapsed
        result["session_id"] = self.session_id

        log.info("Agent run complete",
                 agent_id=self.agent_id,
                 latency_ms=elapsed,
                 status=result.get("status", "ok"))
        return result

    # ── Memory Loading ────────────────────────────────────────────────────

    async def _load_memory(self, task_signature: str, task: dict) -> AgentMemoryContext:
        """Load all 3 memory layers at PLAN time."""
        # 1. Short-term: current session (already created)
        session = await short_term.get_session(self.session_id)

        # 2. Long-term: relevant knowledge facts
        entity_type = task.get("entity_type", "supply_chain_event_pattern")
        knowledge = await long_term.get_facts_by_type(entity_type, limit=5)

        # 3. Reasoning bank: top strategies
        try:
            embedding = await embed_text(task_signature, input_type="query")
        except Exception:
            embedding = None

        strategies = await reasoning_bank.retrieve_strategies(
            task_signature=task_signature,
            embedding=embedding,
            material=task.get("material"),
            pipeline=self.pipeline,
            top_k=5,
        )

        log.info("Memory loaded",
                 agent_id=self.agent_id,
                 knowledge_facts=len(knowledge),
                 strategies=len(strategies))

        return AgentMemoryContext(
            session=session,
            knowledge=knowledge,
            strategies=strategies,
        )

    # ── Memory Update ─────────────────────────────────────────────────────

    async def _update_memory(self, task_signature: str, result: dict,
                              observation: dict) -> None:
        """Update reasoning bank after task completion."""
        outcome = "SUCCESS" if result.get("status") != "failed" else "FAILURE"
        confidence = observation.get("confidence", 0.0)

        try:
            embedding = await embed_text(task_signature, input_type="document")
        except Exception:
            embedding = None

        entry = ReasoningEntry(
            material=result.get("material"),
            pipeline=self.pipeline,
            task_signature=task_signature,
            strategy_summary=result.get("strategy_used",
                                        f"Default {self.agent_id} strategy"),
            tools_used=result.get("tools_used", []),
            tool_priority_order=result.get("tool_priority_order", []),
            outcome=outcome,
            accuracy_delta=confidence - 0.5,  # delta from baseline
            latency_ms=result.get("latency_ms", 0),
            decay_score=1.0,
            similarity_embedding=embedding,
            tags=result.get("tags", []),
        )
        await reasoning_bank.store_entry(entry)

    # ── Abstract Methods ──────────────────────────────────────────────────

    @abstractmethod
    async def _plan(self, task: dict, memory: AgentMemoryContext) -> dict:
        """Create an execution plan from task + memory."""
        ...

    @abstractmethod
    async def _act(self, task: dict, plan: dict,
                   memory: AgentMemoryContext) -> dict:
        """Execute the plan  -  tool calls, sub-agent spawning."""
        ...

    @abstractmethod
    async def _observe(self, task: dict, act_result: dict,
                       memory: AgentMemoryContext) -> dict:
        """Evaluate act_result  -  compute confidence, detect failures."""
        ...

    @abstractmethod
    async def _react(self, task: dict, act_result: dict,
                     observation: dict, memory: AgentMemoryContext) -> dict:
        """Commit result  -  write to MongoDB, emit change streams."""
        ...

    async def _replan(self, task: dict, observation: dict,
                      replan_count: int) -> dict:
        """Default replan  -  can be overridden by subclasses."""
        task["replan_count"] = replan_count
        task["previous_failure_reason"] = observation.get("failure_reason", "low_confidence")
        return task
