# OpsPilot

[![OpsPilot CI](https://github.com/dwaradwara/opspilot/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/dwaradwara/opspilot/actions/workflows/ci.yml)

OpsPilot is a production-support and reliability engineering platform built to simulate the architecture, security boundaries, observability, and operational workflows of a real multi-tenant SaaS system.

The project is designed as a hands-on environment for production-support engineering, incident investigation, reliability testing, and secure backend development.

## What OpsPilot Demonstrates

- Multi-tenant SaaS architecture
- JWT-based authentication
- Role-based access control
- Tenant data isolation
- PostgreSQL persistence
- Redis-backed background jobs
- FastAPI REST APIs
- Nginx reverse proxy
- Alembic database migrations
- Structured JSON logging
- Request correlation IDs
- Health and readiness endpoints
- Docker-based application environments
- Automated security testing
- GitHub Actions CI

## Architecture

```text
                    ┌─────────────────┐
                    │     Client      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │      Nginx      │
                    │ Reverse Proxy   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   FastAPI API   │
                    │ Auth / Tickets  │
                    │ Members / RBAC  │
                    └──────┬────┬─────┘
                           │    │
                 ┌─────────┘    └─────────┐
                 ▼                        ▼
        ┌─────────────────┐      ┌─────────────────┐
        │   PostgreSQL    │      │      Redis      │
        │ Users / Orgs /  │      │   Job Queue     │
        │     Tickets     │      └────────┬────────┘
        └─────────────────┘               │
                                          ▼
                                 ┌─────────────────┐
                                 │ Background      │
                                 │ Worker          │
                                 └─────────────────┘
```

## Security Model

Every user belongs to an organization.

Application queries are tenant-scoped using the authenticated user's `organization_id`, preventing users from accessing tickets belonging to another organization.

Current roles:

- `owner`
- `agent`
- `user`

Organization owners can create members.

Agents and regular users cannot create organization members.

The server assigns the organization automatically rather than trusting a client-supplied tenant identifier.

Security tests verify:

- Cross-tenant ticket access is blocked
- Cross-tenant ticket modification is blocked
- Organization owners can create members
- Agents cannot create members
- Newly created members remain inside the owner's organization

## Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Queue | Redis |
| Worker | Python background worker |
| Proxy | Nginx |
| Authentication | JWT / OAuth2 |
| Validation | Pydantic |
| Testing | Pytest |
| Containers | Docker Compose |
| CI | GitHub Actions |

## Local Development

Create the local environment file:

```bash
cp .env.example .env
```

Replace the example `JWT_SECRET` with a strong local secret.

Start the application:

```bash
docker compose up --build -d
```

Check container status:

```bash
docker compose ps
```

Health endpoint:

```text
http://localhost:8080/health
```

Interactive API documentation:

```text
http://localhost:8080/docs
```

## API Workflow

### 1. Register an organization owner

```text
POST /api/v1/auth/register
```

### 2. Authenticate

```text
POST /api/v1/auth/token
```

Use the email address as the OAuth2 `username`.

### 3. Create and manage tickets

```text
POST   /api/v1/tickets
GET    /api/v1/tickets
GET    /api/v1/tickets/{ticket_id}
PATCH  /api/v1/tickets/{ticket_id}
```

Ticket access is restricted to the authenticated user's organization.

### 4. Create organization members

```text
POST /api/v1/members
```

Only organization owners are authorized to use this endpoint.

## Isolated Test Environment

OpsPilot uses a dedicated Docker Compose environment for integration and security tests.

```bash
docker compose -f docker-compose.test.yml up \
  --build \
  --abort-on-container-exit \
  --exit-code-from api_test
```

The test environment uses isolated PostgreSQL and Redis services and is separate from the development environment.

Clean up after testing:

```bash
docker compose -f docker-compose.test.yml down -v
```

Current automated coverage includes:

```text
Health endpoint
Tenant isolation
Member role enforcement
```

## Continuous Integration

GitHub Actions runs the isolated Docker test environment automatically on:

- Pushes to `master`
- Pull requests targeting `master`

A change is considered healthy only when the test container exits successfully.

## Observability

OpsPilot currently includes:

- Structured JSON application logs
- HTTP request IDs
- Request duration tracking
- HTTP status logging
- Nginx access logging
- Upstream response information
- Health and readiness endpoints

These components provide the foundation for later incident investigation and reliability exercises.

## Reliability Engineering Rule

Production is never intentionally broken.

Failure injection, destructive recovery drills, load tests, bad-release simulations, dependency failures, and blind incident exercises belong in isolated staging environments.

## Project Status

### Completed

- Phase 1.1 — Core platform foundation
- Phase 1.2 — Tenant security and member role enforcement
- Phase 1.3 — Automated Docker CI pipeline

### Next

- Deeper observability
- Metrics and alerting
- Incident simulation
- Failure injection
- Recovery drills
- Operational runbooks
- Postmortem documentation

## Purpose

OpsPilot is not intended to be a simple CRUD demo.

The goal is to build and operate a realistic support and reliability environment where failures can be detected, investigated, explained, fixed, validated, and documented using production-style engineering practices.