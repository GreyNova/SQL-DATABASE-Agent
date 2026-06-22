"""Node 3 — SQL Validator.

Runs the static guardrails from `app.core.security`. If validation fails we
record the error; the graph's conditional edge will route back to the generator
(with the error in context) up to MAX_REPAIR_ATTEMPTS times, otherwise to a
terminal error state.
"""
from __future__ import annotations

from typing import Any

from app.core.security import SQLSafetyError, validate_sql
from app.graph.nodes._common import make_step, timed
from app.graph.state import AgentState


def sql_validator_node(state: AgentState) -> dict[str, Any]:
    sql = state.get("sql") or ""
    with timed() as t:
        try:
            cleaned = validate_sql(sql)
            status, error, step_status = "ok", "", "ok"
            message = "Passed static guardrails."
        except SQLSafetyError as e:
            cleaned = sql
            status, error, step_status = "running", str(e), "error"
            message = f"Rejected by guardrails: {e}"

    return {
        "sql": cleaned,
        "last_error": error,
        "status": status,
        "steps": (state.get("steps") or []) + [
            make_step("sql_validator", step_status, message, None, t["duration_ms"])
        ],
    }
