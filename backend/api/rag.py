"""
EcoHome RAG Engine
Handles retrieval from ChromaDB and generation via Claude API directly.
Replaces the Flowise bridge for the /chat endpoint.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import anthropic
import chromadb
from sentence_transformers import SentenceTransformer

from api.config import settings

logger = logging.getLogger(__name__)

# ── Load system prompt ────────────────────────────────────────────────────────
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system-prompt.md"
SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else ""

# ── Lazy singletons ───────────────────────────────────────────────────────────
_embed_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.HttpClient] = None
_claude_client: Optional[anthropic.Anthropic] = None


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        logger.info("Loading sentence-transformers model...")
        _embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embed_model


def _get_chroma() -> chromadb.Collection:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    return _chroma_client.get_collection("ecohome-kb")


def _get_claude() -> anthropic.Anthropic:
    global _claude_client
    if _claude_client is None:
        _claude_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _claude_client


# ── RAG pipeline ──────────────────────────────────────────────────────────────

def retrieve(query: str, n_results: int = 4) -> list[dict]:
    """Embed query and retrieve top-n chunks from ChromaDB."""
    model = _get_embed_model()
    query_embedding = model.encode([query]).tolist()
    collection = _get_chroma()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "source": meta.get("topic", meta.get("source", "unknown")),
            "score": round(1 - dist, 3),  # cosine similarity
        })
    return chunks


def generate(
    question: str,
    context_chunks: list[dict],
    conversation_history: list[dict],
) -> tuple[str, str | None]:
    """
    Call Claude with retrieved context and conversation history.
    Returns (reply_text, structured_command | None).
    """
    context_text = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in context_chunks
    )

    # Build messages: history + current question with context injected
    messages = list(conversation_history)
    messages.append({
        "role": "user",
        "content": (
            f"Context from EcoHome knowledge base:\n\n{context_text}\n\n"
            f"---\n\nUser question: {question}"
        ),
    })

    client = _get_claude()
    response = client.messages.create(
        model="claude-opus-4-1",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    reply = response.content[0].text

    # Detect structured command
    structured_command = None
    if "[BOOK_CONSULTATION]" in reply:
        structured_command = "BOOK_CONSULTATION"
        reply = reply.replace("[BOOK_CONSULTATION]", "").strip()

    return reply, structured_command


def chat(
    question: str,
    conversation_history: list[dict],
) -> dict:
    """Full RAG pipeline: retrieve → generate → return."""
    chunks = retrieve(question)
    reply, structured_command = generate(question, chunks, conversation_history)
    sources = list({c["source"] for c in chunks})
    return {
        "reply": reply,
        "structured_command": structured_command,
        "sources": sources,
        "chunks": chunks,
    }
