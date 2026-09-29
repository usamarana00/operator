import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from fpdf import FPDF

from agents.producer_agent import ProducerAgent
from auth import get_github_token, get_user_id
from utils.sse import guard_stream
from db import postgres as db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["proposal"])


def _sanitize_latin1(content: str) -> str:
    # Sanitize content to Latin-1 by transliterating smart punctuation
    # and replacing any remaining unencodable characters with '?'
    sanitized = content

    # Transliterate common smart punctuation to ASCII equivalents.
    # Keys use explicit \uXXXX escapes (not literal characters) so the
    # mapping can't be silently corrupted by quote-nesting/parsing accidents.
    smart_quote_map = {
        "\u201c": '"',    # Left double quotation mark
        "\u201d": '"',    # Right double quotation mark
        "\u2018": "'",    # Left single quotation mark
        "\u2019": "'",    # Right single quotation mark
        "\u2014": "-",    # Em dash
        "\u2013": "-",    # En dash
        "\u2026": "...",  # Ellipsis
        "\u2022": "-",    # Bullet
    }

    for smart_char, ascii_char in smart_quote_map.items():
        sanitized = sanitized.replace(smart_char, ascii_char)

    # Backstop: replace any remaining unencodable characters with '?'
    sanitized = sanitized.encode('latin-1', 'replace').decode('latin-1')

    return sanitized


def _render_pdf(content: str) -> bytes:
    sanitized = _sanitize_latin1(content)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 8, sanitized)
    return bytes(pdf.output())


class ProposalRequest(BaseModel):
    client: str
    description: str
    budget: str = ""
    session_id: str = ""


def _parse_sse_content(chunk: str) -> tuple[str, str] | None:
    import json

    if not chunk.startswith("data: "):
        return None
    try:
        event = json.loads(chunk.removeprefix("data: ").strip())
    except json.JSONDecodeError:
        return None
    return str(event.get("type", "")), str(event.get("content", ""))


async def _proposal_stream(
    *,
    user_id: str,
    github_token: str,
    body: ProposalRequest,
) -> AsyncIterator[str]:
    final_content = ""
    agent = ProducerAgent(user_id=user_id, github_token=github_token)

    async for chunk in agent.proposal(
        description=body.description,
        client=body.client,
        budget=body.budget,
    ):
        parsed = _parse_sse_content(chunk)
        if parsed and parsed[0] == "final":
            final_content = parsed[1]
        yield chunk

    if final_content and body.session_id:
        await db.append_message(user_id, body.session_id, "assistant", final_content)


@router.post("/proposal")
async def proposal(body: ProposalRequest, request: Request):
    user_id = get_user_id(request)
    github_token = get_github_token(request)
    if not body.client.strip() or not body.description.strip():
        raise HTTPException(status_code=422, detail="Client and description are required")

    logger.info("proposal requested: user=%s client=%s", user_id, body.client)
    return StreamingResponse(
        guard_stream(_proposal_stream(user_id=user_id, github_token=github_token, body=body), "Proposal"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/proposal/{session_id}/pdf")
async def proposal_pdf(session_id: str, request: Request):
    user_id = get_user_id(request)

    messages = await db.get_messages(user_id, session_id, limit=20)
    content = next(
        (
            message["content"]
            for message in reversed(messages)
            if message.get("role") == "assistant"
        ),
        "",
    )
    if not content:
        raise HTTPException(status_code=404, detail="Proposal not found")

    try:
        pdf = _render_pdf(content)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="proposal-{session_id[:8]}.pdf"'},
        )
    except Exception as exc:
        logger.warning("proposal pdf fallback for session=%s: %s", session_id, exc)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="proposal-{session_id[:8]}.md"'},
        )
