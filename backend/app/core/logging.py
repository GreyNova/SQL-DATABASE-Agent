"""Structured logging via stdlib logging + JSON formatter for production."""
from __future__ import annotations

import logging
import sys

from app.core.config import settings


class _JsonFormatter(logging.Formatter):
    """Minimal JSON formatter — replace with `python-json-logger` in heavy prod."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        base = super().format(record)
        return (
            f'{{"ts":"{self.formatTime(record)}","level":"{record.levelName if False else record.levelname}",'
            f'"logger":"{record.name}","msg":{_q(base)}}}'
        )


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    root.handlers = [handler]

    # Quiet noisy libs
    for noisy in ("httpx", "httpcore", "openai._base_client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
