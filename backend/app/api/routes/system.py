"""System routes: health & readiness."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.db import readonly_session

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — process is up."""
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}


@router.get("/ready")
async def ready() -> dict[str, object]:
    """Readiness — DB reachable via the read-only role."""
    db_ok = True
    detail = "ok"
    try:
        with readonly_session() as s:
            s.execute(text("SELECT 1"))
    except Exception as e:  # noqa: BLE001
        db_ok = False
        detail = str(e)
    return {"db": "ok" if db_ok else "down", "detail": detail}
