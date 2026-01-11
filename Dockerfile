FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Копируем зависимости
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

# Копируем исходники
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY entrypoint.sh /entrypoint.sh
COPY alembic.ini ./

RUN chmod +x /entrypoint.sh
RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["/entrypoint.sh"]
