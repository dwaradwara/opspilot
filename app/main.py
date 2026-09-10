import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import auth, health, members, tickets
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
)
from app.core.rate_limiter import check_rate_limit
from app.core.tracing import configure_tracing
from app.db.session import engine


configure_logging()
logger = logging.getLogger("opspilot.api")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="OpsPilot production-support and reliability engineering platform",
)

configure_tracing(app, engine)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    method = request.method
    started = time.perf_counter()

    HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()

    try:
        rate_limit = await check_rate_limit(request)

        if rate_limit.allowed:
            response = await call_next(request)
        else:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "request_id": request_id,
                },
                headers={
                    "Retry-After": str(rate_limit.retry_after),
                },
            )

        duration_seconds = time.perf_counter() - started
        duration_ms = round(duration_seconds * 1000, 2)

        route_object = request.scope.get("route")
        route = getattr(route_object, "path", "__unmatched__")

        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            route=route,
            status_code=str(response.status_code),
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            route=route,
        ).observe(duration_seconds)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-RateLimit-Limit"] = str(rate_limit.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit.remaining)

        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response

    except Exception as exc:
        duration_seconds = time.perf_counter() - started
        duration_ms = round(duration_seconds * 1000, 2)

        route_object = request.scope.get("route")
        route = getattr(route_object, "path", "__unmatched__")

        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            route=route,
            status_code="500",
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            route=route,
        ).observe(duration_seconds)

        logger.exception(
            "Unhandled request error",
            extra={
                "request_id": request_id,
                "method": method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc)[:1000],
            },
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
        )

    finally:
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1")
app.include_router(members.router, prefix="/api/v1")
