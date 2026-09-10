import asyncio
import json
import logging
import uuid

from prometheus_client import start_http_server
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal
from app.models.processed_event import ProcessedEvent
from worker.metrics import (
    WORKER_EVENTS_PROCESSED_TOTAL,
    WORKER_REDIS_RECONNECTS_TOTAL,
)


configure_logging()
logger = logging.getLogger("opspilot.worker")

CONSUMER_NAME = "ticket-worker"


async def process_event(payload: dict) -> None:
    event_id_raw = payload.get("event_id")
    event_type = payload.get("event_type") or payload.get("type")

    if not event_id_raw:
        logger.warning(
            "Event missing event_id; skipping",
            extra={"event_type": event_type},
        )
        return

    if event_type != "ticket_created":
        logger.warning(
            "Unsupported event type; skipping",
            extra={
                "event_id": event_id_raw,
                "event_type": event_type,
            },
        )
        return

    try:
        event_id = uuid.UUID(event_id_raw)
    except (ValueError, TypeError):
        logger.warning(
            "Invalid event_id; skipping",
            extra={
                "event_id": event_id_raw,
                "event_type": event_type,
            },
        )
        return

    async with AsyncSessionLocal() as session:
        statement = (
            insert(ProcessedEvent)
            .values(
                event_id=event_id,
                consumer_name=CONSUMER_NAME,
                event_type=event_type,
            )
            .on_conflict_do_nothing(
                index_elements=["event_id", "consumer_name"]
            )
            .returning(ProcessedEvent.event_id)
        )

        result = await session.execute(statement)
        claimed_event_id = result.scalar_one_or_none()

        if claimed_event_id is None:
            await session.rollback()

            logger.info(
                "Duplicate event skipped",
                extra={
                    "event_id": str(event_id),
                    "event_type": event_type,
                    "consumer_name": CONSUMER_NAME,
                },
            )
            return

        logger.info(
            "Processed ticket_created notification",
            extra={
                "event_id": str(event_id),
                "ticket_id": payload.get("ticket_id"),
                "organization_id": payload.get("organization_id"),
                "consumer_name": CONSUMER_NAME,
            },
        )

        await session.commit()

        WORKER_EVENTS_PROCESSED_TOTAL.labels(
            event_type="ticket_created"
        ).inc()


async def run_worker() -> None:
    start_http_server(9102)
    logger.info("Worker started")
    logger.info("Worker metrics server started", extra={"port": 9102})

    while True:
        redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

        try:
            logger.info("Worker connecting to Redis")

            while True:
                item = await redis.blpop(
                    settings.redis_queue_key,
                    timeout=5,
                )

                if item is None:
                    continue

                _, raw_payload = item

                try:
                    payload = json.loads(raw_payload)
                except json.JSONDecodeError as exc:
                    logger.error(
                        "Malformed queue message; skipping",
                        extra={"error": str(exc)},
                    )
                    continue

                await process_event(payload)

        except asyncio.CancelledError:
            raise

        except RedisError as exc:
            WORKER_REDIS_RECONNECTS_TOTAL.inc()

            logger.error(
                "Redis unavailable; worker will retry",
                extra={"error": str(exc)},
            )

            await asyncio.sleep(2)

        finally:
            await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run_worker())
