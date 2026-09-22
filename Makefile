dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 5070

migrate:
	uv run alembic upgrade head

redis:
	-docker rm -f api-gateway-redis
	docker run -d --name api-gateway-redis -p 6379:6379 redis:7-alpine
