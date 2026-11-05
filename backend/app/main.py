"""PlaceMate FastAPI application entrypoint."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app import models as _models  # noqa: F401  (register tables)
from app.api.router import api_router
from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import configure_logging
from app.core.ratelimit import limiter
from app.db.base import Base
from app.db.session import SessionLocal, engine

logger = logging.getLogger("placemate.api")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        if request.url.path not in {"/healthz", "/readyz"}:
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                },
            )
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        if settings.api_public_url.startswith("https"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def create_app() -> FastAPI:
    configure_logging()
    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=0.1,
                send_default_pii=False,
                environment=settings.env,
            )
        except Exception:
            logger.warning("sentry_initialisation_failed")

    application = FastAPI(
        title="PlaceMate API",
        version="1.0.0",
        description=(
            "AI placement preparation for colleges. Resume scoring, resume-grounded mock "
            "interviews, rubric feedback and aggregate officer analytics."
        ),
        docs_url="/docs" if settings.env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.env != "production" else None,
    )
    application.state.limiter = limiter
    application.add_middleware(SlowAPIMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )

    @application.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
            headers=exc.headers,
        )

    @application.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please slow down and try again shortly.",
                "code": "rate_limited",
            },
        )

    application.include_router(api_router, prefix="/api/v1")

    @application.get("/healthz", tags=["ops"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "placemate-api"}

    @application.get("/readyz", tags=["ops"])
    def readyz() -> JSONResponse:
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            return JSONResponse({"status": "ready"})
        except Exception:
            return JSONResponse({"status": "degraded"}, status_code=503)

    @application.get("/", tags=["ops"])
    def root() -> dict[str, str]:
        return {
            "name": "PlaceMate API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/healthz",
        }

    @application.on_event("startup")
    def startup() -> None:
        if settings.is_sqlite:
            Base.metadata.create_all(engine)
            logger.info("sqlite_schema_ready")
        logger.info(
            "api_started",
            extra={"env": settings.env, "llm_provider": settings.llm_provider},
        )

    return application


app = create_app()
