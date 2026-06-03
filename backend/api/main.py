"""
EcoHome AI Assistant — FastAPI Backend
Bridges the iOS app ↔ Flowise RAG pipeline.
Handles: chat routing, session management, Langfuse observability, product data.
"""

import uuid
import time
import logging
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.config import settings
from api.products import PRODUCTS
from api.observability import track_chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    app.state.http = httpx.AsyncClient(timeout=60.0)
    logger.info("EcoHome API started")
    yield
    await app.state.redis.aclose()
    await app.state.http.aclose()
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
    Main chat endpoint. Routes message to Flowise and returns the AI reply.
    Detects structured commands in the response (e.g. [BOOK_CONSULTATION]).
    """
    session_id = request.session_id or str(uuid.uuid4())
    start = time.monotonic()

    # ── Call Flowise ─────────────────────────────────────────────────────────
    try:
        flowise_response = await app.state.http.post(
            f"{settings.flowise_url}/api/v1/prediction/{settings.flowise_chatflow_id}",
            headers={"Authorization": f"Bearer {settings.flowise_api_key}"},
            json={
                "question": request.message,
                "sessionId": session_id,
                "overrideConfig": {},
            },
        )
        flowise_response.raise_for_status()
        data = flowise_response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Flowise error: {e}")
        raise HTTPException(status_code=502, detail="AI service unavailable")

    reply: str = data.get("text", "")
    sources: list[str] = [
        doc.get("metadata", {}).get("source", "")
        for doc in data.get("sourceDocuments", [])
        if doc.get("metadata", {}).get("source")
    ]

    # ── Detect structured command ─────────────────────────────────────────────
    structured_command = None
    if "[BOOK_CONSULTATION]" in reply:
        structured_command = "BOOK_CONSULTATION"
        reply = reply.replace("[BOOK_CONSULTATION]", "").strip()

    latency_ms = int((time.monotonic() - start) * 1000)

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
