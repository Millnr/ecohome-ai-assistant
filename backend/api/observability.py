"""
Langfuse observability wrapper.
Tracks chat interactions and user feedback for QA evaluation.
"""

import logging
from api.config import settings

logger = logging.getLogger(__name__)

# Initialise Langfuse client (no-op if keys not configured)
try:
    from langfuse import Langfuse
    _lf = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    ) if settings.langfuse_public_key else None
except Exception as e:
    logger.warning(f"Langfuse not initialised: {e}")
    _lf = None


async def track_chat(
    session_id: str,
    user_message: str,
    ai_reply: str,
    sources: list[str],
    latency_ms: int,
) -> None:
    if not _lf:
        return
    try:
        trace = _lf.trace(
            name="ecohome-chat",
            session_id=session_id,
            input=user_message,
            output=ai_reply,
            metadata={
                "sources": sources,
                "latency_ms": latency_ms,
                "source_count": len(sources),
            },
        )
        trace.generation(
            name="flowise-rag",
            input=user_message,
            output=ai_reply,
            model="claude-sonnet",
            usage={"latency_ms": latency_ms},
        )
    except Exception as e:
        logger.warning(f"Langfuse tracking error: {e}")


async def track_feedback(
    session_id: str,
    message_id: str,
    rating: int,
    comment: str | None,
) -> None:
    if not _lf:
        return
    try:
        _lf.score(
            trace_id=message_id,
            name="user-feedback",
            value=rating,
            comment=comment or "",
        )
    except Exception as e:
        logger.warning(f"Langfuse feedback error: {e}")
