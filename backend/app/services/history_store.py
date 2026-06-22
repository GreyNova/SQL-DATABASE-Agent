"""Query history store.

For this reference build we persist history in-process (thread-safe deque).
Swap `_HistoryStore` for a Postgres/Redis-backed implementation in production —
the interface (`add`, `list`, `by_thread`) is intentionally stable.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from datetime import datetime, timezone

from app.models.schemas import HistoryItem


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HistoryStore:
    def __init__(self, capacity: int = 1000) -> None:
        self._lock = threading.Lock()
        self._items: deque[HistoryItem] = deque(maxlen=capacity)

    def add(
        self,
        *,
        thread_id: str,
        question: str,
        answer: str,
        sql: str | None,
        rowcount: int | None,
    ) -> HistoryItem:
        item = HistoryItem(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            question=question,
            answer=answer,
            sql=sql,
            rowcount=rowcount,
            created_at=_utcnow(),
        )
        with self._lock:
            self._items.append(item)
        return item

    def list(self, limit: int = 50) -> list[HistoryItem]:
        with self._lock:
            return list(self._items)[::-1][:limit]

    def by_thread(self, thread_id: str, limit: int = 20) -> list[HistoryItem]:
        with self._lock:
            return [i for i in self._items if i.thread_id == thread_id][-limit:]


_store: HistoryStore | None = None


def history_store() -> HistoryStore:
    global _store
    if _store is None:
        _store = HistoryStore()
    return _store


def new_thread_id() -> str:
    return str(uuid.uuid4())
