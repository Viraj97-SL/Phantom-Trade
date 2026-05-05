"""
api.py
PHANTOM TRADE — FastAPI REST + SSE backend.
Run: uvicorn api:app --reload --port 8000
"""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.logging import setup_logging, get_logger

setup_logging()
log = get_logger(__name__)

_DEFAULT_SCENARIO_ID = "builtin-rotterdam-strike"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from db.seed_scenarios import seed as seed_scenarios
    try:
        await seed_scenarios()
    except Exception as exc:
        log.warning("Scenario seeding failed (non-fatal)", error=str(exc))
    yield


app = FastAPI(title="Phantom Trade API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    claim_text: str


class PointInTimeRequest(BaseModel):
    as_of: str  # ISO date string


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    from db.connection import ping_db
    mongo_ok = await ping_db()
    try:
        from utils.llm import get_haiku
        llm = get_haiku()
        llm_ok = len(llm._providers) > 0
    except Exception:
        llm_ok = False
    return {"status": "ok", "mongodb": mongo_ok, "llm": llm_ok}


# ── Thesis endpoints ──────────────────────────────────────────────────────────

@app.get("/api/thesis")
async def get_theses():
    from agents.oracle.orchestrator import get_all_thesis
    return await get_all_thesis()


@app.get("/api/thesis/{material}/history")
async def thesis_history(material: str):
    from agents.oracle.orchestrator import get_thesis_history
    return await get_thesis_history(material)


@app.get("/api/thesis/{material}/at/{date}")
async def thesis_at(material: str, date: str):
    """Return thesis valid at a specific point in time."""
    from db.connection import get_db
    from datetime import datetime as dt
    db = get_db()
    try:
        as_of = dt.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601.")
    doc = await db.supply_theses.find_one(
        {
            "material": material,
            "valid_from": {"$lte": as_of},
            "$or": [{"valid_to": None}, {"valid_to": {"$gt": as_of}}],
        },
        sort=[("valid_from", -1)],
    )
    if not doc:
        raise HTTPException(status_code=404, detail="No thesis found for that point in time.")
    doc["_id"] = str(doc["_id"])
    return doc


# ── Forensics endpoints ───────────────────────────────────────────────────────

@app.post("/api/forensics/analyse")
async def analyse(body: AnalyseRequest):
    from agents.forensics.orchestrator import analyse_claim
    verdict = await analyse_claim(body.claim_text)
    return verdict.model_dump()


@app.get("/api/forensics/verdicts")
async def get_verdicts():
    from agents.forensics.orchestrator import get_recent_verdicts
    return await get_recent_verdicts(10)


@app.get("/api/forensics/variants/{claim_id}")
async def get_variants(claim_id: str):
    from agents.forensics.tracker_agent import get_variants_for_claim
    variants = await get_variants_for_claim(claim_id)
    return [v.model_dump() for v in variants]


@app.get("/api/forensics/verdict/{claim_id}")
async def get_verdict(claim_id: str):
    from db.connection import get_db
    db = get_db()
    doc = await db.claim_verdicts.find_one({"claim_id": claim_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Verdict not found")
    doc["_id"] = str(doc["_id"])
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# ── Scenario endpoints ────────────────────────────────────────────────────────

class CreateScenarioRequest(BaseModel):
    name: str
    description: str = ""
    claim_text: str
    category: str = "custom"
    tags: list[str] = []


@app.get("/api/scenarios")
async def list_scenarios(category: Optional[str] = Query(default=None)):
    from db.scenarios import get_all_scenarios
    scenarios = await get_all_scenarios()
    if category:
        scenarios = [s for s in scenarios if s.category == category]
    return [s.model_dump() for s in scenarios]


@app.get("/api/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    from db.scenarios import get_scenario_by_id
    scenario = await get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario.model_dump()


@app.post("/api/scenarios", status_code=201)
async def create_scenario(body: CreateScenarioRequest):
    from db.scenarios import create_scenario as db_create
    from models.schemas import ScenarioTemplate
    scenario = ScenarioTemplate(
        name=body.name,
        description=body.description,
        claim_text=body.claim_text,
        category=body.category,
        tags=body.tags,
        created_by="user",
        is_builtin=False,
    )
    created = await db_create(scenario)
    return created.model_dump()


@app.delete("/api/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: str):
    from db.scenarios import delete_scenario as db_delete
    try:
        deleted = await db_delete(scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Scenario not found")


# ── Reasoning Bank endpoints ──────────────────────────────────────────────────

@app.get("/api/reasoning-bank/stats")
async def rb_stats():
    from memory.reasoning_bank import get_bank_stats
    return await get_bank_stats()


@app.get("/api/reasoning-bank/recent")
async def rb_recent():
    from db.connection import get_db
    db = get_db()
    entries = []
    async for doc in db.reasoning_bank.find().sort("created_at", -1).limit(5):
        doc["_id"] = str(doc["_id"])
        # Serialise datetime fields
        for k, v in doc.items():
            if isinstance(v, datetime):
                doc[k] = v.isoformat()
        entries.append(doc)
    return entries


# ── Demo endpoints ────────────────────────────────────────────────────────────

@app.post("/api/demo/inject-claim")
async def inject_demo_claim(scenario_id: Optional[str] = Query(default=None)):
    from agents.forensics.orchestrator import analyse_claim
    from db.scenarios import get_scenario_by_id
    sid = scenario_id or _DEFAULT_SCENARIO_ID
    scenario = await get_scenario_by_id(sid)
    claim_text = scenario.claim_text if scenario else (
        "BREAKING: Rotterdam port workers have voted for indefinite strike action "
        "effective immediately. All soybean cargo operations halted. "
        "Sources: Reuters. #Rotterdam #SupplyChain"
    )
    verdict = await analyse_claim(claim_text)
    return verdict.model_dump()


@app.post("/api/demo/reset")
async def reset_demo():
    """Reset theses back to seed values."""
    from db.connection import get_db
    from datetime import datetime as dt
    db = get_db()
    baseline = [
        {"material": "soybeans", "risk_level": 28, "risk_label": "STABLE",
         "narrative": "Baseline soybean supply is stable."},
        {"material": "neon", "risk_level": 45, "risk_label": "ELEVATED",
         "narrative": "Neon supply elevated due to regional tensions."},
        {"material": "palladium", "risk_level": 35, "risk_label": "STABLE",
         "narrative": "Palladium markets stable."},
        {"material": "lithium", "risk_level": 52, "risk_label": "ELEVATED",
         "narrative": "Lithium demand outpacing supply."},
    ]
    now = dt.utcnow()
    for item in baseline:
        await db.supply_theses.update_many(
            {"material": item["material"], "valid_to": None},
            {"$set": {"valid_to": now}},
        )
        item["valid_from"] = now
        item["valid_to"] = None
        item["triggered_by"] = "demo_reset"
        item["key_drivers"] = []
        await db.supply_theses.insert_one(item)
    return {"status": "reset", "materials": [i["material"] for i in baseline]}


async def _sse_demo_stream(claim_text: str) -> AsyncGenerator[str, None]:
    """Stream SSE events as the full forensics pipeline runs in real-time."""
    def event(event_type: str, data: dict) -> str:
        payload = json.dumps({"type": event_type, "data": data,
                              "timestamp": datetime.utcnow().isoformat()},
                             default=str)
        return f"data: {payload}\n\n"

    yield event("pipeline_started", {"claim_text": claim_text[:100]})

    import uuid
    from agents.forensics.tracker_agent import track_claim_variants
    from agents.forensics.debate_agent import run_debate
    from agents.forensics.orchestrator import (
        _run_llm_forensics, _build_mutation_summary, _build_evidence,
        _classify_supply_chain_topics,
    )
    from tools.ml import score_claim_ml
    from tools.forensics_search_tool import search_claim_in_news
    from agents.oracle.orchestrator import handle_claim_verdict_trigger
    from memory.reasoning_bank import get_bank_stats
    from middleware.guardrails import check_prompt_injection
    from models.schemas import ClaimVerdict
    from db.connection import get_db

    claim_id = str(uuid.uuid4())
    db = get_db()

    try:
        check_prompt_injection(claim_text)
    except ValueError as e:
        yield event("error", {"message": str(e)})
        return

    # Step 1: Track variants
    yield event("step", {"step": "tracking_variants",
                          "message": "Tracking variants across 5 platforms..."})
    variants = await track_claim_variants(claim_id, claim_text, claim_id)
    for v in variants:
        yield event("variant_found", v.model_dump())
        await asyncio.sleep(0.25)

    # Step 2: News cross-reference
    yield event("step", {"step": "news_crossref",
                          "message": "Cross-referencing against live news sources..."})
    topics = _classify_supply_chain_topics(claim_text)
    news_context = await search_claim_in_news(claim_text, topics)
    yield event("news_crossref_complete", {
        "major_outlets_reporting": news_context.get("major_outlets_reporting"),
        "total_coverage": news_context.get("total_coverage"),
        "summary": news_context.get("summary", ""),
    })

    # Step 3: LLM forensics + ML scoring in parallel
    yield event("step", {"step": "forensics",
                          "message": f"LLM analysing {len(variants)} variants for credibility signals..."})
    yield event("step", {"step": "ml_forensics",
                          "message": "Running ML scoring (TF-IDF, velocity, templates)..."})
    forensics_reports, ml_result = await asyncio.gather(
        _run_llm_forensics(variants, claim_text, news_context),
        score_claim_ml(claim_id, variants, claim_text, news_context),
    )
    mutation_summary = _build_mutation_summary(variants, news_context)
    yield event("ml_forensics_complete", {
        **ml_result.model_dump(),
        "created_at": ml_result.created_at.isoformat(),
    })
    yield event("forensics_complete", {
        "reports_count": len(forensics_reports),
        "mutation_summary": mutation_summary,
    })

    # Step 4: Debate
    yield event("step", {"step": "debate",
                          "message": "MAD-Sherlock debate agents deliberating..."})
    variant_dicts = [v.model_dump() for v in variants]
    report_dicts = [r.model_dump() for r in forensics_reports]
    debate_verdict = await run_debate(
        claim_id=claim_id,
        claim_text=claim_text,
        forensics_reports=report_dicts,
        variants=variant_dicts,
        news_context={**news_context, "ml_result": ml_result.model_dump()},
    )
    yield event("debate_complete", {
        "pro_authentic_score": debate_verdict.pro_authentic_score,
        "pro_fabricated_score": debate_verdict.pro_fabricated_score,
        "consensus_verdict": debate_verdict.consensus_verdict,
        "confidence": debate_verdict.confidence,
    })

    # Step 5: Verdict
    yield event("step", {"step": "verdict", "message": "Writing verdict to MongoDB..."})
    evidence = _build_evidence(forensics_reports, news_context)
    verdict = ClaimVerdict(
        claim_id=claim_id,
        claim_text=claim_text,
        verdict=debate_verdict.consensus_verdict,
        confidence=debate_verdict.confidence,
        evidence=evidence,
        mutation_graph_summary=mutation_summary,
        variants_analysed=len(variants),
        debate_transcript=(
            f"PRO-AUTHENTIC ({debate_verdict.pro_authentic_score:.2f}): "
            f"{debate_verdict.pro_authentic_reasoning[:200]}\n\n"
            f"PRO-FABRICATED ({debate_verdict.pro_fabricated_score:.2f}): "
            f"{debate_verdict.pro_fabricated_reasoning[:200]}"
        ),
        supply_chain_topics=topics,
        ml_result=ml_result,
    )

    verdict_dict = verdict.model_dump()
    # Serialise datetime
    for k, v in verdict_dict.items():
        if isinstance(v, datetime):
            verdict_dict[k] = v.isoformat()

    await db.claim_verdicts.insert_one(verdict.model_dump())
    yield event("verdict_written", verdict_dict)

    # Step 5: Oracle reaction
    yield event("oracle_triggered", {"materials": topics, "verdict": verdict.verdict})
    oracle_result = await handle_claim_verdict_trigger(
        verdict_id=verdict.claim_id,
        verdict=verdict.verdict,
        affected_materials=[t for t in topics if t in
                            ["soybeans", "neon", "palladium", "lithium"]],
    )
    for material, result in oracle_result.items():
        yield event("thesis_updated", {"material": material, **result})

    # Step 6: ReasoningBank
    stats = await get_bank_stats()
    yield event("reasoning_bank_updated", stats)

    yield event("pipeline_complete", {"claim_id": claim_id})


# ── Price & Metrics endpoints ─────────────────────────────────────────────────

@app.get("/api/prices/{material}")
async def get_price_history(material: str, days: int = 30):
    """Return commodity price history from commodity_prices_ts."""
    from db.connection import get_db
    from datetime import timezone
    db = get_db()
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    try:
        cursor = db.commodity_prices_ts.find(
            {"metadata.material": material, "timestamp": {"$gte": cutoff}},
            sort=[("timestamp", 1)],
            projection={"_id": 0, "timestamp": 1, "price": 1,
                        "change_pct": 1, "fred_date": 1},
        )
        points = await cursor.to_list(length=200)
        for p in points:
            if hasattr(p.get("timestamp"), "isoformat"):
                p["timestamp"] = p["timestamp"].isoformat()
        return {"material": material, "days": days, "count": len(points), "prices": points}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/metrics")
async def get_agent_metrics(pipeline: str = None, days: int = 7):
    """Return agent performance metrics from agent_metrics_ts."""
    from db.connection import get_db
    from datetime import timezone
    db = get_db()
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    query: dict = {"timestamp": {"$gte": cutoff}}
    if pipeline:
        query["metadata.pipeline"] = pipeline
    try:
        cursor = db.agent_metrics_ts.find(
            query,
            sort=[("timestamp", -1)],
            projection={"_id": 0, "timestamp": 1, "metadata": 1,
                        "latency_ms": 1, "confidence": 1, "outcome": 1},
        )
        docs = await cursor.to_list(length=500)
        for d in docs:
            if hasattr(d.get("timestamp"), "isoformat"):
                d["timestamp"] = d["timestamp"].isoformat()
        return {"days": days, "count": len(docs), "metrics": docs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/demo/stream")
async def demo_stream(
    claim: Optional[str] = Query(default=None),
    scenario_id: Optional[str] = Query(default=None),
):
    """SSE stream — runs the full forensics+oracle pipeline and emits events.
    Accepts either a raw claim text or a scenario_id to load from the library.
    Falls back to the default Rotterdam scenario when neither is provided.
    """
    from db.scenarios import get_scenario_by_id
    if claim:
        claim_text = claim
    elif scenario_id:
        scenario = await get_scenario_by_id(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        claim_text = scenario.claim_text
    else:
        scenario = await get_scenario_by_id(_DEFAULT_SCENARIO_ID)
        claim_text = scenario.claim_text if scenario else (
            "BREAKING: Rotterdam port workers have voted for indefinite strike action "
            "effective immediately. All soybean cargo operations halted. "
            "Sources: Reuters. #Rotterdam #SupplyChain"
        )
    return StreamingResponse(
        _sse_demo_stream(claim_text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
