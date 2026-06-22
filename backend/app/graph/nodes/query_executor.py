"""Node 4 — Query Executor.

Runs the validated SQL against the READ-ONLY engine. On a DB error it records
the message so the conditional edge can route to repair.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

from app.core.db import readonly_session
from app.graph.nodes._common import make_step, timed
from app.graph.state import AgentState


def query_executor_node(state: AgentState) -> dict[str, Any]:
    sql = state["sql"]
    with timed() as t:
        try:
            with readonly_session() as s:
                result = s.execute(text(sql))
                columns = [{"name": str(c), "type": "auto"} for c in result.keys()]
                rows = [dict(r._mapping) for r in result.fetchall()]
            rowcount = len(rows)
            status, error, step_status = "ok", "", "ok"
            message = f"Returned {rowcount} row(s)."
        except (OperationalError, ProgrammingError) as e:
            rows, columns, rowcount = [], [], 0
            status, error, step_status = "running", _db_error(e), "error"
            message = f"Execution failed: {error}"
        except SQLAlchemyError as e:
            rows, columns, rowcount = [], [], 0
            status, error, step_status = "error", e.__class__.__name__, "error"
            message = f"Execution failed: {e.__class__.__name__}"

    return {
        "rows": _sanitize_rows(rows),
        "columns": columns,
        "rowcount": rowcount,
        "last_error": error,
        "status": status,
        "steps": (state.get("steps") or []) + [
            make_step("query_executor", step_status, message, None, t["duration_ms"])
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _db_error(exc: SQLAlchemyError) -> str:
    """Pull the human-friendly Postgres message out of a SQLAlchemy error."""
    orig = getattr(exc, "orig", None)
    return str(orig) if orig else str(exc)


def _sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Make every value JSON-serializable (Decimal, datetime, ...)."""
    out: list[dict[str, Any]] = []
    for row in rows:
        clean: dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                clean[k] = float(v)
            elif isinstance(v, (datetime.datetime, datetime.date)):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        out.append(clean)
    return out
