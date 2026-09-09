from prometheus_client import Counter, Gauge


OUTBOX_PUBLISH_TOTAL = Counter(
    "opspilot_outbox_publish_total",
    "Total number of outbox publish attempts",
    ["result"],
)

OUTBOX_PENDING_EVENTS = Gauge(
    "opspilot_outbox_pending_events",
    "Number of unpublished events currently waiting in the outbox",
)
