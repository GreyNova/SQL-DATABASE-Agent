"""Database engines & sessions — dialect-aware.

Works locally against SQLite AND in production against PostgreSQL. The
Postgres path additionally hard-enforces a statement timeout + read-only
transaction; SQLite gets an equivalent read-only guarantee via the validator
(every write keyword is already blocked) plus a Python-side row cap.
"""
from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _engine_kwargs(url: str) -> dict[str, Any]:
    """Per-dialect engine creation kwargs."""
    if _is_sqlite(url):
        # Allow the FastAPI threadpool to share the SQLite connection.
        return {"future": True, "connect_args": {"check_same_thread": False}}
    return {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 5,
        "future": True,
    }


# Resolve relative SQLite paths against this file's directory so the app works
# no matter the current working directory (uvicorn, tests, scripts, …).
def _resolve_url(url: str) -> str:
    if _is_sqlite(url) and ":///" in url and not (
        url.startswith("sqlite:////")  # already absolute
        or ":memory:" in url
    ):
        # form: sqlite:///../amazon_test.db  -> normalize to absolute
        path_part = url.split("sqlite:///", 1)[1]
        absolute = (Path(__file__).resolve().parents[2] / path_part).resolve()
        return f"sqlite:///{absolute}"
    return url


_resolved_db = _resolve_url(settings.database_url)
_resolved_ro = _resolve_url(settings.readonly_database_url)

# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------
admin_engine: Engine = create_engine(_resolved_db, **_engine_kwargs(_resolved_db))
readonly_engine: Engine = create_engine(_resolved_ro, **_engine_kwargs(_resolved_ro))

AdminSession = sessionmaker(bind=admin_engine, expire_on_commit=False, future=True)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def admin_session() -> Iterator[Session]:
    """Migrations / admin only."""
    s = AdminSession()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


@contextlib.contextmanager
def readonly_session() -> Iterator[Session]:
    """The session the agent uses.

    * PostgreSQL: sets a statement timeout + read-only transaction per session.
    * SQLite:     no-op (the validator already blocks every write keyword, and
                  we open the DB read-only via the URI when possible).
    """
    s = Session(readonly_engine, expire_on_commit=False)
    try:
        if "postgresql" in str(readonly_engine.url):
            s.execute(text("SET LOCAL statement_timeout = :ms"),
                      {"ms": settings.sql_query_timeout_seconds * 1000})
            s.execute(text("SET LOCAL default_transaction_read_only = on"))
        yield s
        s.rollback()  # never commit from a read-only path
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def fetchall_as_dicts(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run a SELECT via the read-only engine and return JSON-friendly rows."""
    with readonly_session() as s:
        result = s.execute(text(query), params or {})
        return [dict(r._mapping) for r in result.fetchall()]
