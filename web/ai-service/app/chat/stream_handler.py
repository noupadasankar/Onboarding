"""SSE stream handler — converts an async token iterator into SSE text."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


async def token_stream_to_sse(
    token_iter: AsyncIterator[str],
    conversation_id: str,
) -> AsyncIterator[str]:
    """Wrap raw token chunks as SSE events.

    Yields:
        ``event: token\\ndata: <json>\\n\\n`` for each chunk.
        ``event: done\\ndata: <json>\\n\\n`` when the iterator is exhausted.
    """
    full_text: list[str] = []
    async for token in token_iter:
        full_text.append(token)
        yield _sse("token", json.dumps({"token": token}))

    yield _sse(
        "done",
        json.dumps({"conversation_id": conversation_id, "answer": "".join(full_text)}),
    )
