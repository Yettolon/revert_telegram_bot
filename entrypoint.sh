#!/bin/sh

set -e

echo "Applying migrations..."
uv run alembic upgrade head

echo "Starting bot..."
uv run python -m src.main