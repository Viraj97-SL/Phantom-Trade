"""
main.py
PHANTOM TRADE -- Entry point.
Usage:
  python main.py setup      # Create indexes + seed data
  python main.py demo       # Run the full demo scenario
  python main.py forensics  # Analyse a single claim
  python main.py oracle     # Run nightly Oracle
  python main.py watch      # Start change stream watcher
"""
import asyncio
import sys
from utils.logging import setup_logging, get_logger

setup_logging()
log = get_logger(__name__)


async def setup():
    """One-time setup: create indexes and seed demo data."""
    from db.indexes import create_all_indexes
    from db.seed_data import main as seed_main
    from db.connection import ping_db

    log.info("PHANTOM TRADE setup starting...")
    ok = await ping_db()
    if not ok:
        log.error("MongoDB Atlas unreachable. Check MONGODB_URI in .env")
        return

    log.info("Creating indexes...")
    await create_all_indexes()

    log.info("Seeding demo data...")
    await seed_main()

    log.info("Setup complete")
    log.info("Run 'python main.py demo' to execute the demo scenario")


async def run_demo():
    """
    Full demo scenario:
    1. Show current Oracle theses (baseline)
    2. Inject fabricated Rotterdam claim -> Forensics pipeline
    3. Show Oracle thesis revert in real-time
    4. Show ReasoningBank entry added
    5. Show bi-temporal thesis history
    """
    from agents.forensics.orchestrator import analyse_claim, get_recent_verdicts
    from agents.oracle.orchestrator import (
        get_all_thesis, get_thesis_history, handle_claim_verdict_trigger
    )
    from memory.reasoning_bank import get_bank_stats

    print("\n" + "="*60)
    print("  PHANTOM TRADE -- LIVE DEMO")
    print("  Fake signals move real markets. We stop them first.")
    print("="*60)

    # Step 1: Show baseline theses
    print("\n[STEP 1] Current Supply Risk Theses (Baseline)")
    print("-" * 50)
    theses = await get_all_thesis()
    for t in theses:
        print(f"  {t['material'].upper():<12} Risk: {t['risk_level']:>3}/100  [{t['risk_label']}]")

    # Step 2: Inject fabricated claim
    fabricated_claim = (
        "BREAKING: Rotterdam port workers have voted for indefinite strike action "
        "effective immediately. All soybean cargo operations halted. "
        "Sources: Reuters. #Rotterdam #SupplyChain"
    )

    print("\n[STEP 2] Fabricated Claim Detected")
    print("-" * 50)
    print(f"  Claim: {fabricated_claim[:100]}...")
    print("\n  Running Forensics Pipeline...")

    verdict = await analyse_claim(fabricated_claim)

    print("\n  Forensics Result:")
    print(f"     Verdict:    {verdict.verdict}")
    print(f"     Confidence: {verdict.confidence:.2f}")
    print(f"     Variants:   {verdict.variants_analysed} across platforms")
    print(f"     Topics:     {', '.join(verdict.supply_chain_topics)}")

    # Step 3: Oracle reacts
    print("\n[STEP 3] Oracle Pipeline Reacts to Verdict")
    print("-" * 50)
    print("  Change stream triggered -> Soybean agent re-running...")

    oracle_result = await handle_claim_verdict_trigger(
        verdict_id=verdict.claim_id,
        verdict=verdict.verdict,
        affected_materials=["soybeans"],
    )

    soy_result = oracle_result.get("soybeans", {})
    print("\n  Soybean Thesis Update:")
    print(f"     Status:     {soy_result.get('status', 'unknown')}")
    print(f"     Risk Level: {soy_result.get('risk_level', '?')}/100")
    print(f"     Risk Label: {soy_result.get('risk_label', '?')}")
    if verdict.verdict == "FABRICATED":
        print("     Signal invalidated -- no unnecessary hedge required")

    # Step 4: Show ReasoningBank update
    print("\n[STEP 4] ReasoningBank Updated (Agent Learning)")
    print("-" * 50)
    stats = await get_bank_stats()
    print(f"     Total entries:    {stats['total_entries']}")
    print(f"     Successful runs:  {stats['successful_entries']}")
    print(f"     Avg accuracy d:   +{stats['avg_accuracy_delta']:.3f}")
    print(f"     Hit rate:         {stats['hit_rate']:.0%}")
    print("     Each run makes the next one smarter")

    # Step 5: Bi-temporal demo
    print("\n[STEP 5] Bi-Temporal Thesis History (Soybeans)")
    print("-" * 50)
    history = await get_thesis_history("soybeans")
    for i, h in enumerate(history[:3]):
        status = "CURRENT" if h["valid_to"] is None else f"closed {str(h.get('valid_to', ''))[:10]}"
        print(f"  [{i+1}] {str(h['valid_from'])[:16]}  Risk: {h['risk_level']:>3}/100  "
              f"[{h['risk_label']}]  {status}")

    print("\n" + "="*60)
    print("  PHANTOM TRADE -- Fake signals stop here.")
    print("="*60 + "\n")


async def run_forensics():
    """Analyse a claim from command line."""
    from agents.forensics.orchestrator import analyse_claim
    claim = input("Enter claim to analyse: ").strip()
    if not claim:
        print("No claim provided.")
        return
    print("Analysing...")
    verdict = await analyse_claim(claim)
    print(f"\nVerdict: {verdict.verdict}")
    print(f"Confidence: {verdict.confidence:.2f}")
    print(f"Variants analysed: {verdict.variants_analysed}")
    print(f"Topics: {verdict.supply_chain_topics}")


async def run_oracle():
    """Run nightly Oracle for all materials."""
    from agents.oracle.orchestrator import run_nightly_oracle
    print("Running Oracle for all materials...")
    results = await run_nightly_oracle()
    for material, result in results.items():
        status = result.get("status", "?")
        risk = result.get("risk_level", "?")
        print(f"  {material:<12} {status:<20} risk={risk}")


async def watch():
    """Start change stream watcher."""
    from agents.oracle.orchestrator import watch_claim_verdicts
    print("Starting change stream watcher... (Ctrl+C to stop)")
    await watch_claim_verdicts()


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "demo"
    commands = {
        "setup": setup,
        "demo": run_demo,
        "forensics": run_forensics,
        "oracle": run_oracle,
        "watch": watch,
    }
    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)

    asyncio.run(commands[command]())
