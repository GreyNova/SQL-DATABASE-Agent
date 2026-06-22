"""Node 2b — SQL Repair (re-generation on failure).

Invoked by the graph's conditional edge when validation or execution fails and
we still have repair budget. Feeds the failing SQL + error back to the LLM.
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.nodes._common import make_step, timed
from app.graph.nodes.sql_generator import parse_llm_sql
from app.graph.state import AgentState
from app.llm.factory import get_llm
from app.prompts.templates import SYSTEM_PERSONA

_FIX_INSTRUCTIONS = (
    "A previously generated query FAILED. Fix it and return ONLY JSON:\n"
    '{"sql": "<corrected SELECT>", "rationale": "<what was wrong>"}'
)


def sql_repair_node(state: AgentState) -> dict[str, Any]:
    with timed() as t:
        prompt = [
            SystemMessage(content=f"{SYSTEM_PERSONA}\n{_FIX_INSTRUCTIONS}"),
            HumanMessage(
                content=(
                    f"## SCHEMA\n{state['schema_ddl']}\n\n"
                    f"## QUESTION\n{state['question']}\n\n"
                    f"## FAILED SQL\n{state.get('sql','')}\n\n"
                    f"## ERROR\n{state.get('last_error','')}\n\n"
                    "Return the corrected JSON object only."
                )
            ),
        ]
        raw = get_llm().invoke(prompt).content
        parsed = parse_llm_sql(raw)
        sql = str(parsed.get("sql", "")).strip().rstrip(";")

    return {
        "sql": sql,
        "attempts": state.get("attempts", 0) + 1,
        "last_error": "",  # reset; the next validator/executor run will repopulate
        "steps": (state.get("steps") or []) + [
            make_step(
                "sql_repair",
                "ok",
                f"Repair attempt {state.get('attempts', 0) + 1}.",
                {"rationale": parsed.get("rationale")},
                t["duration_ms"],
            )
        ],
    }
