import asyncio
import logging
from dataclasses import dataclass

from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings


logger = logging.getLogger("opspilot.rate_limit")

EXCLUDED_PATHS = {
    "/health",
    "/ready",
    "/metrics",
}

RATE_LIMIT_SCRIPT = """
local current = redis.call("INCR", KEYS[1])

if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end

local ttl = redis.call("TTL", KEYS[1])

if ttl < 0 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
    ttl = tonumber(ARGV[1])
end

return {current, ttl}
"""


@dataclass
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    degraded: bool = False


redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=settings.redis_operation_timeout_seconds,
    socket_timeout=settings.redis_operation_timeout_seconds,
    retry_on_timeout=False,
)


def get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")

    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()

    if request.client:
        return request.client.host

    return "unknown"


async def check_rate_limit(request: Request) -> RateLimitDecision:
    if not settings.rate_limit_enabled:
        return RateLimitDecision(
            allowed=True,
            limit=settings.rate_limit_requests,
            remaining=settings.rate_limit_requests,
            retry_after=0,
        )

    if request.url.path in EXCLUDED_PATHS:
        return RateLimitDecision(
            allowed=True,
            limit=settings.rate_limit_requests,
            remaining=settings.rate_limit_requests,
            retry_after=0,
        )

    client_id = get_client_identifier(request)
    key = f"opspilot:rate_limit:{client_id}"

    try:
        result = await asyncio.wait_for(
            redis_client.eval(
                RATE_LIMIT_SCRIPT,
                1,
                key,
                settings.rate_limit_window_seconds,
            ),
            timeout=settings.redis_operation_timeout_seconds,
        )

        current = int(result[0])
        ttl = max(int(result[1]), 1)

        return RateLimitDecision(
            allowed=current <= settings.rate_limit_requests,
            limit=settings.rate_limit_requests,
            remaining=max(settings.rate_limit_requests - current, 0),
            retry_after=ttl,
        )

    except asyncio.CancelledError:
        raise

    except (RedisError, asyncio.TimeoutError) as exc:
        logger.warning(
            "Rate limiter Redis unavailable; failing open",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc)[:1000],
            },
        )

        return RateLimitDecision(
            allowed=True,
            limit=settings.rate_limit_requests,
            remaining=settings.rate_limit_requests,
            retry_after=0,
            degraded=True,
        )
