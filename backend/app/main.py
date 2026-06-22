"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import chat as chat_routes
from app.api.routes import meta as meta_routes
from app.api.routes import system as system_routes
from app.core.config import settings
from app.core.logging import configure_logging

# Rate limiter (in-memory by default; back with redis for multi-instance)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # LangSmith tracing is wired purely through env vars; nothing to init here,
    # but we log the target project so it's visible in startup logs.
    if settings.langsmith_tracing:
        import logging

        logging.getLogger("app").info(
            "LangSmith tracing enabled → project=%s", settings.langsmith_project
        )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Natural-language → SQL agent (FastAPI + LangGraph)",
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    # ---- middleware ----
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- routes ----
    app.include_router(system_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(meta_routes.router)

    @app.get("/", include_in_schema=False)
    async def root() -> HTMLResponse:
        from fastapi.responses import HTMLResponse
        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, "templates", "index.html")
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        response = HTMLResponse(content=html_content)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    # ---- global exception handler so agent errors never leak a traceback ----
    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        import logging

        logging.getLogger("app").exception("Unhandled error")
        detail = str(exc) if settings.app_debug else exc.__class__.__name__
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": detail},
        )

    return app


app = create_app()
