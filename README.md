# api-gateway

API Gateway — single public backend entry point for demos.

## Responsibilities

- Route `/support/*` to backend services
- Session auth in Redis (TTL); demo data FKed to users in Postgres
- On Redis session expiry, app deletes users (and cascaded products/chats/orders) with no live Redis session
- CORS, request IDs, structured logging, basic rate limiting

## Setup

```bash
uv sync
make redis   # Redis on :6379 with keyspace expiry notifications (Ex)
uv run alembic upgrade head
```

Optional env: `REDIS_URL` (default `redis://localhost:6379/0`), `DATABASE_URL`, `LOGIN_TOKEN`, `SESSION_IDLE_SECONDS`.

## Run locally

```bash
make dev
# uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 5070
```
