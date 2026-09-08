from fastapi import APIRouter, Response, status
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "opspilot-api"}


@router.get("/ready")
async def ready(response: Response) -> dict:
    checks = {"postgres": False, "redis": False}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:
        pass

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        checks["redis"] = bool(await redis.ping())
    except Exception:
        pass
    finally:
        await redis.aclose()

    is_ready = all(checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if is_ready else "not_ready", "checks": checks}
