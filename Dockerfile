FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV SENTINEL_HOST=0.0.0.0
ENV SENTINEL_PORT=8000

RUN groupadd --system appgroup && useradd --system --gid appgroup appuser

EXPOSE 8000

USER appuser

CMD ["uvicorn", "hybrid_sentinel.main:app", "--host", "0.0.0.0", "--port", "8000"]
