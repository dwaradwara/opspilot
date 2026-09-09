import asyncio
import json
import logging

from prometheus_client import start_http_server
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import configure_logging
from worker.metrics import (
    WORKER_EVENTS_PROCESSED_TOTAL,
    WORKER_REDIS_RECONNECTS_TOTAL,
)


configure_logging()
logger = logging.getLogger("opspilot.worker")


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
                payload = json.loads(raw_payload)

                if payload.get("type") == "ticket_created":
                    logger.info(
                        "Processed ticket_created notification",
                        extra={
                            "ticket_id": payload.get("ticket_id"),
                            "organization_id": payload.get("organization_id"),
                        },
                    )

                    WORKER_EVENTS_PROCESSED_TOTAL.labels(
                        event_type="ticket_created"
                    ).inc()

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
