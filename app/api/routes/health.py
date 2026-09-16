import asyncio

from fastapi import APIRouter, Response, status
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "opspilot-api",
    }


@router.get("/ready")
async def ready(response: Response) -> dict:
    checks = {
        "postgres": False,
        "schema": False,
        "redis": False,
    }

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            checks["postgres"] = True

            try:
                current_revision = await session.scalar(
                    text(
                        "SELECT version_num "
                        "FROM alembic_version "
                        "LIMIT 1"
                    )
                )

                checks["schema"] = (
                    current_revision
                    == settings.required_db_schema_revision
                )

            except Exception:
                checks["schema"] = False

    except Exception:
        checks["postgres"] = False
        checks["schema"] = False

    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=settings.redis_operation_timeout_seconds,
        socket_timeout=settings.redis_operation_timeout_seconds,
        retry_on_timeout=False,
    )

    try:
        checks["redis"] = bool(
            await asyncio.wait_for(
                redis.ping(),
                timeout=settings.redis_operation_timeout_seconds,
            )
        )

    except Exception:
        checks["redis"] = False

    finally:
        await redis.aclose()

    if not checks["postgres"] or not checks["schema"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "status": "not_ready",
            "checks": checks,
            "degraded_dependencies": [],
        }

    if not checks["redis"]:
        return {
            "status": "degraded",
            "checks": checks,
            "degraded_dependencies": ["redis"],
        }

    return {
        "status": "ready",
        "checks": checks,
        "degraded_dependencies": [],
    }
