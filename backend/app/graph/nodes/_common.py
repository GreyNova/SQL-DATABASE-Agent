"""Shared helpers used by every graph node."""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator


def make_step(node: str, status: str, message: str | None = None,
              payload: dict[str, Any] | None = None, duration_ms: float | None = None) -> dict[str, Any]:
    return {
        "node": node,
        "status": status,
        "message": message,
        "payload": payload,
        "duration_ms": duration_ms,
    }


@contextmanager
def timed() -> Iterator[dict[str, float]]:
    """Yield a dict that gets `duration_ms` filled in on exit."""
    out = {"duration_ms": 0.0}
    start = time.perf_counter()
    try:
        yield out
    finally:
        out["duration_ms"] = round((time.perf_counter() - start) * 1000.0, 1)
