"""Pytest fixtures for unit tests.

Unit tests must NOT hit a real DB or a real LLM. We set safe dummy env vars
before importing app modules so `get_settings()` doesn't fail on missing secrets.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `app` importable when running from backend/tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Provide dummy secrets so Settings() validates without a real .env
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
os.environ.setdefault("READONLY_DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
