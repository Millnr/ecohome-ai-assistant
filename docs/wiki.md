# EcoHome AI Assistant — Project Wiki

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Components](#3-components)
   - [3.1 iOS App (SwiftUI)](#31-ios-app-swiftui)
   - [3.2 FastAPI Backend](#32-fastapi-backend)
   - [3.3 RAG Engine](#33-rag-engine)
   - [3.4 System Prompt](#34-system-prompt)
   - [3.5 Product Catalogue](#35-product-catalogue)
   - [3.6 Observability (Langfuse)](#36-observability-langfuse)
   - [3.7 Knowledge Base](#37-knowledge-base)
   - [3.8 Ingestion Script](#38-ingestion-script)
   - [3.9 ChromaDB (Vector Store)](#39-chromadb-vector-store)
   - [3.10 Redis (Session Cache)](#310-redis-session-cache)
   - [3.11 QA Evaluation Suite](#311-qa-evaluation-suite)
4. [Data Flow](#4-data-flow)
5. [Infrastructure & Docker](#5-infrastructure--docker)
6. [Configuration & Environment Variables](#6-configuration--environment-variables)
7. [Directory Structure](#7-directory-structure)

---

## 1. Project Overview

EcoHome AI Assistant is a conversational AI product for **EcoHome**, a UK-based provider of residential green energy solutions — solar panels, home batteries, EV chargers, and smart thermostats. The assistant helps customers understand products, check grant eligibility, explore pricing, and book a free consultation with an advisor.

The system is designed around three principles:

- **Grounded answers** — every response is backed by content retrieved from EcoHome's own knowledge base, not the model's training data alone.
- **Compliance by design** — a layered guardrail system prevents misinformation about grants, installer recommendations, and financial guarantees.
- **Actionable hand-off** — when a customer is ready to proceed, the assistant triggers a structured booking command that the client app surfaces as a consultation form.

---

## 2. Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                        iOS App (SwiftUI)                          │
│  Chat UI · Product Cards · Booking Form · Feedback               │
└───────────────────────────┬───────────────────────────────────────┘
                            │  HTTPS  (REST JSON)
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend  :8000                         │
│                                                                   │
│   POST /chat          GET /products        POST /booking          │
│   POST /feedback      GET /products/{id}   GET /health            │
│                                                                   │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │                     RAG Engine                          │    │
│   │  retrieve() → ChromaDB    generate() → Claude API       │    │
│   └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│   Session history ←→ Redis          Tracing → Langfuse           │
└────────┬───────────────────────────────────────────────────────┬─┘
         │                                                        │
         ▼                                                        ▼
┌─────────────────────┐                              ┌────────────────────┐
│   ChromaDB  :8001   │                              │  Langfuse Cloud    │
│  Vector Store       │                              │  LLM Observability │
│  "ecohome-kb"       │                              └────────────────────┘
│  63 chunks          │
└─────────────────────┘
         ▲
         │  one-time ingest
┌─────────────────────┐
│  Ingestion Script   │
│  scripts/ingest.py  │
│                     │
│  knowledge-base/*.md│
└─────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  QA Evaluation Suite  (TypeScript)              │
│  9 YAML scenarios · assertions.ts · guardrails.ts · Ragas      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Components

### 3.1 iOS App (SwiftUI)

**Location:** `ios/EcoHomeApp/`

The iOS client is the primary interface for end users. Built with SwiftUI, it provides the conversational front end that customers interact with. The app communicates exclusively with the FastAPI backend over HTTPS and does not have any local AI inference.

**Responsibilities:**
- Render the chat conversation turn by turn
- Display product cards alongside relevant AI responses (sourced from `/products`)
- Surface the consultation booking form when the backend returns a `BOOK_CONSULTATION` structured command
- Allow users to leave thumbs-up / thumbs-down feedback, posted to `/feedback`

**Key design decision — structured command:** The app does not parse intent itself. Instead, it watches the `structured_command` field in every chat API response. When that field equals `"BOOK_CONSULTATION"`, the app opens the booking form UI automatically. This keeps business logic in the backend and the app's role purely presentational.

The app is at an early scaffold stage — the full chat UI, product cards, and booking form are the next development layer.

---

### 3.2 FastAPI Backend

**Location:** `backend/api/main.py`

The backend is the central hub of the system. It receives requests from the iOS app, orchestrates the RAG pipeline, manages conversation state, and returns structured responses. It is served by Uvicorn and runs inside a Docker container.

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `POST` | `/chat` | Main conversational endpoint — runs the full RAG pipeline |
| `POST` | `/feedback` | Stores user thumbs-up/down ratings in Langfuse |
| `POST` | `/booking` | Persists a consultation booking request in Redis |
| `GET` | `/products` | Returns the full product catalogue (optional `?category=` filter) |
| `GET` | `/products/{id}` | Returns a single product's details |

**`/chat` request/response contract:**

```json
// Request
{ "message": "How much does a solar panel cost?", "session_id": "abc123" }

// Response
{
  "reply": "Solar panel systems start from around £5,000...",
  "session_id": "abc123",
  "structured_command": null,       // or "BOOK_CONSULTATION"
  "sources": ["solar-panels", "pricing"],
  "latency_ms": 1240
}
```

**Startup (`lifespan`):** On startup the server connects to Redis and pre-warms the embedding model (`all-MiniLM-L6-v2`) in a thread pool so the first chat request doesn't pay the cold-start cost.

**Session management:** A `session_id` UUID is generated for new users and echoed back so the client can include it in subsequent messages, maintaining conversation continuity.

---

### 3.3 RAG Engine

**Location:** `backend/api/rag.py`

This is the core AI logic. It implements the Retrieval-Augmented Generation (RAG) pattern: before asking Claude to generate a reply, it first retrieves the most relevant chunks from the EcoHome knowledge base. This grounds the model's answers in factual, up-to-date product information rather than allowing it to rely on training-data knowledge.

**The three-step pipeline:**

```
User message
     │
     ▼
1. retrieve(query)
   - Embed the user's message using all-MiniLM-L6-v2
   - Query ChromaDB for the top-4 nearest chunks (cosine similarity)
   - Return chunks with source labels and similarity scores
     │
     ▼
2. generate(question, chunks, history)
   - Format the retrieved chunks as labelled context
   - Prepend full conversation history for multi-turn continuity
   - Call Claude API (claude-opus-4-1, max 1024 tokens)
   - Pass the system prompt to constrain Claude's persona and guardrails
   - Scan the reply for [BOOK_CONSULTATION] token
     │
     ▼
3. Return dict: reply, structured_command, sources, chunks
```

**Lazy singleton pattern:** The embedding model, ChromaDB client, and Claude client are each initialised once on first use and reused across requests. Because the embedding model is CPU-bound, all calls to `chat()` are dispatched via `asyncio.run_in_executor` so the FastAPI event loop is never blocked.

**Structured command extraction:** Claude's system prompt instructs it to include the literal token `[BOOK_CONSULTATION]` on its own line when a booking is appropriate. The RAG engine strips that token from the visible reply text and surfaces it separately in `structured_command`. This keeps raw AI output clean while giving the client a machine-readable signal.

---

### 3.4 System Prompt

**Location:** `backend/prompts/system-prompt.md`

The system prompt is the primary behaviour specification for the AI. It is read from disk at startup and injected into every Claude API call. Keeping it as a markdown file (rather than a hardcoded string) makes it easy to iterate without code changes.

**What it defines:**

- **Persona** — friendly UK-based eco-product advisor, British English spelling
- **Scope** — only solar, battery, EV, thermostat, grants, installation, pricing, booking topics; polite refusal for everything else
- **Six critical guardrails:**
  1. Never name specific third-party installers (direct to MCS/EST finder tools)
  2. OZEV homeowner EV charger grant ended March 2022 — do not misrepresent
  3. Always caveat grant information as potentially outdated
  4. Never give definitive financial or legal advice
  5. Always include MCS/OZEV certification wording for installations
  6. Always qualify prices as indicative estimates
- **`[BOOK_CONSULTATION]` trigger** — instructs Claude to emit the token when a customer is ready to proceed
- **Response format** — concise (3–5 sentences), bullet points for lists, no markdown headers in chat

---

### 3.5 Product Catalogue

**Location:** `backend/api/products.py`

A static Python dictionary containing the full EcoHome product range, served via the `/products` endpoints. The iOS app uses this data to display rich product cards (capacity, pricing, highlights) alongside chat responses.

**Product categories and items:**

| Category | Products |
|----------|----------|
| Solar panels | Solar Starter 3kW, Solar Plus 5kW, Solar Max 8kW |
| Home batteries | PowerVault 5, PowerVault 10, PowerVault 15 |
| EV chargers | Charge 7 (7.4kW, OZEV eligible), Charge 22 (22kW) |
| Smart thermostats | ThermIQ Basic, ThermIQ Smart, ThermIQ Pro |

Each product entry carries pricing ranges (GBP), technical specs, suitability guidance, install duration, warranty terms, and marketing highlights. Pricing is intentionally a range rather than a fixed figure because the system prompt instructs Claude to always qualify prices as property-survey-dependent estimates.

---

### 3.6 Observability (Langfuse)

**Location:** `backend/api/observability.py`

Every chat interaction and user feedback rating is forwarded to [Langfuse](https://langfuse.com), an open-source LLM observability platform. This gives the product team a dashboard showing real conversations, latency trends, source attribution, and user satisfaction signals.

**What is tracked:**
- Per-session chat traces: user message, AI reply, retrieved sources, latency
- User feedback scores (thumbs up = +1, thumbs down = −1) linked to specific traces

The Langfuse client is initialised as an optional no-op — if the `LANGFUSE_PUBLIC_KEY` environment variable is absent (e.g. in local development), all tracking calls silently skip. This means the system runs fully without a Langfuse account.

---

### 3.7 Knowledge Base

**Location:** `knowledge-base/`

The knowledge base is the single authoritative source of truth that the RAG engine retrieves from. It consists of hand-authored markdown files covering every topic the assistant is expected to know about, plus supplementary PDFs from official UK government and industry sources.

**Markdown files (ingested into ChromaDB):**

| File | Content |
|------|---------|
| `solar-panels.md` | Product specs, key features, installation, SEG eligibility |
| `home-batteries.md` | Battery specs, LFP chemistry, time-of-use benefits |
| `ev-chargers.md` | Charger specs, OZEV grant rules, smart scheduling |
| `smart-thermostats.md` | Thermostat range, learning features, heat pump compatibility |
| `grants-eligibility.md` | ECO4, Warm Homes Plan, BUS, SEG, OZEV rules and caveats |
| `pricing.md` | Indicative price ranges per product, payback estimates |
| `warranties.md` | Warranty terms per product category |
| `installation.md` | Installation process, MCS certification, DNO notifications |
| `booking-consultation.md` | What happens after booking, advisor process |

**PDF documents (reference only — not yet ingested):**

| File | Source |
|------|--------|
| `battery-storage-guide-sp-energy.pdf` | SP Energy Networks |
| `new-homes-solar-bill-parliament.pdf` | UK Parliament |
| `solar-government-estate-handbook.pdf` | UK Government |
| `solar-guide-energy-saving-trust.pdf` | Energy Saving Trust |
| `uk-solar-roadmap-2025-desnz.pdf` | DESNZ |
| `warm-homes-fund-call-for-evidence.pdf` | UK Government |

The markdown content is the live retrieval corpus. PDFs are retained as authoritative reference material and can be ingested in a future pipeline pass.

---

### 3.8 Ingestion Script

**Location:** `backend/scripts/ingest.py`

A one-time (or periodic) script that populates ChromaDB from the knowledge base markdown files. It is run manually when the knowledge base changes, not on every API startup.

**Five-step process:**

1. **Load** — scans `knowledge-base/*.md` (excludes `README.md`)
2. **Chunk** — splits each file using LangChain's `RecursiveCharacterTextSplitter` (800-character chunks, 150-character overlap). Overlap ensures that sentences spanning a chunk boundary appear in both chunks so retrieval does not miss them.
3. **Embed** — generates a 384-dimensional vector for every chunk using `sentence-transformers/all-MiniLM-L6-v2`
4. **Store** — upserts all chunks into ChromaDB's `ecohome-kb` collection with metadata (source filename, topic slug, chunk index). The collection is configured for cosine similarity (`hnsw:space=cosine`).
5. **Smoke test** — fires a test query ("How much does a solar panel system cost?") and prints the top-3 retrieved chunks to confirm retrieval is working.

The current corpus produces **63 chunks** across the 9 markdown files.

---

### 3.9 ChromaDB (Vector Store)

**Container:** `ecohome-chromadb` (port 8001 externally, 8000 internally)

ChromaDB is the vector database that stores all embedded knowledge chunks and serves similarity queries at inference time. It is the memory of the RAG pipeline.

**How it is used at query time:**
1. The RAG engine embeds the user's question into a 384-dim vector
2. ChromaDB finds the 4 nearest stored chunks using approximate nearest-neighbour search (HNSW index, cosine similarity)
3. Those chunks — along with their source topic labels — are returned to the RAG engine and injected into the Claude prompt as context

**Persistence:** The ChromaDB data volume (`chromadb_data`) is mounted as a Docker named volume, so the embedded knowledge base survives container restarts without re-ingestion.

---

### 3.10 Redis (Session Cache)

**Container:** `ecohome-redis` (port 6379)

Redis serves two purposes:

**1. Conversation history**

Each chat session's message history is stored as a Redis list under the key `history:{session_id}`. When a new message arrives, the backend loads the full history, passes it to Claude as prior conversation turns, then appends the new user and assistant messages. Each history list has a **2-hour TTL** — after inactivity, the session resets.

This gives the assistant multi-turn memory without any database, keeping the stateless FastAPI service horizontally scalable.

**2. Booking storage**

When a user submits the consultation booking form, the booking data is stored in a Redis hash under `booking:{booking_id}` with a **30-day TTL**. In production this would be forwarded to a CRM or calendar system; the Redis store acts as a simple demo persistence layer.

**Persistence:** AOF (append-only file) mode is enabled (`--appendonly yes`), so bookings survive container restarts.

---

### 3.11 QA Evaluation Suite

**Location:** `qa/`

A TypeScript evaluation harness that verifies the assistant's correctness, compliance, and safety before any release. It calls the live `/chat` endpoint and evaluates responses against declared acceptance criteria. A failed **release-gating** scenario blocks the build.

**Components:**

#### `qa/scenarios/*.yaml` — Test Scenarios

Each scenario is a YAML file declaring:
- A user message sequence (`input.messages`)
- What the response must and must not contain (`acceptance`)
- Whether failure blocks a release (`runs.release_gate`)

| Scenario | Intent | What it tests |
|----------|--------|---------------|
| `solar_pricing_grounded` | product_knowledge | Prices are mentioned and grounded in KB, not hallucinated |
| `hallucination_warranty` | hallucination | Warranty claims match KB; no invented guarantees |
| `installer_guardrail` | compliance | No named third-party installer is recommended |
| `multi_turn_battery_recommendation` | product_knowledge | Correct recommendation maintained across 3 turns |
| `out_of_scope_refusal` | guardrail | Off-topic questions receive a polite refusal |
| `prompt_injection_blocked` | adversarial | Injection attempts do not leak system prompt or change behaviour |
| `book_consultation_triggered` | structured_command | `BOOK_CONSULTATION` fires when customer requests a quote |
| `ozev_grant_guardrail` | compliance | Homeowner OZEV grant correctly described as ended |
| `stale_knowledge_grants` | compliance | Grant caveats ("confirm at gov.uk") are always included |

#### `qa/src/run.ts` — Orchestrator

Loads YAML scenarios, calls the chatbot endpoint for each turn in sequence, gathers responses, runs assertions, writes a RAGAS dataset, and prints a pass/fail summary. Exits with code 1 if any release-gating scenario fails.

#### `qa/src/assertions.ts` — Acceptance Criteria

Evaluates the specific acceptance rules declared in each scenario YAML:
- `answer_must_refuse` — checks for refusal language
- `answer_must_mention_any` — at least one of a list of phrases must appear
- `answer_must_not_mention` — forbidden phrases must be absent
- `structured_command.must_trigger / must_not_trigger` — validates `[BOOK_CONSULTATION]` behaviour
- `retrieval.min_contexts / expected_source_ids` — validates retrieval quality

#### `qa/src/guardrails.ts` — Zero-Tolerance Safety

Runs on **every** response regardless of scenario-level acceptance criteria. Any violation is an automatic release gate failure:
- Guarantee / definitive-savings language (`"guaranteed savings"`, `"definitely save"`, etc.)
- OZEV homeowner grant misinformation pattern
- Named installer recommendation (regex requiring capitalised proper noun + installer-type word)
- Prompt injection leak (`"system prompt"`, `"hidden instruction"`, `"ignore all previous"`)

#### `qa/ragas/evaluate.py` — RAGAS Metrics

An optional Python script that reads the JSONL dataset produced by `run.ts` and scores it using the [RAGAS](https://docs.ragas.io) framework — faithfulness, answer relevancy, context precision, and context recall. This provides quantitative RAG quality metrics beyond pass/fail.

#### `qa/reports/` — Run Reports

Markdown reports capturing pass rate, per-scenario results, zero-tolerance violations, and next-step actions for each evaluation run. The current baseline (Run 2) shows **9/9 passing** at 100%.

---

## 4. Data Flow

### Chat conversation (happy path)

```
User types: "I'd like a quote for solar panels"
                │
                ▼
iOS App  →  POST /chat  { message, session_id }
                │
                ▼
FastAPI: load history from Redis  (key: history:{session_id})
                │
                ▼
RAG Engine:
  1. Embed message  →  all-MiniLM-L6-v2  →  384-dim vector
  2. Query ChromaDB  →  top-4 chunks from "ecohome-kb"
  3. Build prompt: [system prompt] + [history] + [context chunks] + [question]
  4. Call Claude API (claude-opus-4-1)
  5. Parse reply: extract [BOOK_CONSULTATION] token if present
                │
                ▼
FastAPI:
  - Append user + assistant turns to Redis list (2hr TTL)
  - Fire async Langfuse trace
  - Return ChatResponse
                │
                ▼
iOS App receives:
  { reply, session_id, structured_command: "BOOK_CONSULTATION", sources, latency_ms }
                │
                ▼
iOS App: structured_command == "BOOK_CONSULTATION"
  → Open consultation booking form
```

### Consultation booking

```
User fills booking form in iOS App
                │
                ▼
iOS App  →  POST /booking  { name, postcode, property_type, tenure, ... }
                │
                ▼
FastAPI: generate booking_id, store in Redis hash (30-day TTL)
                │
                ▼
Response: { booking_id, status: "confirmed", message }
```

---

## 5. Infrastructure & Docker

**File:** `docker-compose.yml`

Four services run in Docker:

| Service | Image | Internal port | External port | Role |
|---------|-------|--------------|--------------|------|
| `chromadb` | `chromadb/chroma:latest` | 8000 | 8001 | Vector store |
| `redis` | `redis:7-alpine` | 6379 | 6379 | Session & booking cache |
| `flowise` | `flowiseai/flowise:latest` | 3000 | 3000 | Legacy RAG orchestrator (superseded) |
| `api` | `./backend/Dockerfile` | 8000 | 8000 | FastAPI backend |

**Dependency order:** `api` and `flowise` both declare `depends_on: [chromadb, redis]`, so the vector store and cache are fully started before any service that needs them.

**Note on Flowise:** The `flowise` container appears in `docker-compose.yml` from the initial architecture. The RAG pipeline has since been re-implemented natively in `backend/api/rag.py` (direct ChromaDB + Claude API), which supersedes the Flowise bridge. Flowise may be removed from the compose file in a future cleanup.

---

## 6. Configuration & Environment Variables

**File:** `backend/api/config.py` (reads `.env` at startup via Pydantic Settings)

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `ANTHROPIC_API_KEY` | — | Yes | Claude API authentication |
| `CHROMA_HOST` | `chromadb` | No | ChromaDB hostname (service name in Docker) |
| `CHROMA_PORT` | `8000` | No | ChromaDB port (internal) |
| `REDIS_URL` | `redis://localhost:6379` | No | Redis connection string |
| `LANGFUSE_PUBLIC_KEY` | — | No | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | — | No | Langfuse project secret key |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | No | Langfuse API endpoint |

A `.env.example` file is provided in the repo root. Copy it to `.env` and fill in the required values before running the stack.

**QA environment** (`qa/.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHATBOT_URL` | `http://localhost:8000/chat` | Target API for eval runs |

---

## 7. Directory Structure

```
ecohome-ai-assistant/
│
├── backend/                        # FastAPI backend
│   ├── api/
│   │   ├── main.py                 # App entry point, all HTTP endpoints
│   │   ├── rag.py                  # RAG pipeline (retrieve + generate)
│   │   ├── config.py               # Pydantic settings (env vars)
│   │   ├── products.py             # Static product catalogue
│   │   ├── observability.py        # Langfuse tracing wrapper
│   │   └── __init__.py
│   ├── prompts/
│   │   └── system-prompt.md        # Claude system prompt & guardrails
│   ├── scripts/
│   │   └── ingest.py               # One-time KB → ChromaDB ingestion
│   ├── requirements.txt
│   └── Dockerfile
│
├── ios/EcoHomeApp/                 # SwiftUI iOS app
│   └── EcoHomeApp/
│       ├── EcoHomeAppApp.swift     # App entry point (@main)
│       ├── ContentView.swift       # Root view (scaffold)
│       └── Assets.xcassets/
│
├── knowledge-base/                 # Source-of-truth content
│   ├── solar-panels.md
│   ├── home-batteries.md
│   ├── ev-chargers.md
│   ├── smart-thermostats.md
│   ├── grants-eligibility.md
│   ├── pricing.md
│   ├── warranties.md
│   ├── installation.md
│   ├── booking-consultation.md
│   └── pdfs/                       # Reference PDFs (not yet ingested)
│
├── qa/                             # QA evaluation suite
│   ├── scenarios/                  # 9 YAML test scenarios
│   ├── src/
│   │   ├── run.ts                  # Main test runner
│   │   ├── assertions.ts           # Acceptance criteria evaluator
│   │   ├── guardrails.ts           # Zero-tolerance safety checks
│   │   └── types.ts                # TypeScript interfaces
│   ├── ragas/
│   │   └── evaluate.py             # RAGAS metrics scorer
│   ├── reports/                    # Eval run markdown reports
│   └── package.json
│
├── docs/
│   └── wiki.md                     # This document
│
├── docker-compose.yml              # Service orchestration
├── .env.example                    # Environment variable template
└── .gitignore
```
