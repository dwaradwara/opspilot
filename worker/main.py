import asyncio
import json
import logging

from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("opspilot.worker")


async def run_worker() -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Worker started")
    try:
        while True:
            item = await redis.blpop(settings.redis_queue_key, timeout=5)
            if item is None:
                continue
            _, raw_payload = item
            payload = json.loads(raw_payload)
            if payload.get("type") == "ticket_created":
                logger.info(
                    "Processed ticket_created notification",
                    extra={"organization_id": payload.get("organization_id")},
                )
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run_worker())
