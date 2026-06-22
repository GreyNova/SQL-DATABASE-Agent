"""Chat routes: POST /chat (JSON) and POST /chat/stream (SSE)."""
from __future__ import annotations

import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.agent_service import run_agent, stream_agent

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, responses={400: {"model": ErrorResponse}})
async def chat(req: ChatRequest) -> ChatResponse:
    """Run the full agent synchronously and return the complete result."""
    try:
        return run_agent(req.question, req.thread_id, req.sample_size)
    except Exception as e:  # surfaced as a clean 400 with context
        from app.core.config import settings

        detail = str(e) if settings.app_debug else e.__class__.__name__
        return _error_response(detail, "agent")  # type: ignore[return-value]


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> EventSourceResponse:
    """Stream per-node steps then a final `done` payload as SSE."""
    import asyncio

    async def event_gen():
        try:
            async for sse in stream_agent(req.question, req.thread_id, req.sample_size):
                # `sse` is a pre-formatted "event: ...\ndata: {...}\n\n" string;
                # split it back into sse_starlette's (event, data) shape.
                event, data = _parse_sse(sse)
                yield {"event": event, "data": data}
        except Exception as e:
            from app.core.config import settings

            detail = str(e) if settings.app_debug else e.__class__.__name__
            yield {
                "event": "error",
                "data": json.dumps(ErrorResponse(error="stream_failed", detail=detail).model_dump()),
            }
        # small yield so the SSE connection flushes cleanly
        await asyncio.sleep(0)

    return EventSourceResponse(event_gen())


def _parse_sse(raw: str) -> tuple[str, str]:
    event, data = "message", ""
    for line in raw.strip().splitlines():
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
    return event, data


def _error_response(detail: str, step: str) -> ChatResponse:
    """Return a ChatResponse-shaped error so the frontend can render it uniformly."""
    return ChatResponse(  # type: ignore[arg-type]
        answer=f"Something went wrong: {detail}",
        sql=None,
        execution=None,
        chart=None,
        steps=[],
        follow_ups=[],
        thread_id="",
    )
