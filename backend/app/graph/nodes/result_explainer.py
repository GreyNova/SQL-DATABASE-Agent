"""Node 5 — Result Explainer.

Turns the raw rows into a 2-4 sentence plain-English answer, plus a few
suggested follow-up questions. Uses the LLM. On any LLM failure we degrade
gracefully to a templated answer so the user still gets something useful.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.nodes._common import make_step, timed
from app.graph.state import AgentState
from app.llm.factory import get_llm

_EXPLAIN_SYSTEM = (
    "You explain SQL query results to a non-technical business stakeholder.\n"
    "Rules:\n"
    "- Begin the explanation with the phrase '📊 [Insight Alert] '.\n"
    "- 2-4 sentences. Lead with the direct answer to the question.\n"
    "- Use concrete numbers from the data. Round large numbers sensibly.\n"
    "- No SQL, no column names, no technical jargon.\n"
    "- If the result is empty, say so plainly and suggest why.\n"
    "Then, on a NEW LINE beginning with 'FOLLOWUPS:', list exactly 3 short "
    "follow-up questions separated by '|'."
)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def result_explainer_node(state: AgentState) -> dict[str, Any]:
    sample = state.get("sample_size", 5)
    rows = (state.get("rows") or [])[: max(sample, 5)]
    rowcount = state.get("rowcount", 0)

    with timed() as t:
        try:
            raw = get_llm().invoke(
                [
                    SystemMessage(content=_EXPLAIN_SYSTEM),
                    HumanMessage(
                        content=(
                            f"## QUESTION\n{state['question']}\n\n"
                            f"## SQL THAT RAN\n{state['sql']}\n\n"
                            f"## RESULTS (first {len(rows)} of {rowcount} rows)\n"
                            f"{_format_rows(rows)}\n\n"
                            "Write the explanation now."
                        )
                    ),
                ]
            ).content
            answer, follow_ups = _split_followups(raw)
            step_status, message = "ok", "Explained results."
        except Exception as e:  # never let the explainer kill the whole run
            answer = _fallback_answer(state, rowcount)
            follow_ups = _fallback_followups(state["question"])
            step_status, message = "error", f"Explainer fallback: {e.__class__.__name__}"

    return {
        "answer": answer,
        "follow_ups": follow_ups,
        "status": "ok",
        "steps": (state.get("steps") or []) + [
            make_step("result_explainer", step_status, message, None, t["duration_ms"])
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _split_followups(raw: str) -> tuple[str, list[str]]:
    """Pull the FOLLOWUPS: section out of the LLM response."""
    match = re.search(r"(?is)FOLLOWUPS:\s*(.+)$", raw)
    if not match:
        return _strip_fences(raw).strip(), []
    body = _strip_fences(raw[: match.start()]).strip()
    follow = [
        q.strip().lstrip("0123456789.-) ")
        for q in match.group(1).split("|")
        if q.strip()
    ]
    return body, follow[:3]


def _strip_fences(s: str) -> str:
    return _FENCE_RE.sub("", s).strip()


def _format_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(no rows)"
    header = " | ".join(rows[0].keys())
    sep = "-+-".join("-" * len(c) for c in rows[0].keys())
    body = "\n".join(" | ".join(str(v) for v in r.values()) for r in rows)
    return f"{header}\n{sep}\n{body}"


def _fallback_answer(state: AgentState, rowcount: int) -> str:
    if rowcount == 0:
        return "I ran the query but it returned no rows. The filters may be too strict — try rephrasing without a date range or category."
    if rowcount == 1:
        return f"The query returned one matching record for “{state['question']}”. See the table below for details."
    return f"The query returned {rowcount} rows for “{state['question']}”. The table below shows the full result."


def _fallback_followups(question: str) -> list[str]:
    return [
        "Show me the same breakdown by month.",
        "What are the top contributors here?",
        "How does this compare to last period?",
    ]
