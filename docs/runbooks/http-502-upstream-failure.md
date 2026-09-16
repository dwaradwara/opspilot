# Runbook — HTTP 502 Upstream Failure

## Purpose

Use this runbook when OpsPilot returns HTTP 502 from the proxy or load-balancer path while the backend application may still be healthy.

## Symptoms

Typical signals:

- external endpoint returns HTTP 502
- `OpsPilotStagingEndpointDown` alert fires
- Blackbox `probe_success = 0`
- backend `/health` succeeds directly
- Nginx or proxy logs show upstream connection failure

## Initial Triage

Check the external path:

    curl -i http://<endpoint>/health

If the external path returns 502, test the backend directly from the relevant network/container context.

Example:

    curl -i http://api:8000/health

If the backend is healthy but the proxy path fails, investigate routing and upstream configuration.

## Investigation

Check:

- upstream hostname
- upstream port
- backend listening port
- service discovery / DNS
- security-group connectivity
- target task health
- recent configuration or deployment changes

Typical Nginx error:

    connect() failed (...) while connecting to upstream

Check whether the configured destination matches the actual backend service.

## Diagnosis Pattern

Typical failure path:

    Client
      -> proxy
      -> incorrect upstream host or port
      -> connection failure
      -> HTTP 502

The backend API can remain healthy while users receive 502 responses.

Application-level HTTP metrics may not detect this because the request never reaches the application.

## Recovery

Correct the upstream configuration or routing issue.

Reload or recreate only the affected proxy/service after validating the corrected destination.

Avoid restarting unrelated services.

## Recovery Validation

After remediation verify:

1. external `/health` returns HTTP 200
2. backend `/health` remains healthy
3. Blackbox `probe_success` returns to 1
4. `OpsPilotStagingEndpointDown` resolves
5. Alertmanager sends a resolved notification
6. normal request routing is restored

## Decision Points

### Backend healthy, proxy unhealthy

Focus on:

- upstream hostname
- upstream port
- DNS
- network path
- security groups

### Backend unhealthy too

Treat as an application/service failure rather than a pure proxy issue.

### Correct upstream but connection still fails

Check:

- service discovery
- ECS task health
- target-group health
- network ACLs/security groups
- container port mappings

## Escalation

Escalate when:

- upstream configuration is correct but connectivity still fails
- DNS resolution fails repeatedly
- target tasks remain unhealthy
- security rules block traffic
- 502/504 errors continue after configuration recovery

## Do Not

- do not assume the backend is down because the proxy returns 502
- do not restart all services before testing direct backend connectivity
- do not rely only on application-generated 5xx metrics
- do not change multiple network components at once

## Related Incident

docs/incidents/INC-001-nginx-upstream-502.md
