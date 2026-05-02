"""
agents/oracle/material_agent.py
Oracle Material Agent — maintains a bi-temporal supply risk thesis
for a single material. Runs nightly + reacts to ClaimVerdict change streams.

This is the primary Prolonged Coordination agent.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from agents.base_agent import BaseAgent, AgentMemoryContext
from db.connection import get_db
from models.schemas import MaterialThesis, SignalItem, ProcurementAdvisory
from tools.tavily_search_tool import tavily_search
from tools.commodity_price_tool import get_commodity_price
from utils.llm import get_sonnet, get_haiku
from utils.logging import get_logger
from config.settings import settings
from middleware.guardrails import filter_financial_advice, validate_thesis_output

log = get_logger(__name__)

MATERIAL_CONTEXTS = {
    "neon": "Semiconductor-grade neon is 50%+ produced in Ukraine. Critical for chip manufacturing lasers.",
    "palladium": "70%+ produced in Russia and South Africa. Used in catalytic converters.",
    "soybeans": "Major supply from Brazil, Argentina, USA. Subject to weather, policy, shipping disruptions.",
    "lithium": "Key EV battery material. Major production in Chile, Australia, China.",
}


class MaterialAgent(BaseAgent):
    """
    Prolonged Coordination agent for a single material.
    Persists thesis state in MongoDB across days/weeks.
    """

    def __init__(self, material: str):
        super().__init__(
            agent_id=f"material_agent_{material}",
            pipeline="oracle",
        )
        self.material = material
        self.context = MATERIAL_CONTEXTS.get(material, f"{material} supply chain material.")

    # ── PLAN ──────────────────────────────────────────────────────────────

    async def _plan(self, task: dict, memory: AgentMemoryContext) -> dict:
        """
        Plan signal retrieval strategy based on:
        - Best prior strategy from reasoning bank
        - Current thesis risk level
        - Trigger type (nightly vs claim_verdict)
        """
        current_thesis = await self._get_current_thesis()
        trigger = task.get("trigger", "nightly_run")

        # Load best prior strategy
        best = memory.best_strategy()
        tool_order = best.tool_priority_order if best else [
            "brave_news", "commodity_price", "claim_verdicts"
        ]

        plan = {
            "steps": [
                "retrieve_signals",
                "load_current_thesis",
                "generate_updated_thesis",
                "check_risk_delta",
                "write_thesis_if_changed",
            ],
            "tool_priority_order": tool_order,
            "current_risk_level": current_thesis.risk_level if current_thesis else 0,
            "trigger": trigger,
            "claim_verdict_id": task.get("verdict_id"),
            "strategy_source": "reasoning_bank" if best else "default",
        }

        log.info("Oracle plan created",
                 material=self.material,
                 trigger=trigger,
                 tool_order=tool_order)
        return plan

    # ── ACT ───────────────────────────────────────────────────────────────

    async def _act(self, task: dict, plan: dict, memory: AgentMemoryContext) -> dict:
        """Retrieve signals from all sources in priority order."""
        signals = []
        tools_used = []

        # 1. News signals via Tavily Search
        if "brave_news" in plan["tool_priority_order"]:
            try:
                news = await tavily_search(
                    f"{self.material} supply chain disruption 2026", max_results=4
                )
                for item in news:
                    signals.append(SignalItem(
                        signal_type="news",
                        source="tavily_search",
                        headline=item["title"],
                        content_summary=item["content"][:300],
                        sentiment="neutral",
                        relevance_score=item.get("score", 0.7),
                    ))
                tools_used.append("tavily_news")
                log.info("Live news signals retrieved via Tavily",
                         material=self.material, count=len(news))
            except Exception as e:
                log.warning("Tavily search failed", error=str(e))

        # 2. Commodity price signal
        if "commodity_price" in plan["tool_priority_order"]:
            try:
                price_data = await get_commodity_price(self.material)
                if price_data:
                    sentiment = "bearish" if (price_data.get("change_pct") or 0) > 5 else "neutral"
                    signals.append(SignalItem(
                        signal_type="commodity_price",
                        source="FRED",
                        headline=f"{self.material} price: ${price_data['price']:,.2f}",
                        content_summary=f"Price change: {price_data.get('change_pct', 0)}%",
                        sentiment=sentiment,
                        relevance_score=0.85,
                        is_verified=True,
                    ))
                    tools_used.append("commodity_price")
            except Exception as e:
                log.warning("Commodity price fetch failed", error=str(e))

        # 3. Check for related ClaimVerdicts
        if task.get("verdict_id"):
            try:
                db = get_db()
                verdict = await db.claim_verdicts.find_one(
                    {"_id_str": task["verdict_id"]}
                )
                if verdict:
                    signals.append(SignalItem(
                        signal_type="claim_verdict",
                        source="forensics_pipeline",
                        headline=f"Claim verdict: {verdict.get('verdict')} (confidence {verdict.get('confidence', 0):.2f})",
                        content_summary=f"Claim: {verdict.get('claim_text', '')[:200]}",
                        sentiment="bearish" if verdict.get("verdict") == "AUTHENTIC" else "neutral",
                        relevance_score=verdict.get("confidence", 0.5),
                        is_verified=True,
                        claim_verdict_id=task["verdict_id"],
                    ))
                    tools_used.append("claim_verdicts")
            except Exception as e:
                log.warning("ClaimVerdict fetch failed", error=str(e))

        return {
            "signals": [s.model_dump() for s in signals],
            "tools_used": tools_used,
            "signal_count": len(signals),
        }

    # ── OBSERVE ───────────────────────────────────────────────────────────

    async def _observe(self, task: dict, act_result: dict,
                       memory: AgentMemoryContext) -> dict:
        """Evaluate signal quality. Generate updated thesis via LLM."""
        signals = act_result.get("signals", [])
        current_thesis = await self._get_current_thesis()

        if len(signals) == 0:
            return {
                "confidence": 0.2,
                "failure_reason": "no_signals_retrieved",
                "should_update": False,
            }

        # Generate updated thesis via LLM
        updated_thesis = await self._generate_thesis(signals, current_thesis)

        if updated_thesis is None:
            return {"confidence": 0.3, "failure_reason": "llm_generation_failed"}

        current_risk = current_thesis.risk_level if current_thesis else 0
        new_risk = updated_thesis.get("risk_level", current_risk)
        risk_delta = abs(new_risk - current_risk)

        return {
            "confidence": 0.85,
            "updated_thesis": updated_thesis,
            "current_risk": current_risk,
            "new_risk": new_risk,
            "risk_delta": risk_delta,
            "should_update": risk_delta >= settings.alert_threshold or task.get("verdict_id"),
            "requires_hitl": new_risk >= settings.critical_threshold,
        }

    # ── REACT ─────────────────────────────────────────────────────────────

    async def _react(self, task: dict, act_result: dict,
                     observation: dict, memory: AgentMemoryContext) -> dict:
        """Write updated thesis to MongoDB if risk changed."""
        updated_thesis_dict = observation.get("updated_thesis", {})
        if not updated_thesis_dict or not observation.get("should_update"):
            return {
                "status": "no_change",
                "material": self.material,
                "risk_level": observation.get("current_risk", 0),
                "tools_used": act_result.get("tools_used", []),
                "strategy_used": f"oracle_{self.material}_no_change",
            }

        # Write bi-temporal thesis
        await self._write_thesis(updated_thesis_dict, task.get("verdict_id"))

        # Create procurement advisory if risk is high
        advisory = None
        if observation.get("requires_hitl") or observation.get("risk_delta", 0) > 20:
            advisory = await self._create_advisory(updated_thesis_dict, task)

        risk_label = updated_thesis_dict.get("risk_label", "STABLE")
        log.info("Oracle thesis updated",
                 material=self.material,
                 old_risk=observation.get("current_risk"),
                 new_risk=observation.get("new_risk"),
                 label=risk_label)

        return {
            "status": "thesis_updated",
            "material": self.material,
            "risk_level": observation.get("new_risk"),
            "risk_label": risk_label,
            "risk_delta": observation.get("risk_delta"),
            "advisory_created": advisory is not None,
            "tools_used": act_result.get("tools_used", []),
            "tool_priority_order": act_result.get("tools_used", []),
            "strategy_used": f"oracle_{self.material}_{task.get('trigger', 'nightly')}",
            "tags": [self.material, "oracle", task.get("trigger", "nightly")],
        }

    # ── Helpers ───────────────────────────────────────────────────────────

    async def _get_current_thesis(self) -> Optional[MaterialThesis]:
        """Get the currently active thesis for this material."""
        db = get_db()
        doc = await db.material_thesis.find_one(
            {"material": self.material, "valid_to": None},
            sort=[("valid_from", -1)]
        )
        if doc:
            doc.pop("_id", None)
            try:
                return MaterialThesis(**doc)
            except Exception:
                return None
        return None

    async def _generate_thesis(self, signals: list,
                                current_thesis: Optional[MaterialThesis]) -> Optional[dict]:
        """Call LLM to generate updated thesis from signals."""
        llm = get_sonnet()

        current_summary = "No previous thesis." if not current_thesis else (
            f"Current risk: {current_thesis.risk_level}/100 ({current_thesis.risk_label}). "
            f"Narrative: {current_thesis.narrative[:200]}"
        )

        signals_text = "\n".join([
            f"- [{s['signal_type']}] {s['headline']}: {s['content_summary'][:150]}"
            for s in signals[:6]
        ])

        system = """You are a supply chain risk analyst. Given new signals and the current thesis, 
output a JSON object with:
- risk_level (0-100 integer)
- risk_label (STABLE/ELEVATED/HIGH/CRITICAL)  
- narrative (2-3 sentence analysis)
- procurement_recommendation (1 sentence action, NO financial advice language)
- key_drivers (list of 2-3 main factors)

Respond ONLY with valid JSON. No markdown, no explanation."""

        human = f"""Material: {self.material}
Context: {self.context}
Current Thesis: {current_summary}

New Signals:
{signals_text}

Generate updated risk thesis as JSON:"""

        try:
            response = await llm.ainvoke([
                SystemMessage(content=system),
                HumanMessage(content=human)
            ])
            raw = response.content.strip()
            # Clean any markdown
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            thesis_dict = json.loads(raw)
            thesis_dict["material"] = self.material

            # Apply financial advice filter
            if "procurement_recommendation" in thesis_dict:
                thesis_dict["procurement_recommendation"] = filter_financial_advice(
                    thesis_dict["procurement_recommendation"]
                )

            validate_thesis_output(thesis_dict)
            return thesis_dict
        except Exception as e:
            log.error("Thesis generation failed", material=self.material, error=str(e))
            return None

    async def _write_thesis(self, thesis_dict: dict,
                            verdict_id: Optional[str] = None) -> None:
        """Bi-temporal write — close current, insert new."""
        db = get_db()
        now = datetime.utcnow()

        # Close current thesis
        await db.material_thesis.update_many(
            {"material": self.material, "valid_to": None},
            {"$set": {"valid_to": now}}
        )

        # Insert new version
        risk = thesis_dict.get("risk_level", 0)
        if risk >= 80:
            label = "CRITICAL"
        elif risk >= 60:
            label = "HIGH"
        elif risk >= 40:
            label = "ELEVATED"
        else:
            label = "STABLE"

        new_doc = {
            "material": self.material,
            "risk_level": risk,
            "risk_label": label,
            "narrative": thesis_dict.get("narrative", ""),
            "procurement_recommendation": thesis_dict.get("procurement_recommendation", ""),
            "key_drivers": thesis_dict.get("key_drivers", []),
            "valid_from": now,
            "valid_to": None,
            "triggered_by_claim_verdict_id": verdict_id,
            "created_at": now,
        }
        await db.material_thesis.insert_one(new_doc)
        log.info("Thesis written (bi-temporal)", material=self.material,
                 risk_level=risk, label=label)

        # Store audit artifact in S3 (non-blocking)
        try:
            from utils.s3 import store_oracle_artifact
            await store_oracle_artifact(self.material, new_doc)
        except Exception:
            pass

    async def _create_advisory(self, thesis_dict: dict, task: dict) -> ProcurementAdvisory:
        """Create a procurement advisory for HITL review."""
        db = get_db()
        advisory = ProcurementAdvisory(
            material=self.material,
            risk_level=thesis_dict.get("risk_level", 0),
            risk_label=thesis_dict.get("risk_label", "STABLE"),
            recommendation=thesis_dict.get("procurement_recommendation", "Review required."),
            key_signals_summary=thesis_dict.get("key_drivers", []),
            triggered_by=task.get("trigger", "nightly_run"),
        )
        await db.procurement_advisories.insert_one(advisory.model_dump())
        log.info("Procurement advisory created", material=self.material)
        return advisory
