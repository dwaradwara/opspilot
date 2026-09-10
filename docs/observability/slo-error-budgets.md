# SLOs and Error Budgets

## Overview

OpsPilot uses Prometheus recording rules to measure service reliability and error-budget consumption in staging.

## Availability SLO

Target availability:

99.9%

Allowed error budget:

0.1%

## Latency SLO

Target:

95% of requests must complete within 500 ms.

## SLIs

OpsPilot records:

- 5-minute availability
- 5-minute HTTP error rate
- 5-minute latency compliance
- 1-hour availability
- 1-hour HTTP error rate

## Error-Budget Burn Rate

Availability burn rate is calculated by comparing the observed HTTP error rate against the 0.1% allowed error budget.

A burn rate of:

- 1x means the error budget is being consumed at the expected rate.
- More than 1x means the budget is being consumed too quickly.
- 14.4x or greater is treated as a fast-burn condition.

## Multi-Window Alert

OpsPilotAvailabilityFastBurn requires both:

- 5-minute burn rate > 14.4x
- 1-hour burn rate > 14.4x

The condition must persist for 2 minutes before firing.

## Validation

A controlled PostgreSQL failure was introduced in staging.

Observed during testing:

- Availability SLI: approximately 96.67%
- Error rate: approximately 3.33%
- Initial availability burn rate: approximately 33.33x
- 5-minute burn rate during sustained failure: approximately 256.41x
- 1-hour burn rate during sustained failure: approximately 40.68x

Alert lifecycle observed:

inactive -> pending -> firing -> resolved -> inactive

The critical fast-burn alert was delivered through Alertmanager to the OpsPilot Slack alert channel.

After PostgreSQL recovery and the short reliability window cleared, the alert automatically resolved.

## Operational Workflow

HTTP failures
-> Prometheus request metrics
-> SLI degradation
-> error-budget consumption
-> multi-window burn-rate detection
-> Alertmanager
-> Slack
-> engineer investigation
-> service recovery
-> resolved notification

This provides proactive reliability monitoring instead of relying only on individual HTTP error alerts.
