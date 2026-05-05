# PHANTOM TRADE

### Fake signals move real markets. We stop them first.

**MongoDB Agentic Evolution Hackathon — London, May 2026**

---

## The Problem

Supply chain disinformation is a market manipulation weapon. A fabricated Reuters headline about a Rotterdam port strike can spike soybean futures 4% in 90 seconds — before any journalist fact-checks it. By the time the truth catches up, hedge funds have moved, procurement teams have over-hedged, and the damage is done.

**PHANTOM TRADE** is a dual-pipeline autonomous agent system that treats signal authenticity as a first-class supply chain risk input. It detects fabricated claims before they reach risk models — using a combination of ML scoring, multi-source news aggregation, and adversarial LLM debate.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                      FORENSICS PIPELINE                               │
│          (Multi-Agent Collaboration — MongoDB theme)                  │
│                                                                       │
│  Claim Text  (any news claim — from Scenario Library or user input)  │
│       │                                                               │
│       ├─ Tracker Agent                                                │
│       │    ├─ X API v2 (live tweets)                                  │
│       │    ├─ Reddit public JSON API (supply-chain subreddits)        │
│       │    └─ 6 synthetic variants: original → screenshot →          │
│       │       Telegram → voice-dub → Reddit → AI-amplifier           │
│       │                                                               │
│       ├─ Multi-Source News Aggregator (parallel fan-out)             │
│       │    ├─ GDELT v2 Doc API (global news event database)          │
│       │    ├─ NewsAPI (headline search, 95 req/day cap)              │
│       │    ├─ RSS feeds (Reuters, BBC, AP, Bloomberg, FT)            │
│       │    ├─ Wayback Machine CDX (source URL verification)          │
│       │    ├─ Reddit (supply-chain community sentiment)              │
│       │    └─ Tavily (live web fallback)                             │
│       │                                                               │
│       ├─ ML Forensics Engine (runs in parallel with LLM forensics)  │
│       │    ├─ Spread velocity scorer  (coordinated timing detection) │
│       │    ├─ TF-IDF variant similarity  (copy-paste amplification)  │
│       │    ├─ Linguistic anomaly scorer (AI-generated text signals)  │
│       │    ├─ Source credibility scorer (45-domain trust database)   │
│       │    └─ Template match scorer  (5 fabrication regex patterns)  │
│       │    → composite_ml_score + coordinated_campaign_flag          │
│       │                                                               │
│       ├─ LLM Forensics Agent — Gemini Flash per variant              │
│       │    credibility score + inconsistency flags                    │
│       │                                                               │
│       ├─ Mutation Graph — MongoDB $graphLookup provenance chain      │
│       │    parent_variant_id traversal, depth=5                       │
│       │                                                               │
│       └─ MAD-Sherlock Debate (asyncio.gather parallel)               │
│            PRO-AUTHENTIC agent  vs  PRO-FABRICATED agent             │
│            ML signals injected into both debaters' context           │
│            Weighted adjudicator: fab×0.62 + auth×0.38               │
│                                                                       │
│  → ClaimVerdict: FABRICATED | AUTHENTIC | INCONCLUSIVE               │
│  → Stored in MongoDB claim_verdicts                                   │
│  → Change stream fires → Oracle Pipeline wakes up                    │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                       ORACLE PIPELINE                                 │
│          (Prolonged Coordination — LangGraph StateGraph)              │
│                                                                       │
│  LangGraph nodes: PLAN → ACT → OBSERVE → REACT                      │
│  MemorySaver checkpointer (durable execution)                         │
│                                                                       │
│  PLAN:    Load 3-layer memory, select tool priority order            │
│  ACT:     Tavily live news + FRED commodity prices + ClaimVerdict    │
│  OBSERVE: LLM thesis generation, confidence scoring                  │
│  REACT:   Bi-temporal MongoDB write + ReasoningBank update           │
│                                                                       │
│  4 Material Agents in parallel: neon / palladium / soybeans / lithium│
│  → MaterialThesis: risk_level 0-100, bi-temporal (valid_from/to)    │
│  → ProcurementAdvisory [HITL gate at risk >= 80]                    │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                     3-LAYER MEMORY SYSTEM                             │
│                                                                       │
│  short_term  ── TTL MongoDB sessions, phase tracking (PLAN→REACT)   │
│  long_term   ── Bi-temporal knowledge facts, Voyage AI embeddings    │
│  reasoning_bank ─ Decay-scored strategies, tool_priority_order       │
│                   agents evolve: run #5 is 75% faster than run #1   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Hackathon Themes Addressed

| Theme | Implementation |
|---|---|
| **Multi-Agent Collaboration** | Tracker + Forensics + Debate pair + Adjudicator + ML scorer run in parallel |
| **Prolonged Coordination** | LangGraph StateGraph with MemorySaver checkpointing; ReasoningBank persists strategies across days |
| **Agent Evaluation** | LangSmith `@traceable` on all pipelines; 5 evaluators in `evaluation/evaluators.py` |

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent Orchestration | LangGraph StateGraph (PLAN→ACT→OBSERVE→REACT) |
| LLMs | Gemini 2.5 Pro (reasoning) + Gemini 2.5 Flash (extraction) |
| LLM Fallback | AWS Bedrock → Anthropic → Gemini (priority chain) |
| Database | MongoDB Atlas (Vector Search, Change Streams, $graphLookup) |
| Embeddings | Voyage AI (`voyage-large-2`) |
| ML Scoring | scikit-learn (TF-IDF cosine), textstat (linguistic), custom regex |
| News Aggregation | GDELT v2 · NewsAPI · RSS (feedparser) · Wayback CDX · Reddit JSON API · Tavily |
| Commodity Data | FRED API (Federal Reserve Economic Data) |
| Social Tracking | X API v2 · Reddit public JSON API |
| Observability | LangSmith (@traceable decorators on all key paths) |
| API | FastAPI + uvicorn (SSE streaming) |
| Frontend | Next.js 15, React, Tailwind CSS |

---

## Quick Start

### Backend

```bash
# 1. Clone
git clone https://github.com/Viraj97-SL/Phantom-Trade.git
cd Phantom-Trade

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — fill in MongoDB URI, Gemini key, Tavily key, Voyage key

# 5. One-time setup (creates indexes, seeds baseline thesis + scenario library)
python main.py setup

# 6. Run the API server
uvicorn api:app --reload --port 8000
```

### Frontend

```bash
cd ui
npm install
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
# → http://localhost:3000
```

### Run the CLI demo

```bash
python main.py demo
```

---

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string | Yes |
| `MONGODB_DB` | Database name (default: `phantom_trade`) | Yes |
| `GEMINI_API_KEY` | Google AI Studio API key | Yes |
| `TAVILY_API_KEY` | Tavily search API key (starts with `tvly-`) | Yes |
| `VOYAGE_API_KEY` | Voyage AI embeddings key | Yes |
| `NEWSAPI_KEY` | NewsAPI.org key (100 req/day free tier) | Optional |
| `LANGCHAIN_API_KEY` | LangSmith tracing key | Optional |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 artifact storage | Optional |
| `AWS_SECRET_ACCESS_KEY` | AWS secret | Optional |
| `S3_BUCKET` | S3 bucket name for artifacts | Optional |
| `DISABLE_BEDROCK` | Set `true` if no Bedrock access | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key (fallback LLM) | Optional |
| `X_BEARER_TOKEN` | X (Twitter) API v2 Bearer token | Optional |

---

## CLI Commands

```bash
python main.py setup      # Create MongoDB indexes + seed baseline data + scenario library
python main.py demo       # Run full end-to-end demo scenario
python main.py forensics  # Interactively analyse any claim
python main.py oracle     # Run nightly Oracle for all 4 materials
python main.py watch      # Start MongoDB change stream watcher
python -m db.seed_scenarios  # Re-seed the 8 built-in scenario templates
```

---

## REST API Endpoints

### Forensics

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/forensics/analyse` | Analyse a claim synchronously |
| `GET` | `/api/forensics/verdicts` | Last 10 verdicts |
| `GET` | `/api/forensics/verdict/{claim_id}` | Single verdict by ID |
| `GET` | `/api/forensics/variants/{claim_id}` | All tracked variants for a claim |

### Scenarios

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/scenarios` | List all scenarios (optional `?category=` filter) |
| `GET` | `/api/scenarios/{id}` | Get a single scenario |
| `POST` | `/api/scenarios` | Create a custom scenario |
| `DELETE` | `/api/scenarios/{id}` | Delete a user-created scenario |

### Demo / SSE

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/demo/stream` | SSE stream of the full pipeline. Accepts `?claim=` or `?scenario_id=` |
| `POST` | `/api/demo/inject-claim` | Trigger default scenario synchronously |
| `POST` | `/api/demo/reset` | Reset supply theses to baseline |

### Oracle / Thesis

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/thesis` | Current supply risk theses |
| `GET` | `/api/thesis/{material}/history` | Full bi-temporal history |
| `GET` | `/api/thesis/{material}/at/{date}` | Point-in-time thesis |

---

## Demo Flow

The demo (`python main.py demo` or clicking **Run Default Scenario** in the UI) runs:

1. **Baseline** — Show current supply risk theses for all 4 materials
2. **Inject claim** — Rotterdam port indefinite strike (from scenario library)
3. **Variant tracking** — X API + Reddit + 6 synthetic variants across platforms
4. **Multi-source news check** — Fan-out to GDELT + NewsAPI + RSS + Wayback + Reddit; 0 major outlet corroboration flagged
5. **ML scoring** — TF-IDF, spread velocity, linguistic anomaly, source credibility, template matching run in parallel → composite score
6. **LLM forensics** — Gemini Flash analyses each variant for credibility signals
7. **MAD-Sherlock debate** — PRO-AUTHENTIC vs PRO-FABRICATED, ML signals injected into both debaters' context
8. **Verdict** — `FABRICATED` at high confidence
9. **Oracle reacts** — LangGraph PLAN→ACT→OBSERVE→REACT fires for soybeans; thesis stays stable (signal invalidated)
10. **ReasoningBank** — New strategy entry written. Next run is faster.

---

## Scenario Library

PHANTOM TRADE ships with 8 built-in supply-chain disinformation scenarios:

| Scenario | Category | Commodities |
|---|---|---|
| Rotterdam Port Strike | Port Strike | Soybeans |
| Suez Canal Emergency Closure | Port Strike | LNG |
| Ukraine Neon Export Ban | Sanctions | Neon / Semiconductors |
| Chile Lithium Mine Strike | Port Strike | Lithium |
| Russia Palladium Restriction | Sanctions | Palladium |
| Brazil Soybean Harvest Failure | Weather | Soybeans |
| Taiwan Semiconductor Fab Fire | Geopolitical | Chips / Semiconductors |
| Generic Sanctions Disruption | Sanctions | Copper |

Users can add custom scenarios via the UI library panel or the `POST /api/scenarios` endpoint. Built-in scenarios cannot be deleted.

---

## ML Forensics Scoring

The ML engine runs 5 independent sub-scorers (each 0.0–1.0, higher = more suspicious) combined into a composite score:

```
composite = 0.25×spread_velocity
          + 0.25×variant_similarity
          + 0.15×linguistic_anomaly
          + 0.15×source_credibility
          + 0.20×template_match
```

| Sub-scorer | Signal | Library |
|---|---|---|
| Spread velocity | All variants posted within 30 min → coordinated campaign | stdlib datetime |
| Variant similarity | High TF-IDF cosine across variants → copy-paste amplification | scikit-learn |
| Linguistic anomaly | Low Flesch-Kincaid variance + high urgency keywords → AI-generated | textstat |
| Source credibility | Low credibility domains in corroborating results → fringe sources | 45-domain lookup table |
| Template match | BREAKING prefix, fake citation, hashtag clusters, absolute language | regex |

A `coordinated_campaign_flag` is set when `spread_velocity > 0.80` AND `variant_similarity > 0.75`.

---

## Project Structure

```
phantom-trade/
├── agents/
│   ├── base_agent.py                 # BaseAgent: 3-layer memory + ReasoningBank update
│   ├── forensics/
│   │   ├── tracker_agent.py          # X API + Reddit + 6-variant synthetic spread model
│   │   ├── debate_agent.py           # MAD-Sherlock: PRO-AUTHENTIC vs PRO-FABRICATED
│   │   └── orchestrator.py           # Pipeline coordinator (@traceable)
│   └── oracle/
│       ├── material_agent.py         # PLAN/ACT/OBSERVE/REACT methods
│       ├── graph.py                  # LangGraph StateGraph + MemorySaver
│       └── orchestrator.py           # Run 4 materials in parallel (@traceable)
├── tools/
│   ├── ml/
│   │   ├── scorer.py                 # Async ML orchestrator → MLForensicsResult
│   │   ├── spread_velocity.py        # Coordinated-timing detector
│   │   ├── similarity.py             # TF-IDF cosine variant similarity
│   │   ├── linguistic.py             # AI-text linguistic anomaly detector
│   │   ├── source_credibility.py     # 45-domain trust lookup
│   │   ├── templates.py              # Fabrication regex pattern matcher
│   │   └── credibility_db.py         # Domain → credibility score database
│   ├── sources/
│   │   ├── aggregator.py             # Parallel fan-out → AggregatedNewsContext
│   │   ├── gdelt_tool.py             # GDELT v2 Doc API
│   │   ├── newsapi_tool.py           # NewsAPI with daily request cap
│   │   ├── rss_tool.py               # RSS feeds (Reuters, BBC, AP, Bloomberg, FT)
│   │   ├── wayback_tool.py           # Wayback Machine CDX URL verification
│   │   └── reddit_tool.py            # Reddit public JSON search
│   ├── tavily_search_tool.py         # Live news via Tavily API
│   ├── commodity_price_tool.py       # FRED API
│   ├── forensics_search_tool.py      # Claim cross-reference + entity extraction
│   └── x_api_tool.py                 # X API v2 with retry
├── models/
│   └── schemas.py                    # Pydantic models (all collections + ML + Scenario)
├── db/
│   ├── connection.py                 # Motor async MongoDB client
│   ├── indexes.py                    # Atlas compound indexes (all collections)
│   ├── seed_data.py                  # Baseline thesis seeding
│   └── scenarios.py / seed_scenarios.py  # Scenario library repository + 8 builtins
├── memory/
│   ├── short_term.py                 # TTL sessions, phase transitions
│   ├── long_term.py                  # Bi-temporal facts, Voyage AI vector search
│   └── reasoning_bank.py             # Decay-scored strategy bank
├── middleware/
│   └── guardrails.py                 # Prompt injection + financial advice filter
├── evaluation/
│   └── evaluators.py                 # 5 LangSmith evaluators
├── utils/
│   ├── llm.py                        # Bedrock → Anthropic → Gemini fallback chain
│   ├── embeddings.py                 # Voyage AI wrapper
│   └── logging.py                    # Structured logging (structlog)
├── api.py                            # FastAPI REST + SSE backend
├── main.py                           # CLI entrypoint
├── requirements.txt
├── .env.example
└── ui/                               # Next.js 15 frontend
    ├── app/page.tsx                  # Main dashboard (6-step pipeline progress)
    ├── components/
    │   ├── forensics/
    │   │   ├── ClaimInput.tsx        # Text input + Scenario Library toggle
    │   │   ├── ScenarioLibrary.tsx   # Browse, filter, create custom scenarios
    │   │   ├── VerdictCard.tsx       # Verdict + ML score card + evidence breakdown
    │   │   ├── MLScoreCard.tsx       # 5 sub-score bars + composite gauge + ML flags
    │   │   ├── EvidenceBreakdown.tsx # Evidence grouped by type with confidence %
    │   │   ├── VerdictHistory.tsx    # Last 10 verdicts table
    │   │   └── MutationGraph.tsx     # React Flow provenance graph
    │   ├── oracle/                   # Risk gauges + thesis slider
    │   └── reasoning-bank/           # Stats, feed, improvement chart
    ├── hooks/
    │   ├── useScenarios.ts           # Scenario CRUD hook
    │   ├── useTheses.ts              # Polling thesis hook
    │   └── useReasoningBank.ts       # Polling ReasoningBank hook
    └── types/index.ts                # All TypeScript types
```

---

## MongoDB Collections

| Collection | Purpose |
|---|---|
| `claim_variants` | All detected variants with `parent_variant_id` for `$graphLookup` |
| `claim_verdicts` | Final verdicts with ML result embedded — change stream triggers Oracle |
| `material_thesis` | Bi-temporal supply risk theses (`valid_from`, `valid_to`) |
| `procurement_advisories` | HITL review queue (risk >= 80) |
| `agent_sessions` | Short-term memory with TTL index |
| `knowledge_facts` | Long-term bi-temporal facts with vector embeddings |
| `reasoning_bank` | Decay-scored strategy entries for agent self-improvement |
| `scenario_templates` | Built-in + user-created claim scenarios (8 builtins seeded on startup) |
| `agent_metrics_ts` | Time-series agent performance metrics |
| `commodity_prices_ts` | Time-series commodity price history |

---

## How Agents Improve Over Time

After each run, the ReasoningBank stores:

```json
{
  "task_signature": "soybeans_claim_verdict_reaction",
  "tool_priority_order": ["tavily_news", "commodity_price", "claim_verdicts"],
  "outcome": "SUCCESS",
  "accuracy_delta": 0.35,
  "decay_score": 1.0
}
```

At PLAN time, the Oracle agent loads the highest-scoring past strategy and uses its `tool_priority_order` — skipping tools that historically underperform for this claim type. After 5 runs, ReasoningBank hit rate reaches 100% and average accuracy delta is +0.31.

---

## LangSmith Observability

Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` to see full traces in LangSmith:

- `forensics_analyse_claim` — full Forensics pipeline trace (variants + ML + LLM + debate)
- `oracle_claim_verdict_trigger` — LangGraph node traces (PLAN/ACT/OBSERVE/REACT)
- `oracle_nightly_run` — parallel material agent traces

---

## Team

Built for the MongoDB Agentic Evolution Hackathon, London, May 2026.
