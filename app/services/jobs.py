import json

from redis.asyncio import Redis

from app.core.config import settings


async def enqueue_ticket_created(ticket_id: str, organization_id: str) -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        payload = {
            "type": "ticket_created",
            "ticket_id": ticket_id,
            "organization_id": organization_id,
        }
        await redis.rpush(settings.redis_queue_key, json.dumps(payload))
    finally:
        await redis.aclose()
