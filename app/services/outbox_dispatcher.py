import asyncio
import json
import logging
from datetime import datetime, timezone

from prometheus_client import start_http_server
from redis.asyncio import Redis
from redis.exceptions import RedisError
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


async def publish_with_retry(
    redis: Redis,
    message_payload: dict,
    event_id: str,
    event_type: str,
) -> int:
    max_attempts = settings.redis_retry_attempts + 1

    for attempt in range(1, max_attempts + 1):
        try:
            await asyncio.wait_for(
                redis.rpush(
                    settings.redis_queue_key,
                    json.dumps(message_payload),
                ),
                timeout=settings.redis_operation_timeout_seconds,
            )

            if attempt > 1:
                logger.info(
                    "Outbox publish recovered after retry",
                    extra={
                        "event_id": event_id,
                        "event_type": event_type,
                        "attempts": attempt,
                    },
                )

            return attempt - 1

        except asyncio.CancelledError:
            raise

        except (RedisError, asyncio.TimeoutError) as exc:
            if attempt >= max_attempts:
                logger.error(
                    "Outbox publish retries exhausted",
                    extra={
                        "event_id": event_id,
                        "event_type": event_type,
                        "attempts": attempt,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc)[:1000],
                    },
                )
                raise

            delay = min(
                settings.redis_retry_base_delay_seconds
                * (2 ** (attempt - 1)),
                settings.redis_retry_max_delay_seconds,
            )

            logger.warning(
                "Outbox publish attempt failed; retrying",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                    "attempts": attempt,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc)[:1000],
                },
            )

            await asyncio.sleep(delay)

    raise RuntimeError("Redis publish retry loop exited unexpectedly")


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
            socket_connect_timeout=settings.redis_operation_timeout_seconds,
            socket_timeout=settings.redis_operation_timeout_seconds,
            retry_on_timeout=False,
        )

        message_payload = {
            **event.payload,
            "event_id": str(event.id),
            "event_type": event.event_type,
        }

        try:
            failed_attempts = await publish_with_retry(
                redis=redis,
                message_payload=message_payload,
                event_id=str(event.id),
                event_type=event.event_type,
            )

            event.attempts += failed_attempts
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
                    "attempts": event.attempts,
                },
            )

            return True

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            event.attempts += settings.redis_retry_attempts + 1
            event.last_error = str(exc)[:1000]

            await session.commit()

            OUTBOX_PUBLISH_TOTAL.labels(result="failure").inc()

            logger.exception(
                "Outbox publish failed",
                extra={
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "attempts": event.attempts,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc)[:1000],
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
