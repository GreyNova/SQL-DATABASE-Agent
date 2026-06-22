"""Schema discovery service.

Caches the live schema (from information_schema) so we never hammer the catalog,
and exposes a compact, hand-curated DDL string we feed to the LLM prompt for
token efficiency and stability.
"""
from __future__ import annotations

import time

from sqlalchemy import text

from app.core.db import readonly_session

# The agent is scoped to these tables only.
ALLOWED_TABLES: tuple[str, ...] = ("users", "products", "orders", "order_items")

_SCHEMA_QUERY = """
SELECT c.table_name, c.column_name, c.data_type, c.is_nullable, c.column_default
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.table_name = ANY(:tables)
ORDER BY c.table_name, c.ordinal_position;
"""

# Compact, human/LLM-readable DDL shipped to prompts instead of the live catalog
# (fewer tokens, stable shape, hides irrelevant columns).
_CANONICAL_DDL = """
CREATE TABLE users (
    id          BIGINT PRIMARY KEY,
    name        TEXT,
    email       TEXT,
    city        TEXT,
    created_at  TIMESTAMPTZ
);

CREATE TABLE products (
    id          BIGINT PRIMARY KEY,
    name        TEXT,
    category    TEXT,
    price       NUMERIC(12,2),
    stock       INTEGER
);

CREATE TABLE orders (
    id            BIGINT PRIMARY KEY,
    user_id       BIGINT REFERENCES users(id),
    order_date    TIMESTAMPTZ,
    total_amount  NUMERIC(12,2),
    status        TEXT          -- pending|paid|shipped|delivered|cancelled|refunded
);

CREATE TABLE order_items (
    id          BIGINT PRIMARY KEY,
    order_id    BIGINT REFERENCES orders(id),
    product_id  BIGINT REFERENCES products(id),
    quantity    INTEGER,
    price       NUMERIC(12,2)   -- unit price at time of order
);

-- Relationships:
--   orders.user_id         -> users.id
--   order_items.order_id   -> orders.id
--   order_items.product_id -> products.id
-- Revenue = SUM(orders.total_amount) where status NOT IN ('cancelled','refunded')
--           (equivalently SUM(order_items.quantity * order_items.price)).
"""


class SchemaService:
    """Reads & caches the live schema; serves stable DDL for prompts."""

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self._ttl = ttl_seconds
        self._cached_at: float = 0.0
        self._live_cache: dict[str, list[dict[str, str]]] = {}

    def get_ddl(self) -> str:
        """Return DDL text suitable for the LLM prompt."""
        return _CANONICAL_DDL

    def get_live_schema(self) -> dict[str, list[dict[str, str]]]:
        """Return {table: [{column, type, nullable}, ...]} from the catalog."""
        if time.time() - self._cached_at < self._ttl and self._live_cache:
            return self._live_cache

        from sqlalchemy import inspect
        from app.core.db import readonly_engine

        out: dict[str, list[dict[str, str]]] = {t: [] for t in ALLOWED_TABLES}
        try:
            inspector = inspect(readonly_engine)
            for table_name in ALLOWED_TABLES:
                columns = inspector.get_columns(table_name)
                for col in columns:
                    out[table_name].append(
                        {
                            "column": col["name"],
                            "type": str(col["type"]),
                            "nullable": "YES" if col.get("nullable", True) else "NO",
                        }
                    )
        except Exception:
            pass

        self._live_cache = out
        self._cached_at = time.time()
        return out


_schema_service: SchemaService | None = None


def schema_service() -> SchemaService:
    """Process-wide singleton."""
    global _schema_service
    if _schema_service is None:
        _schema_service = SchemaService()
    return _schema_service
