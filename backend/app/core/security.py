"""SQL safety layer.

The goal is defense-in-depth: even though the runtime DB role is read-only,
we statically reject anything that *looks* destructive before it ever reaches
the database. This module is deliberately over-fitted to our use case:
    * Single statement only
    * SELECT / WITH ... SELECT only
    * No forbidden keywords anywhere in the text
    * No statement-level comments (-- or /*) to defeat keyword scanning
    * Row LIMIT is enforced if missing
"""
from __future__ import annotations

import re
import sqlparse
from sqlparse.sql import Statement, TokenList
from sqlparse.tokens import Keyword

from app.core.config import settings


class SQLSafetyError(ValueError):
    """Raised when generated SQL violates a guardrail."""


# ---------------------------------------------------------------------------
# 1. Comment stripping detection
# ---------------------------------------------------------------------------
_COMMENT_RE = re.compile(r"(--[^\n]*$|/\*.*?\*/)", re.MULTILINE | re.DOTALL)

# ---------------------------------------------------------------------------
# 2. Statement type allow-list
# ---------------------------------------------------------------------------
_ALLOWED_ROOT_KEYWORDS = {"SELECT", "WITH"}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def validate_sql(sql: str) -> str:
    """Validate & normalize a single SELECT query.

    Returns the cleaned SQL (with a guaranteed LIMIT) or raises `SQLSafetyError`.
    """
    if not sql or not sql.strip():
        raise SQLSafetyError("Empty SQL.")

    raw = sql.strip().rstrip(";").strip()

    # Reject anything that contains a comment — keyword scanners can be fooled
    # by hiding forbidden words inside comments, so we forbid them outright.
    if _COMMENT_RE.search(raw):
        raise SQLSafetyError("SQL comments are not permitted.")

    # Must parse as a single statement.
    parsed = sqlparse.parse(raw)
    if len(parsed) != 1:
        raise SQLSafetyError("Only a single SQL statement is allowed.")
    stmt: Statement = parsed[0]
    if stmt.get_type() != "SELECT":
        raise SQLSafetyError(
            f"Only SELECT statements are allowed (got '{stmt.get_type()}')."
        )

    # Root keyword must be in allow-list.
    first_kw = _first_keyword(stmt)
    if first_kw not in _ALLOWED_ROOT_KEYWORDS:
        raise SQLSafetyError(f"Statement must start with SELECT or WITH (got {first_kw}).")

    # Reject multiple statements at root level that are not combined via set operators.
    dml_count = 0
    has_set_operator = False
    for tok in stmt.tokens:
        if tok.ttype == Keyword.DML:
            dml_count += 1
        elif tok.ttype == Keyword and tok.normalized.upper() in ("UNION", "INTERSECT", "EXCEPT"):
            has_set_operator = True

    if dml_count > 1 and not has_set_operator:
        raise SQLSafetyError("Only a single SQL statement is allowed.")

    # Forbidden keywords anywhere in the normalized text.
    lowered = raw.lower()
    for bad in settings.forbidden_keyword_list:
        if _contains_keyword(lowered, bad):
            raise SQLSafetyError(f"Forbidden keyword detected: {bad.upper()}.")

    # Lockdown: no semicolons mid-statement, no dangerous function calls.
    if ";" in raw:
        raise SQLSafetyError("Semicolons / multiple statements are not allowed.")
    for fn in ("pg_sleep", "lo_import", "lo_export", "pg_read_file", "pg_ls_dir"):
        if fn in lowered:
            raise SQLSafetyError(f"Disallowed function: {fn}.")

    # Inject a LIMIT if the user/LLM didn't supply one (cap to SQL_MAX_ROWS).
    cleaned = _ensure_limit(raw)
    return cleaned


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _first_keyword(stmt: TokenList) -> str:
    for tok in stmt.flatten():
        if tok.ttype in Keyword:
            return tok.normalized.upper()
    return ""


def _contains_keyword(text: str, keyword: str) -> bool:
    """Word-boundary match so 'inserted' doesn't trip on 'insert'."""
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _ensure_limit(sql: str) -> str:
    """Append `LIMIT N` when missing; clamp existing LIMIT to SQL_MAX_ROWS."""
    has_limit = re.search(r"\blimit\s+\d+", sql, re.IGNORECASE) is not None
    if not has_limit:
        return f"{sql.rstrip(';').strip()}\nLIMIT {settings.sql_max_rows};"

    # Clamp an existing limit that is larger than the cap.
    def _clamp(match: re.Match[str]) -> str:
        n = int(match.group(1))
        n = min(n, settings.sql_max_rows)
        return f"LIMIT {n}"

    return re.sub(r"\blimit\s+(\d+)", _clamp, sql, flags=re.IGNORECASE) + ";"
