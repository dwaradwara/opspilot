# INC-004 — Failed ECS Deployment and Automatic Rollback

## Environment

AWS Staging

## Severity

SEV-2 / Controlled Deployment Failure

## Summary

A controlled failure-injection exercise validated the OpsPilot ECS deployment circuit breaker and automatic rollback behavior.

The healthy staging API was running task definition revision 33.

An intentionally broken revision 34 was registered using the same immutable application image but with the API startup command replaced by a process that remained alive without starting Uvicorn or listening on port 8000.

The broken revision was deployed to the staging API service.

The Application Load Balancer health checks rejected the new tasks because port 8000 did not respond.

ECS stopped and deregistered the unhealthy tasks and automatically restored the previous healthy task definition revision 33.

## Pre-Incident State

The API service was stable:

- Desired tasks: 1
- Running tasks: 1
- Pending tasks: 0
- Rollout state: COMPLETED
- Deployment circuit breaker: enabled
- Automatic rollback: enabled

External health check:

`/health`

returned:

`{"status":"healthy","service":"opspilot-api"}`

## Failure Injection

The existing healthy ECS task definition was copied.

Only the API container command was modified.

Instead of starting the normal FastAPI/Uvicorn process, revision 34 executed:

`python -c "import time; print('INC-004 failure injection: API intentionally not listening'); time.sleep(900)"`

The container remained alive but no application process listened on port 8000.

No changes were made to:

- application image
- PostgreSQL
- Redis
- worker service
- Terraform
- networking
- secrets

## Failure Detection

After revision 34 was deployed, the ALB registered the new target.

The target then became unhealthy because its port 8000 health check failed.

ECS service events reported that the task was unhealthy in the target group because:

`Health checks failed`

ECS subsequently:

- stopped the unhealthy task
- deregistered the failed target
- attempted deployment recovery

## Availability During Failure

The previous healthy revision 33 remained running while ECS evaluated revision 34.

External `/health` continued returning:

`{"status":"healthy","service":"opspilot-api"}`

This demonstrated that the rolling deployment configuration protected customer traffic from the failed revision.

## Automatic Rollback

The ECS deployment circuit breaker detected that revision 34 could not reach a healthy state.

The service automatically reverted to the previous task definition:

`opspilot-staging-api:33`

No manual rollback command was required.

## Recovery Validation

Final ECS state:

- Task definition: revision 33
- Desired tasks: 1
- Running tasks: 1
- Pending tasks: 0
- Rollout state: COMPLETED

Application readiness returned:

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