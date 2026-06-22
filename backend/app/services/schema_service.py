"""Schema discovery service.

Dialect-agnostic: uses SQLAlchemy's `inspect()` so it works on both SQLite
(local) and PostgreSQL (production). Caches the live schema so we never hammer
the catalog, and exposes a compact DDL string we feed to the LLM prompt.
"""
from __future__ import annotations

import time

from sqlalchemy import inspect

from app.core.db import readonly_engine

# The agent is scoped to these tables only.
ALLOWED_TABLES: tuple[str, ...] = ("amazon_products", "amazon_sales")

# Compact, LLM-readable DDL shipped to prompts for token efficiency & stability.
# Mirrors the actual amazon_test.db schema.
_CANONICAL_DDL = """
CREATE TABLE amazon_products (
    id              INTEGER PRIMARY KEY,
    product_name    TEXT,         -- display name of the product
    category        TEXT,         -- e.g. Electronics, Books, Clothing & Accessories, …
    price           REAL,         -- current unit price in INR
    rating          REAL,         -- average customer rating (1.0 - 5.0)
    stock_quantity  INTEGER       -- units currently in stock
);

CREATE TABLE amazon_sales (
    id            INTEGER PRIMARY KEY,
    product_id    INTEGER,        -- -> amazon_products.id
    customer_id   INTEGER,        -- anonymized customer identifier
    sale_date     TEXT,           -- ISO date string 'YYYY-MM-DD'
    quantity      INTEGER,        -- units sold in this transaction
    total_price   REAL            -- line revenue = quantity * unit price at sale time
);

-- Relationships:
--   amazon_sales.product_id  -> amazon_products.id
-- Revenue   = SUM(amazon_sales.total_price)
-- Units sold = SUM(amazon_sales.quantity)
-- Top products = GROUP BY amazon_products.name / category
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
        """Return {table: [{column, type, nullable}, ...]} via SQLAlchemy introspection."""
        if time.time() - self._cached_at < self._ttl and self._live_cache:
            return self._live_cache

        out: dict[str, list[dict[str, str]]] = {t: [] for t in ALLOWED_TABLES}
        try:
            inspector = inspect(readonly_engine)
            available = set(inspector.get_table_names())
            for table_name in ALLOWED_TABLES:
                if table_name not in available:
                    continue
                for col in inspector.get_columns(table_name):
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
