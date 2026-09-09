import asyncio
import json
import logging
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal
from app.models.outbox_event import OutboxEvent


configure_logging()
logger = logging.getLogger("opspilot.outbox")


async def dispatch_once() -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        event = result.scalar_one_or_none()

        if event is None:
            return False

        redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

        try:
            await redis.rpush(
                settings.redis_queue_key,
                json.dumps(event.payload),
            )

            event.published_at = datetime.now(timezone.utc)
            event.last_error = None

            await session.commit()

            logger.info(
                "Outbox event published",
                extra={
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                },
            )

            return True

        except Exception as exc:
            event.attempts += 1
            event.last_error = str(exc)

            await session.commit()

            logger.exception(
                "Outbox publish failed",
                extra={
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "attempts": event.attempts,
                },
            )

            return False

        finally:
            await redis.aclose()


async def run_dispatcher() -> None:
    logger.info("Outbox dispatcher started")

    while True:
        dispatched = await dispatch_once()

        if not dispatched:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_dispatcher())
