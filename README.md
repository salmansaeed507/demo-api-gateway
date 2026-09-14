# api-gateway

API Gateway — single public backend entry point for demos.

## Responsibilities

- Route `/api/shoppilot-ai/*` and `/api/lead-qualification/*` to backend services
- API key authentication (`X-API-Key` header)
- CORS, request IDs, structured logging, basic rate limiting

## Setup

```bash
uv sync
uv run alembic upgrade head
```

## Run locally

```bash
make dev
# uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 5070
```