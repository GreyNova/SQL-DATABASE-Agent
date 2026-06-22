"""Pydantic schemas for every API request & response."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Chat / Agent
# ============================================================================
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Natural-language question")
    thread_id: str | None = Field(default=None, description="Conversation thread id (memory)")
    sample_size: int = Field(default=5, ge=0, le=20, description="Rows to send to the explainer")


class ColumnMeta(BaseModel):
    name: str
    type: str


class QueryExecution(BaseModel):
    sql: str
    rowcount: int
    columns: list[ColumnMeta]
    rows: list[dict[str, Any]]


class ChatStep(BaseModel):
    """One node's output in the graph — surfaced to the UI as a 'thought stream'."""
    node: str
    status: Literal["ok", "error", "skipped"]
    message: str | None = None
    payload: dict[str, Any] | None = None
    duration_ms: float | None = None


class ChartSpec(BaseModel):
    """A suggested chart derived from the result shape. The frontend renders it."""
    type: Literal["table", "bar", "line", "pie", "kpi"]
    title: str
    x_field: str | None = None
    y_field: str | None = None
    label_field: str | None = None
    value_field: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    execution: QueryExecution | None = None
    chart: ChartSpec | None = None
    steps: list[ChatStep] = []
    follow_ups: list[str] = []
    thread_id: str


# ============================================================================
# History
# ============================================================================
class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    thread_id: str
    question: str
    answer: str
    sql: str | None = None
    rowcount: int | None = None
    created_at: datetime


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int


# ============================================================================
# Schema introspection (read-only metadata endpoint)
# ============================================================================
class SchemaResponse(BaseModel):
    tables: dict[str, list[ColumnMeta]]


# ============================================================================
# Errors
# ============================================================================
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    step: str | None = None
