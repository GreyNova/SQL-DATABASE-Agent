"""Agent service — the thin layer the API calls.

Responsibilities:
  * Load recent conversation memory for a thread.
  * Invoke the compiled LangGraph.
  * Map the final state to a `ChatResponse` (incl. chart inference).
  * Persist the turn to history.
  * Provide a streaming variant that emits per-node `ChatStep` deltas.
"""
from __future__ import annotations

import json
from collections import deque
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.builder import agent_graph
from app.models.schemas import (
    ChartSpec,
    ChatResponse,
    ChatStep,
    ColumnMeta,
    QueryExecution,
)
from app.services.chart_inference import infer_chart
from app.services.history_store import history_store, new_thread_id

# In-process conversation memory: thread_id -> deque of recent messages.
# Production: swap for the LangGraph PostgresSaver checkpointer.
_MAX_TURNS = 12
_memory: dict[str, deque[Any]] = {}


def _load_memory(thread_id: str) -> list[Any]:
    return list(_memory.get(thread_id, []))


def _push_memory(thread_id: str, human: str, ai: str) -> None:
    dq = _memory.setdefault(thread_id, deque(maxlen=_MAX_TURNS))
    dq.append(HumanMessage(content=human))
    dq.append(AIMessage(content=ai))


def _initial_state(question: str, thread_id: str, sample_size: int) -> dict[str, Any]:
    return {
        "question": question,
        "thread_id": thread_id,
        "sample_size": sample_size,
        "messages": _load_memory(thread_id),
        "attempts": 0,
        "steps": [],
        "status": "running",
    }


def run_agent(question: str, thread_id: str | None, sample_size: int = 5) -> ChatResponse:
    """Synchronous end-to-end run."""
    thread_id = thread_id or new_thread_id()
    graph = agent_graph()
    final_state: dict[str, Any] = graph.invoke(_initial_state(question, thread_id, sample_size))

    response = _to_response(final_state, question, thread_id, sample_size)

    # memory + history
    _push_memory(thread_id, question, response.answer)
    history_store().add(
        thread_id=thread_id,
        question=question,
        answer=response.answer,
        sql=response.sql,
        rowcount=response.execution.rowcount if response.execution else None,
    )
    return response


async def stream_agent(
    question: str, thread_id: str | None, sample_size: int = 5
) -> AsyncIterator[str]:
    """Stream SSE events: one `step` event per node, then a final `done` event.

    The frontend renders the per-node steps as a 'thought stream' and swaps in
    the full payload on `done`.
    """
    thread_id = thread_id or new_thread_id()
    graph = agent_graph()

    seen_steps = 0
    last_state: dict[str, Any] = {}

    for chunk in graph.stream(
        _initial_state(question, thread_id, sample_size),
        stream_mode="updates",
    ):
        # chunk is {node_name: state_delta}
        for node_name, delta in chunk.items():
            steps = (delta or {}).get("steps") or []
            # Emit any newly appended steps.
            for step in steps[seen_steps:]:
                seen_steps += 1
                yield _sse("step", ChatStep(**step).model_dump())
            last_state.update(delta or {})

    # Merge last_state into a full state snapshot for response building.
    full = _initial_state(question, thread_id, sample_size)
    full.update(last_state)
    response = _to_response(full, question, thread_id, sample_size)

    _push_memory(thread_id, question, response.answer)
    history_store().add(
        thread_id=thread_id,
        question=question,
        answer=response.answer,
        sql=response.sql,
        rowcount=response.execution.rowcount if response.execution else None,
    )

    yield _sse("done", response.model_dump())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_response(
    state: dict[str, Any], question: str, thread_id: str, sample_size: int
) -> ChatResponse:
    rows = state.get("rows") or []
    columns = state.get("columns") or []
    sql = state.get("sql")
    rowcount = state.get("rowcount", 0)

    execution: QueryExecution | None = None
    if sql and (rows or columns):
        execution = QueryExecution(
            sql=sql,
            rowcount=rowcount,
            columns=[ColumnMeta(**c) for c in columns],
            rows=rows,
        )

    chart: ChartSpec | None = None
    if rows:
        chart = infer_chart(rows, question)

    steps = [ChatStep(**s) for s in (state.get("steps") or [])]

    answer = state.get("answer") or _failed_answer(state)

    return ChatResponse(
        answer=answer,
        sql=sql,
        execution=execution,
        chart=chart,
        steps=steps,
        follow_ups=state.get("follow_ups") or [],
        thread_id=thread_id,
    )


def _failed_answer(state: dict[str, Any]) -> str:
    err = state.get("last_error") or "unknown error"
    return (
        "I couldn't produce a valid query for that question after a few attempts. "
        f"Last problem: {err}. Could you rephrase or add more detail?"
    )


def _sse(event: str, data: Any) -> str:
    payload = data.model_dump() if hasattr(data, "model_dump") else data
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
