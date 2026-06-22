"""Node 2 — SQL Generator.

Calls the LLM to turn the question + schema into a single SELECT statement.
The model is asked for strict JSON so we can extract the SQL deterministically;
we strip markdown fences defensively in case it adds them anyway.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.nodes._common import make_step, timed
from app.graph.state import AgentState
from app.llm.factory import get_llm
from app.prompts.templates import SYSTEM_PERSONA

# Shared between generate & repair.
_GEN_INSTRUCTIONS = (
    "You will be given the database schema and the user's question. "
    "Respond with ONLY a JSON object, no markdown fences, no commentary:\n"
    '{"sql": "<a single SELECT statement>", '
    '"rationale": "<one sentence on your approach>", '
    '"assumptions": ["<any assumptions made>"]}'
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(s: str) -> str:
    return _FENCE_RE.sub("", s).strip()


def parse_llm_sql(raw: str) -> dict[str, Any]:
    """Best-effort parse of the model's JSON response."""
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back: grab the first SQL-looking statement between SELECT and ;/EOF
        m = re.search(r"(?is)(SELECT|WITH)\b.*?(?:;|$)", cleaned)
        if m:
            return {"sql": m.group(0).strip(), "rationale": "", "assumptions": []}
        raise


def _conversation_context(state: AgentState) -> str:
    """Render the last couple of turns so the LLM can resolve follow-ups
    like 'what about last quarter?'."""
    msgs = state.get("messages") or []
    if not msgs:
        return "(none)"
    lines: list[str] = []
    for m in msgs[-6:]:  # last 6 messages only
        role = getattr(m, "type", str(m))
        content = getattr(m, "content", str(m))
        lines.append(f"{role}: {content[:300]}")
    return "\n".join(lines)


def sql_generator_node(state: AgentState) -> dict[str, Any]:
    with timed() as t:
        prompt = [
            SystemMessage(content=f"{SYSTEM_PERSONA}\n{_GEN_INSTRUCTIONS}"),
            HumanMessage(
                content=(
                    f"## DATABASE SCHEMA\n{state['schema_ddl']}\n\n"
                    f"## RECENT CONVERSATION\n{_conversation_context(state)}\n\n"
                    f"## QUESTION\n{state['question']}\n\n"
                    "Respond with the JSON object only."
                )
            ),
        ]
        raw = get_llm().invoke(prompt).content
        parsed = parse_llm_sql(raw)
        sql = str(parsed.get("sql", "")).strip().rstrip(";")

    return {
        "sql": sql,
        "sql_rationale": str(parsed.get("rationale", "")),
        "last_error": "",
        "steps": (state.get("steps") or []) + [
            make_step(
                "sql_generator",
                "ok",
                f"Generated SQL ({t['duration_ms']}ms).",
                {"rationale": parsed.get("rationale"), "assumptions": parsed.get("assumptions")},
                t["duration_ms"],
            )
        ],
    }
