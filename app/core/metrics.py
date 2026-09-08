from prometheus_client import Counter, Gauge, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "opspilot_http_requests_total",
    "Total number of HTTP requests processed by OpsPilot",
    ["method", "route", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "opspilot_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "opspilot_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"],
)