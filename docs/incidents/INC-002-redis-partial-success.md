# INC-002 — Redis Partial Success and Event Delivery Failure

## Summary

Ticket creation originally depended directly on Redis after the PostgreSQL transaction.

When Redis became unavailable, PostgreSQL could successfully persist the ticket while the API returned an error because publishing the background event failed.

This created a partial-success condition:

- ticket persisted in PostgreSQL
- client received an error
- background event could be lost
- retry behavior was not durable
- worker exited when Redis disconnected

The incident was corrected using a transactional outbox pattern and Redis reconnection logic.

## Impact

A Redis outage could cause the ticket API to report failure even though the ticket had already been created.

This created a risk of:

- duplicate user retries
- inconsistent client/server state
- lost asynchronous events
- worker downtime after Redis recovery

## Root Cause

The ticket creation request performed two operations across separate systems:

1. commit ticket data to PostgreSQL
2. publish a `ticket_created` event to Redis

These operations were not atomic.

PostgreSQL could succeed while Redis failed.

The worker also treated a Redis connection failure as fatal and exited instead of reconnecting.

## Remediation

### Transactional Outbox

An `outbox_events` table was introduced.

Ticket creation now writes both:

- the ticket
- the corresponding `ticket_created` outbox event

inside the same PostgreSQL transaction.

The API no longer publishes directly to Redis.

### Outbox Dispatcher

A dedicated `outbox-dispatcher` staging service polls unpublished outbox events.

For each event it:

1. attempts to publish the event to Redis
2. records failed attempts and the error
3. leaves `published_at` NULL when publishing fails
4. retries pending events
5. sets `published_at` after successful publication
6. clears `last_error` after recovery

### Worker Redis Recovery

The worker was changed to handle Redis failures without exiting.

When Redis is unavailable it:

1. catches the Redis connection error
2. logs the failure
3. waits before retrying
4. reconnects automatically
5. resumes consuming queued events after Redis returns

## Validation

### Normal delivery

A ticket was created and an outbox event was written.

The dispatcher published the event to Redis.

The worker consumed the event and logged:

`Processed ticket_created notification`

The Redis queue no longer contained the processed ticket ID.

### Redis outage test

Redis was deliberately stopped in staging.

The readiness endpoint correctly reported the dependency failure while the application remained live.

A ticket was then successfully created while Redis was unavailable.

This proved the API no longer depends on Redis for successful ticket persistence.

The associated outbox event remained pending.

Observed database state during the outage:

- `attempts`: increased during retries
- `last_error`: Redis connection failure
- `published_at`: NULL

The dispatcher repeatedly logged:

`Outbox publish failed`

No outbox event was lost.

### Automatic dispatcher recovery

Redis was restored without restarting the dispatcher.

The dispatcher automatically retried the pending event and logged:

`Outbox event published`

The database record then showed:

- `last_error`: NULL
- `published_at`: populated

### Automatic worker recovery

During another Redis outage the worker remained running and repeatedly logged:

`Redis unavailable; worker will retry`

and:

`Worker connecting to Redis`

After Redis was restored, neither the worker nor dispatcher was manually restarted.

The dispatcher published the pending event and the worker automatically reconnected and logged:

`Processed ticket_created notification`

The recovered ticket ID was no longer present in the Redis queue.

## Result

The failure mode changed from:

`PostgreSQL success -> Redis failure -> API error / possible lost event`

to:

`PostgreSQL ticket + outbox atomic commit -> durable retry -> Redis recovery -> automatic event processing`

The system now tolerates temporary Redis outages without losing ticket-created events or requiring manual worker recovery.

## Components Changed

- `app/api/routes/tickets.py`
- `app/models/outbox_event.py`
- `app/models/__init__.py`
- `app/services/outbox_dispatcher.py`
- `worker/main.py`
- `alembic/env.py`
- `alembic/versions/0002_add_outbox_events.py`
- `docker-compose.staging.yml`

## Operational Evidence

The staging environment demonstrated:

- API ticket creation while Redis was unavailable
- durable PostgreSQL outbox storage
- retry attempt tracking
- Redis failure diagnostics
- automatic dispatcher recovery
- worker Redis reconnection
- eventual event consumption
- readiness monitoring for dependency failure
