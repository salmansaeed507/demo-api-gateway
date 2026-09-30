# api-gateway

API Gateway — single public backend entry point for demos.

## Responsibilities

- Route `/support/*` to backend services
- Session auth in Redis (TTL); demo data FKed to users in Postgres
- Cron job every 2 hours purges CSA data for users with no live Redis session
- CORS, request IDs, structured logging, basic rate limiting

## Setup

```bash
uv sync
make redis   # Redis on :6379
uv run alembic upgrade head
```

Optional env: `REDIS_URL` (default `redis://localhost:6379/0`), `DATABASE_URL`, `LOGIN_TOKEN`, `SESSION_IDLE_SECONDS`, `PURGE_INACTIVE_SESSIONS_CRON` (default `0 */2 * * *`; local often `* * * * *` for every minute).

S3 / RustFS (presigned uploads+downloads): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (default `us-east-1`), `S3_ENDPOINT_URL` (e.g. `http://localhost:9000`; omit for AWS), `S3_BUCKET`, `S3_KEY_PREFIX` (default empty; objects land under `{prefix}/tmp/…` then promote to `{prefix}/…`), `S3_PRESIGN_EXPIRES_SECONDS` (default `3600`).

Auth-gated endpoints:

- `POST /files/presign-upload` `{ "content_type", "filename?" }` → `{ key, upload_url, download_url, expires_in }` (key is always under staging `tmp/`)
- `POST /files/presign-download` `{ "key" }` → `{ key, download_url, expires_in }`

Frontend uploads/downloads directly to the presigned URLs (send the same `Content-Type` on PUT as used when requesting the upload URL). Product create/update in customer-support-agent promotes staging `imageUrl` keys to final keys; abandoned uploads stay in `tmp/` — expire that prefix with bucket lifecycle.

## Run locally

```bash
make dev
# uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 5070
```
