# INC-001 — Nginx Upstream Misconfiguration Causing HTTP 502

## Environment
Staging

## Severity
SEV-2 / Service Degradation

## Summary
The OpsPilot staging endpoint returned HTTP 502 Bad Gateway while the FastAPI application remained healthy.

## Customer Impact
Requests routed through the Nginx reverse proxy failed with HTTP 502 responses.

The backend API itself remained operational.

## Detection
The issue was reproduced through the staging Nginx endpoint:

`http://localhost:18080/health`

Response:

`HTTP/1.1 502 Bad Gateway`

## Investigation

Direct API health check from inside the API container succeeded:

`http://127.0.0.1:8000/health`

Result:

`{"status":"healthy","service":"opspilot-api"}`

Connectivity from the Nginx container to the correct backend endpoint also succeeded:

`http://api:8000/health`

Connectivity to the configured upstream port failed:

`http://api:9999/health`

Nginx logged:

`connect() failed (111: Connection refused) while connecting to upstream`

The failing upstream was port `9999`.

## Root Cause

The staging Nginx upstream configuration incorrectly pointed to:

`api:9999`

The FastAPI service was actually listening on:

`api:8000`

## Resolution

The Nginx upstream configuration was corrected from:

`api:9999`

to:

`api:8000`

The staging Nginx container was recreated with the corrected configuration.

## Validation

After recovery:

`HTTP/1.1 200 OK`

and:

`{"status":"healthy","service":"opspilot-api"}`

The normal OpsPilot environment remained healthy throughout the staging incident.

## Monitoring Gap Identified

Application-level Prometheus 5xx metrics cannot detect 502 responses generated directly by Nginx because those requests never reach the FastAPI application.

A proxy-level Nginx error metric or log-derived alert should be added to detect this failure mode.

## Preventive Actions

- Add Nginx 5xx monitoring.
- Add an alert for elevated proxy 502/504 responses.
- Validate upstream connectivity during deployment.
- Maintain separate staging Nginx configuration for destructive testing.
