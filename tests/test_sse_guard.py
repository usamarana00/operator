import json

import pytest

from utils.sse import guard_stream


async def _boom():
    yield "data: first\n\n"
    raise RuntimeError("openai down")


@pytest.mark.asyncio
async def test_guard_stream_emits_error_event_instead_of_dying_silently():
    chunks = [c async for c in guard_stream(_boom(), "Chat")]

    assert chunks[0] == "data: first\n\n"
    event = json.loads(chunks[1].removeprefix("data: "))
    assert event["agent"] == "system"
    assert event["type"] == "error"
    assert "RuntimeError" in event["content"]
    assert "openai down" not in event["content"]  # no raw exception text to the client
