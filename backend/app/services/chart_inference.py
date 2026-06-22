"""Infer a sensible chart from a result set's shape.

Kept deliberately heuristic and dependency-free so the frontend gets a hint
without us shipping a heavyweight visualization library on the backend.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.models.schemas import ChartSpec

_NUMERIC = (int, float, Decimal)
_TEMPORAL_NAMES = {"month", "year", "date", "order_date", "week", "quarter"}


def infer_chart(rows: list[dict[str, Any]], question: str) -> ChartSpec:
    """Pick the best chart for the given rows; default to a table."""
    if not rows:
        return ChartSpec(type="table", title="No data")

    cols = list(rows[0].keys())
    q = (question or "").lower()

    # Single-row, single-value => KPI.
    if len(rows) == 1 and len(cols) == 1:
        return ChartSpec(
            type="kpi",
            title=_title_from_question(q),
            value_field=cols[0],
        )

    # Two columns: a category/time + a measure.
    if len(cols) >= 2:
        label_col, value_col = _find_label_value(cols, rows)
        if _looks_temporal(label_col):
            return ChartSpec(
                type="line",
                title=_title_from_question(q),
                x_field=label_col,
                y_field=value_col,
            )
        # Pie when there are few categories AND the question implies a share.
        if len(rows) <= 6 and _wants_share(q):
            return ChartSpec(
                type="pie",
                title=_title_from_question(q),
                label_field=label_col,
                value_field=value_col,
            )
        return ChartSpec(
            type="bar",
            title=_title_from_question(q),
            x_field=label_col,
            y_field=value_col,
        )

    return ChartSpec(type="table", title=_title_from_question(q))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _find_label_value(cols: list[str], rows: list[dict[str, Any]]) -> tuple[str, str]:
    """First non-numeric column is the label, first numeric column is the value."""
    label = cols[0]
    value = cols[-1]
    for c in cols:
        if any(isinstance(r.get(c), _NUMERIC) for r in rows):
            value = c
            break
    for c in cols:
        if c != value and not any(isinstance(r.get(c), _NUMERIC) for r in rows):
            label = c
            break
    return label, value


def _looks_temporal(col: str) -> bool:
    return any(t in col.lower() for t in _TEMPORAL_NAMES)


def _wants_share(q: str) -> bool:
    return any(w in q for w in ("distribution", "share", "breakdown", "split", "by category"))


def _title_from_question(q: str) -> str:
    q = q.strip().rstrip("?")
    return q[:80] + ("…" if len(q) > 80 else "")
