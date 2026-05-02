"""
agents/oracle/orchestrator.py
Oracle Pipeline Orchestrator.
Coordinates: MaterialAgent × 4 materials + change stream watcher.
LangGraph StateGraph is the primary execution path; direct agent.run() is the fallback.
"""
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from langsmith import traceable

from db.connection import get_db
from agents.oracle.material_agent import MaterialAgent
from agents.oracle.graph import run_oracle_graph
from utils.logging import get_logger

log = get_logger(__name__)

MATERIALS = ["soybeans", "neon", "palladium", "lithium"]


async def _run_material_via_graph(material: str, task: dict) -> Any:
    """Run a single material through LangGraph with direct-agent fallback."""
    try:
        return await run_oracle_graph(material, task)
    except Exception as exc:
        log.warning("LangGraph oracle failed - falling back to direct agent",
                    material=material, error=str(exc))
        agent = MaterialAgent(material)
        return await agent.run(task)


@traceable(name="oracle_nightly_run")
async def run_nightly_oracle(materials: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run Oracle for all (or specified) materials via LangGraph StateGraph.
    Agents run in parallel via asyncio.gather.
    Returns dict of material -> result.
    """
    target = materials or MATERIALS
    log.info("Oracle nightly run starting", materials=target)

    tasks = []
    for material in target:
        task_payload = {
            "task_signature": f"{material}_thesis_update",
            "session_type": "oracle_run",
            "material": material,
            "trigger": "nightly_run",
            "entity_type": "supply_chain_event_pattern",
        }
        tasks.append((material, _run_material_via_graph(material, task_payload)))

    results: Dict[str, Any] = {}
    task_results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)
    for (material, _), result in zip(tasks, task_results):
        if isinstance(result, Exception):
            log.error("Material agent failed", material=material, error=str(result))
            results[material] = {"status": "error", "reason": str(result)}
        else:
            results[material] = result

    log.info("Oracle nightly run complete", results={k: v.get("status") for k, v in results.items()})
    return results


@traceable(name="oracle_claim_verdict_trigger")
async def handle_claim_verdict_trigger(
    verdict_id: str,
    verdict: str,
    affected_materials: List[str],
) -> Dict[str, Any]:
    """
    Triggered by change stream when a ClaimVerdict is written.
    Runs LangGraph MaterialAgent for each affected material.
    """
    log.info("Claim verdict trigger received",
             verdict_id=verdict_id, verdict=verdict,
             materials=affected_materials)

    tasks = []
    for material in affected_materials:
        task_payload = {
            "task_signature": f"{material}_claim_verdict_reaction",
            "session_type": "oracle_run",
            "material": material,
            "trigger": "claim_verdict",
            "verdict_id": verdict_id,
            "claim_verdict": verdict,
            "entity_type": "supply_chain_event_pattern",
        }
        tasks.append((material, _run_material_via_graph(material, task_payload)))

    results: Dict[str, Any] = {}
    task_results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)
    for (material, _), result in zip(tasks, task_results):
        if isinstance(result, Exception):
            log.error("Material agent failed on verdict trigger",
                      material=material, error=str(result))
            results[material] = {"status": "error", "reason": str(result)}
        else:
            results[material] = result

    return results


async def watch_claim_verdicts() -> None:
    """
    Continuous change stream watcher on claim_verdicts collection.
    When a new verdict is inserted, triggers affected material agents.
    """
    db = get_db()
    log.info("Change stream watcher started on claim_verdicts")

    pipeline = [{"$match": {"operationType": "insert"}}]
    async with db.claim_verdicts.watch(pipeline, full_document="updateLookup") as stream:
        async for change in stream:
            try:
                doc = change.get("fullDocument", {})
                verdict_id = doc.get("claim_id", str(change.get("documentKey", {}).get("_id", "")))
                verdict = doc.get("verdict", "INCONCLUSIVE")
                topics = doc.get("supply_chain_topics", [])

                # Map topics to affected materials
                affected_materials = _topics_to_materials(topics)
                if not affected_materials:
                    log.info("No material agents affected by verdict", topics=topics)
                    continue

                log.info("Change stream fired",
                         verdict_id=verdict_id,
                         verdict=verdict,
                         affected_materials=affected_materials)

                await handle_claim_verdict_trigger(
                    verdict_id=verdict_id,
                    verdict=verdict,
                    affected_materials=affected_materials,
                )
            except Exception as e:
                log.error("Change stream handler error", error=str(e))


def _topics_to_materials(topics: List[str]) -> List[str]:
    """Map supply chain topics to material agent names."""
    mapping = {
        "soybeans": ["soybeans"],
        "neon": ["neon"],
        "palladium": ["palladium"],
        "lithium": ["lithium"],
        "port": ["soybeans"],   # port disruptions affect soybean shipping most
        "strike": ["soybeans"],
    }
    materials = set()
    for topic in topics:
        for mat in mapping.get(topic, []):
            materials.add(mat)
    return list(materials)


async def get_all_thesis() -> List[dict]:
    """Get all currently active theses (valid_to=None)."""
    db = get_db()
    cursor = db.material_thesis.find({"valid_to": None}).sort("material", 1)
    theses = []
    async for doc in cursor:
        doc.pop("_id", None)
        theses.append(doc)
    return theses


async def get_thesis_history(material: str, limit: int = 10) -> List[dict]:
    """Get full bi-temporal history for a material."""
    db = get_db()
    cursor = db.material_thesis.find(
        {"material": material}
    ).sort("valid_from", -1).limit(limit)
    history = []
    async for doc in cursor:
        doc.pop("_id", None)
        history.append(doc)
    return history
