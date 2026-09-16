# Runbook — PostgreSQL Connection Pool Exhaustion

## Purpose

Use this runbook when OpsPilot API requests fail or stall because the application cannot obtain PostgreSQL connections from the SQLAlchemy pool.

## Symptoms

Typical signals:

- HTTP 500 responses increase
- requests take approximately the configured pool timeout before failing
- `OpsPilotDBPoolHighUtilization` alert fires
- checked-out database connections remain high
- overflow connections increase
- PostgreSQL sessions are blocked or long-running

## Relevant Metrics

Check:

- `opspilot_db_pool_size`
- `opspilot_db_pool_capacity`
- `opspilot_db_pool_checked_out_connections`
- `opspilot_db_pool_checked_in_connections`
- `opspilot_db_pool_overflow_connections`

## Initial Triage

Check application readiness:

    curl http://<staging-endpoint>/ready

If PostgreSQL is completely unavailable, readiness should return HTTP 503.

If PostgreSQL responds but requests are failing, investigate pool pressure and database contention.

## PostgreSQL Investigation

Inspect active sessions:

    SELECT
        pid,
        state,
        wait_event_type,
        wait_event,
        query_start,
        query
    FROM pg_stat_activity
    WHERE datname = current_database()
    ORDER BY query_start;

Inspect locks:

    SELECT
        pid,
        locktype,
        relation::regclass,
        mode,
        granted
    FROM pg_locks
    WHERE relation IS NOT NULL
    ORDER BY granted, pid;

Look for:

- blocked sessions
- long-running transactions
- table locks
- idle transactions
- slow queries
- unusually high connection usage

## Diagnosis

Pool exhaustion occurs when application requests hold all available database connections long enough that another request cannot obtain one before the configured pool timeout.

Common causes:

- blocking PostgreSQL locks
- long-running queries
- long transactions
- application connection leaks
- abnormal concurrency
- insufficient capacity

Do not assume increasing pool size fixes the root cause.

## Recovery

Identify the database session causing the contention.

For a confirmed blocking backend in staging:

    SELECT pg_terminate_backend(<pid>);

Terminate only a PID that has been positively identified as the blocker.

In production, follow the appropriate approval and escalation process before terminating database sessions.

## Recovery Validation

After removing the blocker verify:

1. affected API endpoint returns HTTP 200
2. checked-out connections decrease
3. overflow connections return toward zero
4. blocked PostgreSQL sessions clear
5. `/ready` reports PostgreSQL healthy
6. `/ready` reports schema healthy
7. `OpsPilotDBPoolHighUtilization` resolves

## Decision Points

### Pool high but requests still succeeding

Investigate before full exhaustion occurs.

Use metrics and `pg_stat_activity` to find the source of sustained connection usage.

### Pool exhausted because of a blocking lock

Remove the blocker rather than restarting the API.

### Pool remains saturated after blocker removal

Investigate:

- leaked sessions
- long transactions
- repeated expensive queries
- PostgreSQL resource pressure
- application traffic spike

## Escalation

Escalate when:

- pool repeatedly exhausts under normal load
- RDS approaches its connection limit
- database CPU or memory pressure is high
- lock contention cannot be safely resolved
- connection usage does not recover after the suspected blocker is removed

## Do Not

- do not blindly increase pool size
- do not restart the API before inspecting PostgreSQL
- do not terminate unknown database sessions
- do not assume every HTTP 500 is caused by the connection pool

## Related Incident

docs/incidents/INC-003-postgres-pool-exhaustion.md
