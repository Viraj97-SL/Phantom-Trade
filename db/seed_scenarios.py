"""
db/seed_scenarios.py
Seeds 8 built-in supply-chain disinformation scenario templates.
Run on startup or: python -m db.seed_scenarios
"""
import asyncio
from datetime import datetime

from db.connection import get_db, ping_db
from db.scenarios import upsert_builtin_scenario
from models.schemas import ScenarioTemplate
from utils.logging import get_logger

log = get_logger(__name__)

_BUILTIN_SCENARIOS = [
    ScenarioTemplate(
        id="builtin-rotterdam-strike",
        name="Rotterdam Port Strike",
        description="Fake indefinite strike action claim targeting Rotterdam soybean operations.",
        claim_text=(
            "BREAKING: Rotterdam port workers have voted for indefinite strike action "
            "effective immediately. All soybean cargo operations halted. "
            "Sources: Reuters. #Rotterdam #SupplyChain"
        ),
        category="port_strike",
        tags=["rotterdam", "soybeans", "strike", "europe"],
        created_by="system",
        is_builtin=True,
    ),
    ScenarioTemplate(
        id="builtin-suez-blockage",
        name="Suez Canal Emergency Closure",
        description="Fabricated emergency closure blocking all LNG tanker transit.",
        claim_text=(
            "URGENT: Suez Canal emergency closure declared after vessel grounding. "
            "All LNG tanker transits suspended indefinitely by Egyptian authorities. "
            "Bloomberg confirms. Market impact expected within hours."
        ),
        category="port_strike",
        tags=["suez", "lng", "canal", "egypt", "tanker"],
        created_by="system",
        is_builtin=True,
    ),
    ScenarioTemplate(
        id="builtin-ukraine-neon-ban",
        name="Ukraine Neon Export Ban",
        description="Disinformation about Ukraine banning all neon gas exports targeting semiconductor supply.",
        claim_text=(
            "Ukraine has announced a complete ban on neon gas exports effective Monday. "
            "Semiconductor manufacturers warn of 6-month chip shortage. "
            "AP sources: 90% of global neon supply at risk. #Neon #Semiconductors"
        ),
        category="sanctions",
        tags=["ukraine", "neon", "semiconductor", "chip", "export-ban"],
        created_by="system",
        is_builtin=True,
    ),
    ScenarioTemplate(
        id="builtin-chile-lithium-strike",
        name="Chile Lithium Mine Strike",
        description="Fabricated lithium miner strike claim targeting EV battery supply chains.",
        claim_text=(
            "BREAKING: Chilean lithium mine workers begin indefinite strike at Atacama operations. "
            "Estimated 40% of global lithium carbonate output affected. "
            "Financial Times: EV battery makers scrambling. #Lithium #Chile"
        ),
        category="port_strike",
        tags=["chile", "lithium", "strike", "atacama", "ev", "battery"],
        created_by="system",
        is_builtin=True,
    ),
    ScenarioTemplate(
        id="builtin-russia-palladium-restriction",
        name="Russia Palladium Export Restriction",
        description="False claim about Russia imposing emergency palladium export restrictions.",
        claim_text=(
            "Russia imposes emergency export restrictions on palladium amid sanctions escalation. "
            "Automotive catalytic converter supply in critical shortage. "
            "WSJ: Prices expected to triple within 30 days. #Palladium #Russia #Sanctions"
        ),
        category="sanctions",
        tags=["russia", "palladium", "sanctions", "automotive", "catalytic"],
        created_by="system",
        is_builtin=True,
    ),
    ScenarioTemplate(
        id="builtin-brazil-soybean-drought",
        name="Brazil Soybean Harvest Failure",
        description="Exaggerated drought claim targeting Brazilian soybean futures.",
        claim_text=(
            "Catastrophic drought destroys 60% of Brazil's soybean harvest in Mato Grosso. "
            "USDA emergency assessment confirms worst crop failure in 50 years. "
            "Chicago futures up 18% pre-market. #Soybeans #Brazil #Drought"
        ),
        category="weather",
        tags=["brazil", "soybeans", "drought", "matogrosso", "usda", "futures"],
        created_by="system",
        is_builtin=True,
    ),
    ScenarioTemplate(
        id="builtin-taiwan-fab-fire",
        name="Taiwan Semiconductor Fab Fire",
        description="Fabricated fire at Taiwan chip fabrication plant claiming major output loss.",
        claim_text=(
            "CONFIRMED: Major fire at TSMC Fab 18 in Tainan Science Park. "
            "Production halted on 3nm and 5nm lines. Reuters: 3-month recovery timeline. "
            "Apple, NVIDIA sourcing alternatives. #TSMC #Taiwan #Semiconductor"
        ),
        category="geopolitical",
        tags=["taiwan", "tsmc", "semiconductor", "fire", "chip", "3nm"],
        created_by="system",
        is_builtin=True,
    ),
    ScenarioTemplate(
        id="builtin-generic-sanctions",
        name="Generic Sanctions Disruption Template",
        description="Template for testing commodity sanctions disinformation patterns.",
        claim_text=(
            "Major G7 sanctions package announced targeting copper exports. "
            "Full embargo effective in 48 hours per Bloomberg exclusive. "
            "Copper futures circuit-breaker triggered on London Metal Exchange. #Copper #Sanctions"
        ),
        category="sanctions",
        tags=["copper", "sanctions", "g7", "lme", "futures"],
        created_by="system",
        is_builtin=True,
    ),
]


async def seed() -> None:
    for scenario in _BUILTIN_SCENARIOS:
        await upsert_builtin_scenario(scenario)
    log.info("Built-in scenarios seeded", count=len(_BUILTIN_SCENARIOS))


async def main() -> None:
    ok = await ping_db()
    if not ok:
        log.error("Cannot reach MongoDB Atlas — check MONGODB_URI in .env")
        return
    await seed()
    log.info("Scenario seed complete")


if __name__ == "__main__":
    asyncio.run(main())
