"""
db/seed_data.py
Seeds demo data for the hackathon presentation.
Run once: python -m db.seed_data

Seeds:
- 4 material theses (current baselines)
- 20 reasoning bank entries (simulating 20 prior runs)
- 5 skill library cards
- 3 knowledge facts
"""
import asyncio
from datetime import datetime, timedelta
from db.connection import get_db, ping_db
from utils.logging import get_logger

log = get_logger(__name__)


async def seed_material_theses() -> None:
    db = get_db()
    now = datetime.utcnow()

    # Clear existing theses
    await db.material_thesis.delete_many({})

    theses = [
        {
            "material": "soybeans",
            "risk_level": 28,
            "risk_label": "STABLE",
            "narrative": (
                "Soybean supply chains remain stable with normal Brazilian harvest season. "
                "Rotterdam port operations nominal. No significant disruptions detected."
            ),
            "procurement_recommendation": (
                "Maintain current inventory levels. Monitor Brazilian weather forecasts."
            ),
            "key_drivers": ["Normal harvest season", "Stable Rotterdam operations", "Steady demand"],
            "valid_from": now - timedelta(days=2),
            "valid_to": None,
            "triggered_by_claim_verdict_id": None,
            "created_at": now - timedelta(days=2),
        },
        {
            "material": "neon",
            "risk_level": 45,
            "risk_label": "ELEVATED",
            "narrative": (
                "Semiconductor-grade neon supply remains elevated risk due to ongoing "
                "geopolitical tensions near Ukrainian production facilities. "
                "Alternative suppliers being qualified."
            ),
            "procurement_recommendation": (
                "Consider strategic reserve increase of 30-day supply buffer."
            ),
            "key_drivers": ["Geopolitical tension", "Ukraine production risk", "Alternative qualification in progress"],
            "valid_from": now - timedelta(days=5),
            "valid_to": None,
            "triggered_by_claim_verdict_id": None,
            "created_at": now - timedelta(days=5),
        },
        {
            "material": "palladium",
            "risk_level": 35,
            "risk_label": "STABLE",
            "narrative": (
                "Palladium markets stable. Russian export levels holding steady. "
                "Automotive demand softening due to EV transition."
            ),
            "procurement_recommendation": (
                "No immediate action required. Review hedging positions at next quarterly cycle."
            ),
            "key_drivers": ["Stable Russian exports", "Softening automotive demand", "EV transition"],
            "valid_from": now - timedelta(days=3),
            "valid_to": None,
            "triggered_by_claim_verdict_id": None,
            "created_at": now - timedelta(days=3),
        },
        {
            "material": "lithium",
            "risk_level": 52,
            "risk_label": "ELEVATED",
            "narrative": (
                "Chilean lithium carbonate prices showing upward pressure. "
                "New DRC mining regulations introducing uncertainty. "
                "EV demand continues to outpace supply expansion."
            ),
            "procurement_recommendation": (
                "Review long-term contracts. Consider spot market purchases for Q3 buffer."
            ),
            "key_drivers": ["Chilean price pressure", "DRC regulatory uncertainty", "EV demand surge"],
            "valid_from": now - timedelta(days=1),
            "valid_to": None,
            "triggered_by_claim_verdict_id": None,
            "created_at": now - timedelta(days=1),
        },
    ]
    await db.material_thesis.insert_many(theses)
    log.info("Material theses seeded", count=len(theses))


async def seed_reasoning_bank() -> None:
    """Seed 20 reasoning bank entries to simulate prior learning."""
    db = get_db()
    await db.reasoning_bank.delete_many({})
    now = datetime.utcnow()

    entries = []

    # Oracle entries  -  showing improvement over cycles
    oracle_strategies = [
        {
            "material": "soybeans",
            "strategy_summary": "Rotterdam port strike claims: verify with port authority feed before elevating thesis",
            "tools_used": ["brave_news", "commodity_price"],
            "outcome": "SUCCESS",
            "accuracy_delta": 0.22,
            "use_count": 8,
        },
        {
            "material": "neon",
            "strategy_summary": "Odessa port + Ukrainian gas processing plant signals precede neon price by 6-8 weeks",
            "tools_used": ["brave_news", "claim_verdicts"],
            "outcome": "SUCCESS",
            "accuracy_delta": 0.31,
            "use_count": 5,
        },
        {
            "material": "palladium",
            "strategy_summary": "Russian export news + GDELT geopolitical score outperforms commodity futures for palladium",
            "tools_used": ["brave_news"],
            "outcome": "SUCCESS",
            "accuracy_delta": 0.18,
            "use_count": 12,
        },
        {
            "material": "soybeans",
            "strategy_summary": "Fabricated port disruption claims: check audio-visual forensics before elevating  -  learned from March 2024",
            "tools_used": ["claim_verdicts", "brave_news"],
            "outcome": "SUCCESS",
            "accuracy_delta": 0.41,
            "use_count": 3,
        },
    ]

    # Forensics entries
    forensics_strategies = [
        {
            "strategy_summary": "Port strike claims with Reuters logo in screenshot: check logo placement forensics first",
            "tools_used": ["tracker_x", "forensics_visual"],
            "outcome": "SUCCESS",
            "accuracy_delta": 0.35,
            "use_count": 6,
        },
        {
            "strategy_summary": "Telegram-originated claims spread 3x faster than X  -  track Telegram first",
            "tools_used": ["tracker_telegram", "tracker_x"],
            "outcome": "SUCCESS",
            "accuracy_delta": 0.15,
            "use_count": 9,
        },
        {
            "strategy_summary": "Audio-dubbed video variants: CLAP fingerprint mismatch detects 89% of fakes",
            "tools_used": ["forensics_audio", "forensics_visual"],
            "outcome": "SUCCESS",
            "accuracy_delta": 0.28,
            "use_count": 4,
        },
    ]

    for i, s in enumerate(oracle_strategies):
        entries.append({
            "material": s.get("material"),
            "pipeline": "oracle",
            "task_signature": f"{s.get('material', 'oracle')}_thesis_update",
            "strategy_summary": s["strategy_summary"],
            "tools_used": s["tools_used"],
            "tool_priority_order": s["tools_used"],
            "outcome": s["outcome"],
            "accuracy_delta": s["accuracy_delta"],
            "decay_score": max(0.7, 1.0 - (i * 0.05)),
            "similarity_embedding": None,  # Will be populated when embed runs
            "tags": [s.get("material", "oracle"), "oracle"],
            "created_at": now - timedelta(days=20 - i * 2),
            "last_used_at": now - timedelta(days=i),
            "use_count": s["use_count"],
        })

    for i, s in enumerate(forensics_strategies):
        entries.append({
            "material": None,
            "pipeline": "forensics",
            "task_signature": "claim_analysis",
            "strategy_summary": s["strategy_summary"],
            "tools_used": s["tools_used"],
            "tool_priority_order": s["tools_used"],
            "outcome": s["outcome"],
            "accuracy_delta": s["accuracy_delta"],
            "decay_score": max(0.65, 1.0 - (i * 0.08)),
            "similarity_embedding": None,
            "tags": ["forensics", "claim"],
            "created_at": now - timedelta(days=15 - i * 3),
            "last_used_at": now - timedelta(days=i + 1),
            "use_count": s["use_count"],
        })

    await db.reasoning_bank.insert_many(entries)
    log.info("Reasoning bank seeded", count=len(entries))


async def seed_skill_library() -> None:
    """Seed skill cards for each agent type."""
    db = get_db()
    await db.skill_library.delete_many({})
    now = datetime.utcnow()

    cards = [
        {
            "agent_type": "material_agent_soybeans",
            "version": 3,
            "system_prompt": (
                "You are a supply chain risk analyst specialising in agricultural commodities. "
                "Focus on: port operations, weather events, geopolitical trade policy. "
                "Always verify claimed disruptions against commodity price signals before escalating."
            ),
            "tool_list": ["brave_news", "commodity_price", "claim_verdicts"],
            "tool_priority_order": ["claim_verdicts", "commodity_price", "brave_news"],
            "planning_instructions": (
                "1. Always check ClaimVerdicts first  -  fabricated signals move this market. "
                "2. Cross-reference commodity price momentum before escalating risk. "
                "3. Only escalate to HIGH if both news AND price confirm disruption."
            ),
            "notes": "Tool priority updated after run #23  -  claim_verdicts now first",
            "created_at": now - timedelta(days=30),
            "updated_at": now - timedelta(days=2),
        },
        {
            "agent_type": "material_agent_neon",
            "version": 2,
            "system_prompt": (
                "You are a supply chain risk analyst specialising in semiconductor materials. "
                "Focus on: Ukrainian production, Odessa port, geopolitical signals. "
                "Neon price lags geopolitical signals by 6-8 weeks."
            ),
            "tool_list": ["brave_news", "claim_verdicts"],
            "tool_priority_order": ["brave_news", "claim_verdicts"],
            "planning_instructions": (
                "1. Monitor Odessa port status and Ukrainian gas processing plant signals. "
                "2. These lead neon price by 6-8 weeks  -  act early. "
                "3. Verify geopolitical signals against multiple news sources."
            ),
            "notes": "Leading indicator strategy learned from Feb 2022 backtest",
            "created_at": now - timedelta(days=45),
            "updated_at": now - timedelta(days=10),
        },
        {
            "agent_type": "forensics_orchestrator",
            "version": 2,
            "system_prompt": (
                "You are a disinformation forensics analyst. "
                "Your job is to determine if supply chain claims are authentic or fabricated. "
                "Be precise about evidence. Never make definitive claims without evidence."
            ),
            "tool_list": ["tracker_x", "tracker_telegram", "tracker_reddit",
                          "forensics_visual", "forensics_audio"],
            "tool_priority_order": ["tracker_telegram", "tracker_x", "tracker_reddit"],
            "planning_instructions": (
                "1. Check Telegram first  -  fabricated claims originate there 60% of the time. "
                "2. Look for media brand logos in screenshots  -  common fabrication pattern. "
                "3. Audio-dubbed videos: always run CLAP fingerprint check."
            ),
            "notes": "Platform priority updated after 15 forensics runs",
            "created_at": now - timedelta(days=20),
            "updated_at": now - timedelta(days=5),
        },
    ]

    await db.skill_library.insert_many(cards)
    log.info("Skill library seeded", count=len(cards))


async def seed_knowledge_facts() -> None:
    """Seed long-term knowledge facts."""
    db = get_db()
    await db.agent_knowledge.delete_many({})
    now = datetime.utcnow()

    facts = [
        {
            "entity": "Rotterdam_Port_Strike_Rumours",
            "entity_type": "supply_chain_event_pattern",
            "facts": {
                "historical_frequency": "3 fabricated incidents in 36 months",
                "avg_market_impact_pct": 1.8,
                "typical_origin_platforms": ["X", "Telegram"],
                "debunk_avg_time_hours": 6.2,
                "correlation_with_real_events": 0.31,
                "fabrication_signature": "Reuters/BBC logo in screenshot, viral before outlet pickup",
            },
            "valid_from": now - timedelta(days=90),
            "valid_to": None,
            "confidence": 0.88,
            "source_session_ids": ["historical_analysis"],
            "last_updated": now - timedelta(days=5),
        },
        {
            "entity": "Neon_Ukraine_Leading_Indicator",
            "entity_type": "material_signal_pattern",
            "facts": {
                "lead_time_weeks": "6-8",
                "key_signals": ["Odessa port activity", "Ukrainian gas processing output"],
                "accuracy": 0.79,
                "last_verified": "Feb 2022 crisis prediction",
                "source": "backtest_analysis",
            },
            "valid_from": now - timedelta(days=180),
            "valid_to": None,
            "confidence": 0.79,
            "source_session_ids": ["backtest_neon_001"],
            "last_updated": now - timedelta(days=30),
        },
        {
            "entity": "Fabricated_Port_Strike_Financial_Impact",
            "entity_type": "business_impact_pattern",
            "facts": {
                "avg_futures_movement_pct": 2.3,
                "avg_time_to_move_minutes": 40,
                "avg_debunk_time_hours": 6,
                "unnecessary_hedge_cost_estimate_gbp": 2300000,
                "case_study": "March 2024 Rotterdam fabricated strike",
            },
            "valid_from": now - timedelta(days=60),
            "valid_to": None,
            "confidence": 0.95,
            "source_session_ids": ["case_study_march_2024"],
            "last_updated": now - timedelta(days=7),
        },
    ]

    await db.agent_knowledge.insert_many(facts)
    log.info("Knowledge facts seeded", count=len(facts))


async def seed_agent_metrics() -> None:
    """Seed 30 days of synthetic agent performance metrics."""
    db = get_db()
    await db.agent_metrics_ts.delete_many({})
    now = datetime.utcnow()

    import random
    docs = []
    agents = [
        ("material_agent_soybeans", "oracle", "soybeans"),
        ("material_agent_neon", "oracle", "neon"),
        ("material_agent_palladium", "oracle", "palladium"),
        ("material_agent_lithium", "oracle", "lithium"),
        ("forensics_orchestrator", "forensics", None),
    ]
    outcomes = ["ok", "ok", "ok", "thesis_updated", "ok", "no_change"]

    for day_offset in range(30, 0, -1):
        ts = now - timedelta(days=day_offset, hours=random.randint(0, 5))
        for agent_id, pipeline, material in agents:
            # Latency improves over time (learning effect)
            base_latency = max(800, 4000 - day_offset * 80 + random.randint(-200, 200))
            docs.append({
                "timestamp": ts,
                "metadata": {"agent_id": agent_id, "pipeline": pipeline, "material": material},
                "latency_ms": base_latency,
                "outcome": random.choice(outcomes),
                "confidence": round(random.uniform(0.72, 0.97), 2),
            })

    await db.agent_metrics_ts.insert_many(docs)
    log.info("agent_metrics_ts seeded", count=len(docs))


async def seed_commodity_prices() -> None:
    """Seed 60 days of synthetic commodity price history."""
    db = get_db()
    await db.commodity_prices_ts.delete_many({})
    now = datetime.utcnow()

    import random
    base_prices = {
        "soybeans": 450.0,
        "palladium": 950.0,
        "lithium": 14000.0,
    }
    docs = []

    for material, base in base_prices.items():
        price = base
        for day_offset in range(60, 0, -1):
            ts = now - timedelta(days=day_offset)
            change_pct = round(random.uniform(-2.5, 2.5), 2)
            price = round(price * (1 + change_pct / 100), 2)
            fred_date = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            docs.append({
                "timestamp": ts,
                "metadata": {"material": material, "source": "FRED"},
                "price": price,
                "change_pct": change_pct,
                "fred_date": fred_date,
            })

    await db.commodity_prices_ts.insert_many(docs)
    log.info("commodity_prices_ts seeded", count=len(docs))


async def main():
    ok = await ping_db()
    if not ok:
        log.error("Cannot reach MongoDB Atlas  -  check MONGODB_URI in .env")
        return

    log.info("Starting seed data population...")
    await seed_material_theses()
    await seed_reasoning_bank()
    await seed_skill_library()
    await seed_knowledge_facts()
    await seed_agent_metrics()
    await seed_commodity_prices()
    log.info("All seed data populated successfully")


if __name__ == "__main__":
    asyncio.run(main())
