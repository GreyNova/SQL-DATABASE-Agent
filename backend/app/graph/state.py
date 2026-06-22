"""LangGraph state — the single object that flows through every node.

We use a TypedDict so LangGraph can merge partial updates from each node
(only the keys a node returns are overwritten).
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import MessagesState  # built-in message-list state


class AgentState(TypedDict, total=False):
    # ---- inputs ----
    question: str
    thread_id: str
    sample_size: int

    # ---- conversation memory (last few turns) ----
    messages: list[Any]  # MessagesState-compatible

    # ---- schema discovery ----
    schema_ddl: str

    # ---- sql generation / correction ----
    sql: str
    sql_rationale: str
    attempts: int                       # self-correction counter
    last_error: str                     # populated when a node fails

    # ---- execution ----
    columns: list[dict[str, str]]
    rows: list[dict[str, Any]]
    rowcount: int

    # ---- explanation ----
    answer: str
    follow_ups: list[str]

    # ---- orchestration signals ----
    status: str                         # running | ok | error
    steps: list[dict[str, Any]]         # per-node trace for the UI thought-stream


# How many times the graph will try to self-correct a failing query.
MAX_REPAIR_ATTEMPTS: int = 2
