import json
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)


async def guard_stream(stream: AsyncIterator[str], label: str) -> AsyncIterator[str]:
    """Pass SSE chunks through; if the stream raises, log it and emit a visible error event
    instead of silently closing the connection mid-response."""
    try:
        async for chunk in stream:
            yield chunk
    except Exception as exc:
        logger.exception("%s stream failed", label)
        payload = {
            "agent": "system",
            "type": "error",
            "content": f"{label} failed ({type(exc).__name__}). Check the backend logs.",
        }
        yield f"data: {json.dumps(payload)}\n\n"
