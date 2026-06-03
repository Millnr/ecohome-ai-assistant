"""
EcoHome AI Assistant — FastAPI Backend
RAG pipeline: ChromaDB retrieval + Claude API generation.
Handles: chat, session management, Langfuse observability, product data, bookings.
"""

from __future__ import annotations

import uuid
import time
import logging
import asyncio
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.config import settings
from api.products import PRODUCTS
from api.observability import track_chat
from api import rag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    # Pre-warm the embedding model in a thread (it's CPU-bound)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, rag._get_embed_model)
    logger.info("EcoHome API started — RAG engine ready")
    yield
    await app.state.redis.aclose()
    logger.info("EcoHome API shutdown")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="EcoHome AI Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    structured_command: str | None = None   # e.g. "BOOK_CONSULTATION"
    sources: list[str] = []
    latency_ms: int = 0


class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    rating: int          # 1 = thumbs up, -1 = thumbs down
    comment: str | None = None


class BookingRequest(BaseModel):
    name: str
    postcode: str
    property_type: str   # house / flat / bungalow / other
    tenure: str          # own / rent
    product_interest: str
    contact_method: str  # phone / email
    preferred_time: str  # morning / afternoon / flexible
    notes: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ecohome-api"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint. Retrieves context from ChromaDB, generates reply via
    Claude API, detects structured commands, tracks via Langfuse.
    """
    session_id = request.session_id or str(uuid.uuid4())
    start = time.monotonic()

    # ── Load conversation history from Redis ──────────────────────────────────
    history_key = f"history:{session_id}"
    raw_history = await app.state.redis.lrange(history_key, 0, -1)
    import json
    conversation_history = [json.loads(m) for m in raw_history]

    # ── RAG: retrieve + generate (CPU-bound — run in thread pool) ─────────────
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, rag.chat, request.message, conversation_history
        )
    except Exception as e:
        logger.error(f"RAG error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="AI service error")

    reply: str = result["reply"]
    structured_command: str | None = result["structured_command"]
    sources: list[str] = result["sources"]
    latency_ms = int((time.monotonic() - start) * 1000)

    # ── Persist turn to Redis conversation history ────────────────────────────
    await app.state.redis.rpush(history_key, json.dumps({"role": "user", "content": request.message}))
    await app.state.redis.rpush(history_key, json.dumps({"role": "assistant", "content": reply}))
    await app.state.redis.expire(history_key, 60 * 60 * 2)  # 2 hour TTL

    # ── Langfuse tracking ─────────────────────────────────────────────────────
    await track_chat(
        session_id=session_id,
        user_message=request.message,
        ai_reply=reply,
        sources=sources,
        latency_ms=latency_ms,
    )

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        structured_command=structured_command,
        sources=sources,
        latency_ms=latency_ms,
    )


@app.post("/feedback")
async def feedback(request: FeedbackRequest):
    """Stores thumbs up/down feedback — forwarded to Langfuse."""
    from api.observability import track_feedback
    await track_feedback(
        session_id=request.session_id,
        message_id=request.message_id,
        rating=request.rating,
        comment=request.comment,
    )
    return {"status": "ok"}


@app.post("/booking")
async def booking(request: BookingRequest):
    """
    Handles the [BOOK_CONSULTATION] form submission from the iOS app.
    In demo mode: stores in Redis and returns confirmation.
    In production: would POST to a CRM or calendar system.
    """
    booking_id = str(uuid.uuid4())[:8].upper()
    booking_data = request.model_dump()
    booking_data["booking_id"] = booking_id
    booking_data["status"] = "pending"

    await app.state.redis.hset(f"booking:{booking_id}", mapping=booking_data)
    await app.state.redis.expire(f"booking:{booking_id}", 60 * 60 * 24 * 30)  # 30 days

    logger.info(f"Booking created: {booking_id} for {request.name} ({request.postcode})")

    return {
        "booking_id": booking_id,
        "status": "confirmed",
        "message": f"Thanks {request.name}, your consultation request has been received. "
                   f"We'll be in touch within 2 business hours. Your reference is {booking_id}.",
    }


@app.get("/products")
async def products(category: str | None = None):
    """
    Returns EcoHome product catalogue.
    iOS app uses this to display product cards alongside chat responses.
    """
    if category:
        filtered = {k: v for k, v in PRODUCTS.items() if v.get("category") == category}
        return {"products": filtered}
    return {"products": PRODUCTS}


@app.get("/products/{product_id}")
async def product_detail(product_id: str):
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    return PRODUCTS[product_id]
