# INC-003 - PostgreSQL Connection Pool Exhaustion

## Summary

A controlled staging incident reproduced PostgreSQL connection-pool exhaustion in the OpsPilot API.

The staging API was configured with:

- Pool size: 2
- Max overflow: 0
- Pool timeout: 2 seconds

Two blocked requests occupied both available database connections. A third request could not obtain a connection and returned HTTP 500 after approximately 2 seconds.

## Environment

- Environment: Staging
- Service: OpsPilot API
- Database: PostgreSQL
- ORM: SQLAlchemy Async
- Reverse proxy: Nginx

## Incident Trigger

An ACCESS EXCLUSIVE PostgreSQL lock was intentionally placed on the tickets table.

The test transaction used:

BEGIN;
LOCK TABLE tickets IN ACCESS EXCLUSIVE MODE;
SELECT pg_sleep(600);

Two concurrent requests to /api/v1/tickets became blocked while using the two available database connections.

## Symptoms

The third request returned:

HTTP 500 Internal Server Error

Client-side duration:

2.02 seconds

API log evidence:

- path: /api/v1/tickets
- status_code: 500
- duration_ms: 2002.28

The failure duration closely matched the configured 2-second database pool timeout.

## Diagnosis

PostgreSQL lock inspection confirmed:

tickets | AccessExclusiveLock | granted

The staging connection-pool configuration was:

- pool_size = 2
- max_overflow = 0
- pool_timeout = 2

With both connections occupied by blocked requests, another request could not obtain a database connection before the pool timeout expired.

## Root Cause

The immediate failure was database connection-pool exhaustion.

A PostgreSQL table lock caused two API requests to retain the only two available connections.

With max overflow disabled, the third request waited until the configured pool timeout expired.

## Recovery

The PostgreSQL backend holding the exclusive lock was terminated.

The lock was verified as removed.

No API container restart was required.

## Recovery Verification

The same endpoint was tested again after removing the database blocker.

Result:

- GET /api/v1/tickets
- Status: 200
- Recovery request elapsed: 0.05 seconds

The API recovered immediately without a restart.

## Lessons

- Connection-pool exhaustion can surface as HTTP 500 responses.
- Request duration matching pool timeout is an important diagnostic signal.
- PostgreSQL lock inspection can reveal database contention.
- Pool size, overflow, and timeout should be explicitly configured.
- Removing the underlying database blocker can restore service without restarting the API.

## Result

INC-003 demonstrated:

Failure injection -> connection-pool exhaustion -> HTTP 500 -> diagnosis -> root-cause confirmation -> remediation -> HTTP 200 recovery without API restart.
## Prevention and Observability Improvements

After reproducing the connection-pool exhaustion incident, OpsPilot was updated so database pool pressure can be detected before requests begin failing.

### Added Metrics

The API now exposes SQLAlchemy pool metrics through Prometheus:

- opspilot_db_pool_size
- opspilot_db_pool_max_overflow
- opspilot_db_pool_capacity
- opspilot_db_pool_checked_out_connections
- opspilot_db_pool_checked_in_connections
- opspilot_db_pool_overflow_connections

Normal staging configuration:

- Base pool size: 5
- Maximum overflow: 10
- Maximum connection capacity: 15
- Pool timeout: 30 seconds

### Proactive Alert

A Prometheus alert named `OpsPilotDBPoolHighUtilization` was added.

The alert fires when at least 80% of total SQLAlchemy connection capacity remains checked out for more than 1 minute.

During validation:

- 12 concurrent requests were blocked
- 12 of 15 available connections were checked out
- Pool utilization reached 80%
- 7 overflow connections were in use
- Prometheus changed the alert state to firing
- Alertmanager received the alert as active
- Slack delivered the firing notification

### Recovery Validation

After terminating the PostgreSQL backend holding the blocking table lock:

- Blocked requests completed
- Checked-out connections returned from 12 to 0
- Overflow connections returned from 7 to 0
- 5 idle connections remained available in the base pool
- Prometheus returned the alert to inactive
- Slack delivered the resolved notification

### Operational Improvement

The system can now identify sustained connection-pool pressure before full exhaustion occurs.

This changes the operational workflow from reactive failure diagnosis to proactive detection:

Database contention -> pool utilization rises -> Prometheus warning -> engineer investigates -> blocker removed -> pool recovers -> alert resolves.
