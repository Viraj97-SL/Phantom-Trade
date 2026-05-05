"""
db/scenarios.py
MongoDB repository for ScenarioTemplate documents.
"""
from typing import List, Optional

from db.connection import get_db
from models.schemas import ScenarioTemplate
from utils.logging import get_logger

log = get_logger(__name__)

_COLLECTION = "scenario_templates"


async def get_all_scenarios() -> List[ScenarioTemplate]:
    db = get_db()
    results = []
    async for doc in db[_COLLECTION].find().sort("is_builtin", -1):
        doc.pop("_id", None)
        results.append(ScenarioTemplate(**doc))
    return results


async def get_scenario_by_id(scenario_id: str) -> Optional[ScenarioTemplate]:
    db = get_db()
    doc = await db[_COLLECTION].find_one({"id": scenario_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return ScenarioTemplate(**doc)


async def create_scenario(scenario: ScenarioTemplate) -> ScenarioTemplate:
    db = get_db()
    await db[_COLLECTION].insert_one(scenario.model_dump())
    log.info("Scenario created", id=scenario.id, name=scenario.name)
    return scenario


async def delete_scenario(scenario_id: str) -> bool:
    db = get_db()
    doc = await db[_COLLECTION].find_one({"id": scenario_id})
    if not doc:
        return False
    if doc.get("is_builtin"):
        raise ValueError("Built-in scenarios cannot be deleted")
    result = await db[_COLLECTION].delete_one({"id": scenario_id})
    return result.deleted_count == 1


async def upsert_builtin_scenario(scenario: ScenarioTemplate) -> None:
    db = get_db()
    await db[_COLLECTION].update_one(
        {"id": scenario.id},
        {"$set": scenario.model_dump()},
        upsert=True,
    )
