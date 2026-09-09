import asyncio
import json
import logging
from datetime import datetime, timezone

from prometheus_client import start_http_server
from redis.asyncio import Redis
from sqlalchemy import func, select

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal
from app.models.outbox_event import OutboxEvent
from app.services.outbox_metrics import (
    OUTBOX_PENDING_EVENTS,
    OUTBOX_PUBLISH_TOTAL,
)


configure_logging()
logger = logging.getLogger("opspilot.outbox")


async def dispatch_once() -> bool:
    async with AsyncSessionLocal() as session:
        pending_count = await session.scalar(
            select(func.count())
            .select_from(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
        )

        OUTBOX_PENDING_EVENTS.set(pending_count or 0)

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

            OUTBOX_PUBLISH_TOTAL.labels(result="success").inc()
            OUTBOX_PENDING_EVENTS.set(max((pending_count or 1) - 1, 0))

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

            OUTBOX_PUBLISH_TOTAL.labels(result="failure").inc()

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
    start_http_server(9101)

    logger.info("Outbox dispatcher started")
    logger.info(
        "Outbox metrics server started",
        extra={"port": 9101},
    )

    while True:
        dispatched = await dispatch_once()

        if not dispatched:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_dispatcher())
