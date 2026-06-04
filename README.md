# EcoHome AI Assistant

A production-grade AI chatbot for a fictional smart home energy company — built to demonstrate end-to-end AI QA strategy, RAG pipeline design, and formal evaluation methodology.

> **Portfolio project by Simon Dina.** All knowledge base content is sourced from publicly available UK government and charity publications. This project does not reference or contain any proprietary work from any employer.

---

## What It Does

EcoHome AI Assistant answers customer questions about:
- Solar panels, home batteries, EV chargers, smart thermostats
- UK government grants and eligibility (ECO4, Warm Homes, OZEV, SEG, 0% VAT)
- Warranties, installation process, and pricing
- Booking a free consultation (`[BOOK_CONSULTATION]` structured command)

Built to test real AI QA dimensions: **RAG accuracy · hallucination control · compliance guardrails · out-of-scope refusal · adversarial injection · structured command detection · multi-turn conversation**

---

## Architecture

```
iOS App (SwiftUI)          ← Layer 3 (in progress)
        │
        ▼
FastAPI /chat endpoint     ← Layer 2
        │
   ┌────┴────┐
   ▼         ▼
ChromaDB   Redis
(vectors)  (conversation
           history)
   │
   ▼
Claude API (claude-opus-4-1)
        │
        ▼
Langfuse (observability)
```

**Stack:** FastAPI · ChromaDB · sentence-transformers · Claude API · Redis · Langfuse · Docker Compose · SwiftUI

---

## Project Structure

```
ecohome-ai-assistant/
├── knowledge-base/          # Layer 1 — Domain knowledge base
│   ├── solar-panels.md
│   ├── home-batteries.md
│   ├── ev-chargers.md
│   ├── smart-thermostats.md
│   ├── warranties.md
│   ├── installation.md
│   ├── grants-eligibility.md
│   ├── pricing.md
│   ├── booking-consultation.md
│   └── pdfs/                # 6 source PDFs (GOV.UK, EST, MCS, Parliament)
│
├── backend/                 # Layer 2 — RAG backend
│   ├── api/
│   │   ├── main.py          # FastAPI app — /chat /feedback /booking /products
│   │   ├── rag.py           # RAG engine — retrieve() + generate()
│   │   ├── products.py      # Product catalogue (11 products)
│   │   ├── observability.py # Langfuse tracking
│   │   └── config.py        # Settings via pydantic-settings
│   ├── scripts/
│   │   └── ingest.py        # KB ingestion → ChromaDB
│   └── prompts/
│       └── system-prompt.md # Claude system prompt with guardrails
│
├── qa/                      # Layer 4 — QA evaluation suite
│   ├── scenarios/           # 9 YAML test scenarios
│   ├── src/                 # TypeScript eval runner
│   │   ├── run.ts
│   │   ├── assertions.ts
│   │   ├── guardrails.ts
│   │   └── types.ts
│   ├── ragas/
│   │   └── evaluate.py      # Ragas faithfulness/relevancy scoring
│   └── reports/             # Eval run reports
│       ├── run-001-2026-06-03.md  # Run 1: 6/9 (67%)
│       └── run-002-2026-06-03.md  # Run 2: 9/9 (100%)
│
├── ios/                     # Layer 3 — iOS SwiftUI app (in progress)
│   └── EcoHomeApp/
│
└── docker-compose.yml       # 4-container stack
```

---

## Quick Start

### Prerequisites
- Docker Desktop
- Anthropic API key
- Node.js 18+
- Python 3.12

### 1. Clone and configure

```bash
git clone https://github.com/Millnr/ecohome-ai-assistant.git
cd ecohome-ai-assistant
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Start the stack

```bash
docker compose up -d
```

This starts:
| Service | URL | Role |
|---|---|---|
| FastAPI | http://localhost:8000 | Chat API |
| Flowise | http://localhost:3000 | RAG orchestration UI |
| ChromaDB | http://localhost:8001 | Vector store |
| Redis | localhost:6379 | Conversation cache |

### 3. Ingest the knowledge base

```bash
docker exec ecohome-api python3 /app/scripts/ingest.py
```

This chunks, embeds, and stores all 9 KB documents in ChromaDB (63 chunks, 384-dim embeddings).

### 4. Test the chat endpoint

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How much does a solar panel system cost?"}'
```

---

## QA Evaluation

The project includes a formal QA test suite covering 9 dimensions of AI chatbot quality.

### Run the eval suite

```bash
cd qa
npm install
cp .env.example .env
npm run eval
```

### Run Ragas scoring

```bash
npm run eval:ragas
```

### Results

| Run | Date | Pass Rate | Notes |
|---|---|---|---|
| Run 1 | 2026-06-03 | 6/9 (67%) | 3 test/guardrail bugs identified |
| Run 2 | 2026-06-03 | 9/9 (100%) | All P1 fixes applied |

See [`qa/reports/`](qa/reports/) for full failure analysis and root-cause documentation.

### QA Dimensions Covered

| Scenario | Dimension |
|---|---|
| `solar_pricing_grounded` | RAG accuracy |
| `hallucination_warranty` | Hallucination control |
| `installer_guardrail` | Compliance guardrail |
| `ozev_grant_guardrail` | Compliance guardrail (OZEV grant misinformation) |
| `stale_knowledge_grants` | Stale knowledge / compliance caveating |
| `out_of_scope_refusal` | Out-of-scope refusal |
| `prompt_injection_blocked` | Adversarial injection |
| `book_consultation_triggered` | Structured command detection |
| `multi_turn_battery_recommendation` | Multi-turn conversation memory |

---

## Knowledge Base Sources

All KB content is based on publicly available UK government, charity, and industry body sources:

| Source | Topics |
|---|---|
| GOV.UK | Warm Homes Plan, ECO4, Boiler Upgrade Scheme, OZEV grants |
| Energy Saving Trust | Solar panels, battery storage, heating controls |
| MCS | Installer certification, consumer protection |
| SP Energy Networks | Battery storage guide |
| Parliament.uk | New Homes Solar Generation Bill briefing |
| DESNZ | UK Solar Roadmap 2025 |

> All knowledge base content is fictional product data for demonstration purposes. EcoHome is not a real company.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/chat` | POST | Send a message, receive AI reply + sources |
| `/feedback` | POST | Submit thumbs up/down on a response |
| `/booking` | POST | Submit consultation booking form |
| `/products` | GET | Retrieve product catalogue |

### Chat request/response

```json
// POST /chat
{ "message": "How much does solar cost?", "session_id": "optional-uuid" }

// Response
{
  "reply": "Solar panel systems from EcoHome typically cost...",
  "session_id": "abc-123",
  "structured_command": null,
  "sources": ["pricing", "solar-panels"],
  "latency_ms": 3200
}
```

---

## Guardrails

Five critical guardrails are enforced at the system prompt and knowledge base level:

1. **No installer recommendations** — never names a specific third-party installer; directs to MCS finder
2. **OZEV grant accuracy** — correctly states the homeowner EV charger grant ended March 2022
3. **Grant staleness caveat** — always adds "confirm current eligibility at gov.uk"
4. **No definitive financial/legal advice** — uses qualifying language throughout
5. **Indicative pricing only** — always qualifies prices as estimate pending a survey

---

## Roadmap

- [x] Layer 1 — Knowledge base (9 topics, 6 source PDFs)
- [x] Layer 2 — RAG backend (FastAPI + ChromaDB + Claude API + Redis + Langfuse)
- [ ] Layer 3 — iOS SwiftUI chat UI
- [x] Layer 4 — QA evaluation suite (9 scenarios, 2 runs, 100% pass rate)
- [ ] PDF ingestion pipeline
- [ ] Ragas scoring in CI
- [ ] Railway.app cloud deployment

---

## Author

**Simon Dina** — AI QA Strategy & Evaluation

Built with [Claude Code](https://claude.ai/code) · [Anthropic](https://anthropic.com)
