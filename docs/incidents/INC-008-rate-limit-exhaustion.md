# INC-008 — Rate Limit Exhaustion / HTTP 429

## Environment

AWS Staging

## Severity

SEV-3 / Controlled Client Throttling Scenario

## Summary

A controlled traffic exercise validated OpsPilot's Redis-backed API rate limiter.

A harmless nonexistent API path was repeatedly requested from the same client until the configured request quota was exhausted.

The API correctly returned HTTP 429 responses while the application and its dependencies remained healthy.

After the rate-limit window expired, normal request processing resumed automatically.

## Configuration

The staging API was configured with:

- Rate limiting enabled
- Request limit: 60
- Window: 60 seconds

The rate limiter stores client request counters in Redis.

Health endpoints including `/ready` are excluded from throttling.

## Failure Injection

A harmless nonexistent endpoint was used:

`/api/v1/inc008-rate-limit-probe`

Because the route does not exist, requests below the rate limit normally returned HTTP 404.

No application data was created or modified.

## Rate Limit Trigger

Requests were sent repeatedly from the same client.

The first blocked request was:

- Request: 61
- HTTP status: 429
- Limit: 60
- Remaining: 0
- Retry-After: 52 seconds

This confirmed that the API enforced the configured request quota.

## Service Health During Throttling

While the client was receiving HTTP 429 responses, `/ready` returned:

```json
{
  "status": "ready",
  "checks": {
    "postgres": true,
    "schema": true,
    "redis": true
  },
  "degraded_dependencies": []
}