FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY common/ common/
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Flat `src/` + `common/` layout; run via PYTHONPATH instead of installing the project wheel.
ENV PYTHONPATH=/app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev --no-install-project --python 3.12 \
    && chown -R appuser:appuser /app

ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 5070

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5070"]
