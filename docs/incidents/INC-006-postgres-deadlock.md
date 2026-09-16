# INC-006 — PostgreSQL Deadlock

## Environment

AWS Staging

## Severity

SEV-2 / Controlled Database Concurrency Failure

## Summary

A controlled failure-injection exercise was performed against two isolated OpsPilot ticket rows to validate PostgreSQL deadlock detection and application recovery behavior.

Two independent database transactions acquired row locks in opposite order, creating a circular wait condition.

PostgreSQL detected the deadlock, aborted one transaction, and allowed the other transaction to complete.

## Test Rows

Two isolated staging tickets were created specifically for this exercise.

- Ticket A: `930028ef-75d8-4f89-b019-59450fe5ba46`
- Ticket B: `903345fa-c45e-4de3-b149-a5317bdf6acd`

No production data was involved.

## Failure Injection

Transaction A:

1. locked Ticket A
2. waited
3. requested Ticket B

Transaction B:

1. locked Ticket B
2. waited
3. requested Ticket A

This created the cycle:

`TX-A -> waits for B -> TX-B -> waits for A`

## PostgreSQL Behavior

PostgreSQL detected the deadlock automatically.

One transaction was selected as the deadlock victim and aborted.

The other transaction acquired the released lock and completed successfully.

The ECS verification task returned:

`ExitCode: 0`

The test script defined exit code 0 as:

- exactly one transaction detected a deadlock
- exactly one transaction completed successfully

## Data Safety

The exercise used:

`SELECT ... FOR UPDATE`

No ticket updates or deletes were performed.

The row locks existed only for the lifetime of the two transactions.

After the deadlock victim was aborted and the surviving transaction completed, PostgreSQL released the locks automatically.

## Recovery Validation

After the test:

- the OpsPilot API remained available
- PostgreSQL connectivity remained healthy
- both test tickets remained readable
- no manual database restart was required
- no ECS service restart was required

## Root Cause

The deadlock was intentionally caused by inconsistent row-lock ordering across concurrent transactions.

Transaction A locked resources in the order:

`A -> B`

Transaction B locked resources in the order:

`B -> A`

Concurrent transactions that acquire shared resources in inconsistent order can create circular waits.

## Operational Lessons

Deadlocks are not the same as database outages.

PostgreSQL resolves deadlocks by terminating one conflicting transaction rather than stopping the database.

Applications should therefore:

- keep transactions short
- acquire shared resources in a consistent order
- detect deadlock errors
- retry safe/idempotent operations when appropriate
- avoid holding locks while performing unrelated work

## Result

The demonstrated failure path was:

`TX-A locks A -> TX-B locks B -> TX-A waits for B -> TX-B waits for A -> PostgreSQL detects deadlock -> one transaction aborted -> other transaction completes -> service remains healthy`