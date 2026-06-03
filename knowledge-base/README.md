# EcoHome AI Assistant — Knowledge Base

This directory contains the source knowledge base for the EcoHome AI Assistant RAG pipeline. All documents are hand-authored markdown files structured for embedding into ChromaDB via Flowise.

## Files

| File | Topic | QA Dimensions Covered |
|---|---|---|
| `solar-panels.md` | Solar panel products, FAQs, compliance | RAG accuracy, safety wording, SEG/MCS |
| `home-batteries.md` | Battery storage products, FAQs | Product recommendation, safety wording |
| `ev-chargers.md` | EV charger products, OZEV grants | Guardrail (grant misconception), eligibility |
| `smart-thermostats.md` | Thermostat products, compatibility | Product recommendation, compatibility edge cases |
| `warranties.md` | Product, performance & workmanship warranties | Hallucination control, stale knowledge |
| `installation.md` | Install process, G98/G99, scaffolding | Structured process, compliance wording |
| `grants-eligibility.md` | ECO4, Warm Homes, BUS, SEG, VAT, Scotland/Wales | Eligibility edge cases, stale knowledge |
| `pricing.md` | Indicative pricing, payback periods | Hallucination control, disclaimer handling |
| `booking-consultation.md` | Booking flow, `[BOOK_CONSULTATION]` command | Form journey, structured commands, guardrails |

## Design Principles

1. **Guardrails are embedded in the KB** — safety notes (e.g. "never name a specific installer", "do not tell customers the homeowner OZEV grant is still available") are written directly into the relevant document so the LLM retrieves them alongside factual content.

2. **Stale knowledge is flagged** — documents contain explicit "as at 2025" date markers and prompts to verify current grant terms. This deliberately surfaces the stale/missing knowledge QA test dimension.

3. **Structured commands are documented** — `[BOOK_CONSULTATION]` is defined in `booking-consultation.md` so the LLM knows when and how to trigger it.

4. **Source attribution** — every file lists its public source URLs (GOV.UK, Energy Saving Trust, MCS, etc.) supporting the portfolio narrative around content governance and human-in-the-loop validation.

## Flowise Ingestion

- Loader: Markdown file loader or PDF loader (for any PDFs sourced separately)
- Chunk size: 500–1000 tokens
- Chunk overlap: 100–200 tokens
- Metadata tag each chunk with `topic:` for filtered retrieval
- Re-ingest when grant/policy pages update (grants-eligibility.md is most volatile)

## Attribution

> All knowledge base content is based on publicly available UK government, charity, and industry body information. Sources include GOV.UK, Energy Saving Trust, MCS, SP Energy Networks, and Parliament.uk. This project is a fictional demonstration and does not represent any real company or service.
