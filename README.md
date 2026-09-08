# OpsPilot

OpsPilot is a production-support and reliability engineering platform built as a real SaaS application with separate development, staging, and production environments.

This repository begins with the Phase 1 application foundation. Destructive reliability exercises will be added later and will run only in staging.

## Phase 1 stack

- FastAPI
- PostgreSQL
- Redis
- Background worker
- Nginx
- Docker Compose
- Alembic migrations
- JWT authentication
- Tenant-scoped support tickets
- Request IDs and structured JSON logs
- Health/readiness endpoints

## Start locally

```bash
cp .env.example .env
```

Replace `JWT_SECRET` in `.env` with a random secret, then run:

```bash
docker compose up --build -d
```

Verify:

```bash
./scripts/verify-environment.sh
```

API documentation is available at:

```text
http://localhost:8080/docs
```

## First workflow

1. Register an organization owner: `POST /api/v1/auth/register`
2. Login using the email as the OAuth2 `username`: `POST /api/v1/auth/token`
3. Use the returned bearer token.
4. Create/list/update tenant-scoped tickets under `/api/v1/tickets`.

## Engineering rule

Production will not be intentionally broken. Failure injection, blind incidents, load tests, destructive recovery drills, and bad-release simulations belong in staging.
