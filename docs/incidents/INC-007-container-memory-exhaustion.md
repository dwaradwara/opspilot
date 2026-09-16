# INC-007 — Container Memory Exhaustion / OOM Kill

## Environment

AWS Staging

## Severity

SEV-2 / Controlled Resource Exhaustion

## Summary

A controlled failure-injection exercise validated how AWS ECS/Fargate handles a container that exceeds its configured memory limit.

The exercise used an isolated one-off ECS task based on the same task definition as the staging API.

The API container command was temporarily overridden with a Python process that continuously allocated memory until the container exceeded its configured memory boundary.

The normal OpsPilot staging API service was not modified.

## Failure Injection

The temporary process repeatedly allocated approximately 20 MB memory chunks:

`20 MB -> 40 MB -> 60 MB -> ...`

until the container exceeded its allowed memory.

No changes were made to:

- the running API service
- PostgreSQL
- Redis
- the worker service
- Terraform
- networking
- application data

## Failure Detection

ECS reported:

- Exit code: `137`
- Last status: `STOPPED`
- Reason: `OutOfMemoryError: container killed due to memory usage`

Exit code 137 indicates that the process was terminated by `SIGKILL`.

The ECS reason explicitly identified memory exhaustion as the cause.

## Blast-Radius Validation

The failure occurred only in the isolated one-off Fargate task.

The actual staging API service remained:

- Desired tasks: 1
- Running tasks: 1
- Pending tasks: 0
- Rollout state: COMPLETED

The service continued using its healthy task definition.

## Application Health Validation

After the OOM event, `/ready` returned:

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