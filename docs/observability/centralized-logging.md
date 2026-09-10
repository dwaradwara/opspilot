# Centralized Logging with Loki and Grafana Alloy

## Overview

OpsPilot uses a centralized logging pipeline for staging:

Docker containers -> Grafana Alloy -> Loki -> Grafana Explore

Grafana Alloy discovers Docker containers through the Docker socket, attaches useful labels, and forwards container stdout/stderr logs to Loki.

## Components

- Grafana Alloy - Docker log discovery and forwarding
- Loki - centralized log storage and querying
- Grafana Explore - investigation and LogQL queries

## Log Labels

Logs include labels such as:

- environment
- service
- container
- job

Example:

```logql
{service="api"}
```

## Structured API Logs

OpsPilot API logs include structured fields such as:

- timestamp
- level
- logger
- message
- request_id
- method
- path
- status_code
- duration_ms
- exception_type
- exception_message

## Request Correlation

A request can be investigated directly using its request ID:

```logql
{service="api"} | json | request_id="<request-id>"
```

This provides a production-support workflow:

Customer/API failure -> request_id -> Grafana Explore -> exact request log -> exception details

## Error Safety

Internal exception details are retained in centralized logs for engineering investigation.

The API client continues to receive a safe response such as:

```json
{
  "detail": "Internal server error",
  "request_id": "<request-id>"
}
```

Internal exception messages are not exposed to the client.

## Validation

Centralized logging was validated by intentionally making PostgreSQL unavailable and requesting a database-backed endpoint.

The API returned HTTP 500 with a request ID.

Using that request ID in Grafana Explore returned the exact structured error log including:

- HTTP status 500
- request path
- request duration
- exception type
- exception message

This confirms end-to-end request-level incident correlation through Loki.
