"""LangGraph workflow assembly.

Topology:

    START
      ↓
    schema_discovery
      ↓
    sql_generator
      ↓
    sql_validator ──(invalid & budget left)──→ sql_repair ─→ sql_validator
      ↓ (valid)
    query_executor ──(error & budget left)───→ sql_repair ─→ sql_validator
      ↓ (ok)
    result_explainer
      ↓
    END

Both failure paths route through `sql_repair`, which increments `attempts`
and re-enters the validator. If `attempts` exceeds MAX_REPAIR_ATTEMPTS we
go straight to the explainer with an empty result so the user still gets a
graceful, explained failure rather than a stack trace.
"""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.query_executor import query_executor_node
from app.graph.nodes.result_explainer import result_explainer_node
from app.graph.nodes.schema_discovery import schema_discovery_node
from app.graph.nodes.sql_generator import sql_generator_node
from app.graph.nodes.sql_repair import sql_repair_node
from app.graph.nodes.sql_validator import sql_validator_node
from app.graph.state import MAX_REPAIR_ATTEMPTS, AgentState


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------
def _route_after_validator(state: AgentState) -> Literal["ok", "repair", "explain_fail"]:
    if not state.get("last_error"):
        return "ok"
    if state.get("attempts", 0) < MAX_REPAIR_ATTEMPTS:
        return "repair"
    return "explain_fail"


def _route_after_executor(state: AgentState) -> Literal["ok", "repair", "explain_fail"]:
    if not state.get("last_error"):
        return "ok"
    if state.get("attempts", 0) < MAX_REPAIR_ATTEMPTS:
        return "repair"
    return "explain_fail"


# ---------------------------------------------------------------------------
# Build the compiled graph
# ---------------------------------------------------------------------------
def build_agent_graph():
    g = StateGraph(AgentState)

    g.add_node("schema_discovery", schema_discovery_node)
    g.add_node("sql_generator", sql_generator_node)
    g.add_node("sql_validator", sql_validator_node)
    g.add_node("sql_repair", sql_repair_node)
    g.add_node("query_executor", query_executor_node)
    g.add_node("result_explainer", result_explainer_node)

    # Linear spine
    g.add_edge(START, "schema_discovery")
    g.add_edge("schema_discovery", "sql_generator")
    g.add_edge("sql_generator", "sql_validator")

    # Validator → {execute | repair | explain_fail}
    g.add_conditional_edges(
        "sql_validator",
        _route_after_validator,
        {"ok": "query_executor", "repair": "sql_repair", "explain_fail": "result_explainer"},
    )

    # Repair loops back into the validator
    g.add_edge("sql_repair", "sql_validator")

    # Executor → {end-via-explain | repair | explain_fail}
    g.add_conditional_edges(
        "query_executor",
        _route_after_executor,
        {"ok": "result_explainer", "repair": "sql_repair", "explain_fail": "result_explainer"},
    )

    g.add_edge("result_explainer", END)
    return g.compile()


# Single process-wide compiled graph (stateless in itself; memory lives in the
# checkpointer passed at invocation time, or in state.messages).
_agent_graph = None


def agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
