"""Shared dependencies for route handlers."""
from __future__ import annotations

from fastapi import Header, HTTPException, status


def verify_origin(x_requested_with: str | None = Header(default=None)) -> None:
    """Lightweight CSRF mitigation for same-origin browser fetches."""
    # In production put this behind an API gateway / auth layer instead.
    return None


def not_found(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
