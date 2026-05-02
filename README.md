# PHANTOM TRADE

### Fake signals move real markets. We stop them first.

**MongoDB Agentic Evolution Hackathon — London, May 2026**

---

## The Problem

Supply chain disinformation is a market manipulation weapon. A fabricated Reuters headline about a Rotterdam port strike can spike soybean futures 4% in 90 seconds — before any journalist fact-checks it. By the time the truth catches up, hedge funds have moved, procurement teams have over-hedged, and the damage is done.

**PHANTOM TRADE** is a dual-pipeline autonomous agent system that treats signal authenticity as a first-class supply chain risk input. It detects fabricated claims before they reach risk models.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     FORENSICS PIPELINE                            │
│         (Multi-Agent Collaboration — MongoDB theme)               │
│                                                                   │
│  Claim Text                                                       │
│       │                                                           │
│       ├─ Tracker Agent ─── X API v2 + synthetic spread models    │
│       │                     6 variants: original → screenshot →  │
│       │                     Telegram → dub → Reddit → AI-augment │
│       │                                                           │
│       ├─ Forensics Agent ─ LLM per variant (Gemini Flash)        │
│       │                    credibility score + inconsistency flags│
│       │                                                           │
│       ├─ Mutation Graph ── MongoDB $graphLookup provenance chain  │
│       │                    parent_variant_id traversal, depth=5   │
│       │                                                           │
│       └─ MAD-Sherlock Debate (2 agents, asyncio.gather parallel) │
│            PRO-AUTHENTIC agent  vs  PRO-FABRICATED agent         │
│            Weighted adjudicator: fab×0.62 + auth×0.38           │
│                                                                   │
│  → ClaimVerdict: FABRICATED | AUTHENTIC | INCONCLUSIVE           │
│  → Stored in MongoDB claim_verdicts + S3 audit artifact          │
│  → Change stream fires → Oracle Pipeline wakes up                │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      ORACLE PIPELINE                              │
│         (Prolonged Coordination — LangGraph StateGraph)           │
│                                                                   │
│  LangGraph nodes: PLAN → ACT → OBSERVE → REACT                  │
│  MemorySaver checkpointer (durable execution)                     │
│                                                                   │
│  PLAN:    Load 3-layer memory, select tool priority order        │
│  ACT:     Tavily live news + FRED commodity prices + ClaimVerdict│
│  OBSERVE: LLM thesis generation, confidence scoring              │
│  REACT:   Bi-temporal MongoDB write + S3 artifact + ReasoningBank│
│                                                                   │
│  4 Material Agents in parallel: neon / palladium / soybeans / lithium
│  → MaterialThesis: risk_level 0-100, bi-temporal (valid_from/to) │
│  → ProcurementAdvisory [HITL gate at risk >= 80]                 │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    3-LAYER MEMORY SYSTEM                          │
│                                                                   │
│  short_term  ── TTL MongoDB sessions, phase tracking (PLAN→REACT)│
│  long_term   ── Bi-temporal knowledge facts, Voyage AI embeddings │
│  reasoning_bank ─ Decay-scored strategies, tool_priority_order   │
│                   agents evolve: run #5 is 75% faster than run #1│
└──────────────────────────────────────────────────────────────────┘
```

---

## Hackathon Themes Addressed

| Theme | Implementation |
|---|---|
| **Multi-Agent Collaboration** | Tracker + Forensics + Debate pair + Adjudicator run in parallel |
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
| News Search | Tavily API (live web + news) |
| Commodity Data | FRED API (Federal Reserve Economic Data) |
| Artifact Storage | AWS S3 (forensics verdicts + oracle theses) |
| Observability | LangSmith (@traceable decorators on all key paths) |
| API | FastAPI + uvicorn |
| Frontend | Next.js 15, React, Framer Motion, Tailwind CSS |

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

# 5. One-time setup (creates indexes + seeds baseline thesis data)
python main.py setup

# 6. Run the full demo
python main.py demo
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

### API Server

```bash
# In the root directory
uvicorn api:app --reload --port 8000
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Required |
|---|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string | Yes |
| `MONGODB_DB` | Database name (default: `phantom_trade`) | Yes |
| `GEMINI_API_KEY` | Google AI Studio API key | Yes |
| `TAVILY_API_KEY` | Tavily search API key (starts with `tvly-`) | Yes |
| `VOYAGE_API_KEY` | Voyage AI embeddings key | Yes |
| `LANGCHAIN_API_KEY` | LangSmith tracing key | Optional |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 artifact storage | Optional |
| `AWS_SECRET_ACCESS_KEY` | AWS secret | Optional |
| `S3_BUCKET` | S3 bucket name for artifacts | Optional |
| `DISABLE_BEDROCK` | Set `true` if no Bedrock access | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key (fallback LLM) | Optional |

---

## CLI Commands

```bash
python main.py setup      # Create MongoDB indexes + seed baseline data
python main.py demo       # Run full end-to-end demo scenario
python main.py forensics  # Interactively analyse a claim
python main.py oracle     # Run nightly Oracle for all 4 materials
python main.py watch      # Start MongoDB change stream watcher
```

---

## Demo Flow

The demo (`python main.py demo`) runs this scenario:

1. **Baseline** — Show current supply risk theses for all 4 materials
2. **Inject claim** — A fabricated "Rotterdam port indefinite strike" headline
3. **Forensics** — 6 variants tracked, `$graphLookup` provenance graph built, MAD-Sherlock debate runs
4. **Verdict** — `FABRICATED` at 1.00 confidence
5. **Oracle reacts** — LangGraph PLAN→ACT→OBSERVE→REACT fires for soybeans
6. **No escalation** — Thesis stays stable. Signal invalidated. No unnecessary hedge.
7. **ReasoningBank** — New strategy entry written. Next run is faster.
8. **Bi-temporal history** — Full thesis version chain visible

---

## Project Structure

```
Phantom-Trade/
├── agents/
│   ├── base_agent.py              # BaseAgent: 3-layer memory loading + ReasoningBank update
│   ├── forensics/
│   │   ├── tracker_agent.py       # X API + 6-variant synthetic spread model
│   │   ├── debate_agent.py        # MAD-Sherlock: PRO-AUTHENTIC vs PRO-FABRICATED
│   │   └── orchestrator.py        # Pipeline coordinator (@traceable)
│   └── oracle/
│       ├── material_agent.py      # PLAN/ACT/OBSERVE/REACT methods
│       ├── graph.py               # LangGraph StateGraph + MemorySaver
│       └── orchestrator.py        # Run 4 materials in parallel (@traceable)
├── memory/
│   ├── short_term.py              # TTL sessions, phase transitions
│   ├── long_term.py               # Bi-temporal facts, Voyage AI vector search
│   └── reasoning_bank.py          # Decay-scored strategy bank
├── tools/
│   ├── tavily_search_tool.py      # Live news via Tavily API
│   ├── commodity_price_tool.py    # FRED API (soybean, neon, palladium, lithium)
│   ├── forensics_search_tool.py   # Claim cross-reference + entity extraction
│   ├── brave_search_tool.py       # Backward-compat wrapper → Tavily
│   └── x_api_tool.py              # X API v2 with retry
├── models/
│   └── schemas.py                 # Pydantic models (ClaimVariant, MaterialThesis, etc.)
├── db/
│   ├── connection.py              # Motor async MongoDB client
│   ├── indexes.py                 # Atlas Vector Search + compound indexes
│   └── seed_data.py               # Baseline thesis seeding
├── middleware/
│   └── guardrails.py              # Prompt injection + financial advice filter
├── evaluation/
│   └── evaluators.py              # 5 LangSmith evaluators
├── utils/
│   ├── llm.py                     # Bedrock → Anthropic → Gemini fallback chain
│   ├── s3.py                      # S3 artifact storage (non-blocking)
│   ├── embeddings.py              # Voyage AI wrapper
│   └── logging.py                 # Structured logging (structlog)
├── config/
│   └── settings.py                # Pydantic Settings
├── tests/                         # pytest test suite
├── api.py                         # FastAPI REST API
├── main.py                        # CLI entrypoint
├── requirements.txt
├── .env.example
└── ui/                            # Next.js frontend
    ├── app/                       # Next.js App Router
    ├── components/
    │   ├── forensics/             # Forensics dashboard
    │   ├── oracle/                # Oracle thesis viewer
    │   └── reasoning-bank/        # ReasoningBank visualisation
    └── package.json
```

---

## MongoDB Collections

| Collection | Purpose |
|---|---|
| `claim_variants` | All detected variants with `parent_variant_id` for `$graphLookup` |
| `claim_verdicts` | Final verdicts — change stream triggers Oracle |
| `material_thesis` | Bi-temporal supply risk theses (`valid_from`, `valid_to`) |
| `procurement_advisories` | HITL review queue (risk >= 80) |
| `agent_sessions` | Short-term memory with TTL index |
| `knowledge_facts` | Long-term bi-temporal facts with vector embeddings |
| `reasoning_bank` | Decay-scored strategy entries for agent self-improvement |

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

- `forensics_analyse_claim` — full Forensics pipeline trace
- `oracle_claim_verdict_trigger` — LangGraph node traces (PLAN/ACT/OBSERVE/REACT)
- `oracle_nightly_run` — parallel material agent traces

---

## Team

Built for the MongoDB Agentic Evolution Hackathon, London, May 2026.
