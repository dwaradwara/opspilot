# Runbook — Redis Outage and Outbox Backlog

## Purpose

Use this runbook when Redis is unavailable, outbox events remain unpublished, or background event processing stops.

## Symptoms

Typical signals:

- `/ready` reports `redis: false`
- readiness status becomes `degraded`
- pending outbox events increase
- `Outbox publish failed` appears in logs
- Redis timeout or connection errors appear
- ticket creation succeeds but notifications are delayed

## Expected System Behavior

Redis failure must not prevent ticket persistence.

Expected flow:

API -> PostgreSQL ticket + outbox event -> Redis unavailable -> event remains pending -> Redis recovers -> dispatcher publishes -> worker consumes

The API should remain available while Redis is temporarily unavailable.

## Initial Triage

Check readiness:

    curl http://<staging-endpoint>/ready

Expected degraded response:

    status: degraded
    postgres: true
    schema: true
    redis: false

Check ECS services:

    aws ecs describe-services `
      --cluster opspilot-staging-cluster `
      --services opspilot-staging-api-service opspilot-staging-worker-service `
      --region eu-central-1

## Investigation

Look for these log messages:

- Redis unavailable
- Outbox publish failed
- Outbox publish retries exhausted
- Redis circuit breaker open
- connection timeout
- connection refused

Check pending outbox events:

    SELECT
        id,
        event_type,
        attempts,
        last_error,
        created_at,
        published_at
    FROM outbox_events
    WHERE published_at IS NULL
    ORDER BY created_at;

## Decision Points

### PostgreSQL healthy and Redis unhealthy

Treat the system as degraded, not fully unavailable.

Expected behavior:

- API continues accepting ticket writes
- PostgreSQL remains authoritative
- outbox events remain durable
- dispatcher retries automatically

Do not delete pending outbox events.

### Redis recovered but events remain pending

Check dispatcher logs.

Confirm the circuit breaker has moved back toward normal operation and retry attempts have resumed.

Allow automatic recovery before restarting services.

### Worker does not resume

Confirm Redis connectivity and ECS worker health.

Restart or redeploy the worker only after proving Redis is healthy and the worker remains stuck.

## Recovery Validation

After Redis recovery verify:

1. `/ready` reports `status: ready`
2. `checks.redis` is true
3. pending events are eventually published
4. `published_at` becomes populated
5. `last_error` is cleared
6. the worker consumes the event

Database validation:

    SELECT
        id,
        attempts,
        last_error,
        published_at
    FROM outbox_events
    ORDER BY created_at DESC
    LIMIT 10;

## Escalation

Escalate when:

- PostgreSQL also becomes unavailable
- backlog continues growing after Redis recovery
- circuit breaker never recovers
- worker cannot resume consumption
- duplicate or missing events are observed

## Do Not

- do not delete pending outbox rows
- do not manually mark events as published
- do not restart every service before identifying the failing dependency
- do not retry ticket creation simply because notification processing is delayed

## Related Incident

docs/incidents/INC-002-redis-partial-success.md
