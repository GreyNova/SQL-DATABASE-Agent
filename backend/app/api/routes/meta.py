"""History & schema metadata routes."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import ColumnMeta, HistoryItem, HistoryListResponse, SchemaResponse
from app.services.history_store import history_store
from app.services.schema_service import schema_service

router = APIRouter(tags=["meta"])


@router.get("/history", response_model=HistoryListResponse)
async def list_history(limit: int = Query(default=50, ge=1, le=200)) -> HistoryListResponse:
    items = history_store().list(limit=limit)
    return HistoryListResponse(items=[HistoryItem(**i.model_dump()) for i in items], total=len(items))


@router.get("/history/{thread_id}", response_model=HistoryListResponse)
async def thread_history(thread_id: str) -> HistoryListResponse:
    items = history_store().by_thread(thread_id)
    return HistoryListResponse(items=[HistoryItem(**i.model_dump()) for i in items], total=len(items))


@router.get("/schema", response_model=SchemaResponse)
async def get_schema() -> SchemaResponse:
    live = schema_service().get_live_schema()
    tables = {
        t: [ColumnMeta(name=c["column"], type=c["type"]) for c in cols]
        for t, cols in live.items()
    }
    return SchemaResponse(tables=tables)
