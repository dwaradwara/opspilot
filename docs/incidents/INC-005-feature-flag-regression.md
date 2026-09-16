# INC-005 — Feature Flag Regression Silently Disabled Notifications

## Environment

AWS Staging

## Severity

SEV-2 / Controlled Configuration Regression

## Summary

A controlled failure-injection exercise validated how OpsPilot behaves when the ticket notification feature is accidentally disabled through configuration.

A temporary ECS API task definition was created using the same immutable application image as the healthy deployment.

The only intentional configuration change was:

`FEATURE_TICKET_NOTIFICATIONS_ENABLED=false`

The API remained healthy and continued accepting ticket creation requests.

However, ticket notification outbox events were silently skipped.

## Failure Injection

Healthy API revision:

`opspilot-staging-api:36`

Failure-injection revision:

`opspilot-staging-api:37`

Revision 37 added:

`FEATURE_TICKET_NOTIFICATIONS_ENABLED=false`

No application image, database, Redis, networking, worker, or infrastructure configuration was changed.

## Infrastructure Health

During the regression `/ready` continued returning:

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