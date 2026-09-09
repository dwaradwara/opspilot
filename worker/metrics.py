from prometheus_client import Counter


WORKER_EVENTS_PROCESSED_TOTAL = Counter(
    "opspilot_worker_events_processed_total",
    "Total number of events processed by the OpsPilot worker",
    ["event_type"],
)

WORKER_REDIS_RECONNECTS_TOTAL = Counter(
    "opspilot_worker_redis_reconnects_total",
    "Total number of Redis connection failures that triggered worker reconnection",
)
