"""Tests for the SQL safety layer — the most security-critical module."""
from __future__ import annotations

import pytest

from app.core.security import SQLSafetyError, validate_sql


class TestHappyPath:
    def test_simple_select_gets_limit_appended(self):
        out = validate_sql("SELECT * FROM users")
        assert out.upper().endswith("LIMIT 200;")

    def test_with_cte_is_allowed(self):
        out = validate_sql(
            "WITH r AS (SELECT id, total_amount FROM orders) SELECT * FROM r"
        )
        assert "WITH" in out.upper()

    def test_existing_limit_is_respected(self):
        out = validate_sql("SELECT * FROM users LIMIT 10")
        assert "LIMIT 10" in out

    def test_existing_limit_above_cap_is_clamped(self, monkeypatch):
        from app.core import security

        monkeypatch.setattr(security.settings, "sql_max_rows", 50)
        out = validate_sql("SELECT * FROM users LIMIT 1000")
        assert "LIMIT 50" in out


class TestBlockedStatements:
    @pytest.mark.parametrize(
        "sql",
        [
            "DROP TABLE users",
            "DELETE FROM users WHERE 1=1",
            "UPDATE users SET name='x'",
            "INSERT INTO users(name) VALUES ('x')",
            "TRUNCATE users",
            "ALTER TABLE users ADD COLUMN x TEXT",
            "GRANT SELECT ON users TO public",
            "CREATE TABLE evil(x int)",
        ],
    )
    def test_destructive_statements_rejected(self, sql):
        with pytest.raises(SQLSafetyError):
            validate_sql(sql)

    def test_stacked_queries_rejected(self):
        with pytest.raises(SQLSafetyError):
            validate_sql("SELECT * FROM users; DROP TABLE users")

    def test_comments_rejected(self):
        with pytest.raises(SQLSafetyError):
            validate_sql("SELECT * FROM users -- DROP TABLE users")

    def test_block_comment_rejected(self):
        with pytest.raises(SQLSafetyError):
            validate_sql("SELECT * FROM users /* secret */")

    def test_pg_sleep_rejected(self):
        with pytest.raises(SQLSafetyError):
            validate_sql("SELECT pg_sleep(10)")

    def test_empty_input_rejected(self):
        with pytest.raises(SQLSafetyError):
            validate_sql("   ")

    def test_multiple_statements_rejected(self):
        with pytest.raises(SQLSafetyError):
            validate_sql("SELECT 1\nSELECT 2")
