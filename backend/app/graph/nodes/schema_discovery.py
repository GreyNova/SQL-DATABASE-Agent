"""Node 1 — Schema Discovery.

Reads the (cached) schema DDL and attaches it to state. Cheap and synchronous,
but kept as its own node so it shows up in LangSmith traces and the UI's
thought-stream, and so it can be swapped for live introspection per-request.
"""
from __future__ import annotations

from typing import Any

from app.graph.nodes._common import make_step, timed
from app.graph.state import AgentState
from app.services.schema_service import schema_service


def schema_discovery_node(state: AgentState) -> dict[str, Any]:
    with timed() as t:
        ddl = schema_service().get_ddl()

    return {
        "schema_ddl": ddl,
        "status": "running",
        "steps": (state.get("steps") or []) + [
            make_step(
                "schema_discovery",
                "ok",
                "Loaded schema for 4 tables.",
                {"tables": ["users", "products", "orders", "order_items"]},
                t["duration_ms"],
            )
        ],
    }
