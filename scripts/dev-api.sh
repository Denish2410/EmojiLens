#!/usr/bin/env bash
# Run database migrations, then start the API on 127.0.0.1:8000 with reload.
set -euo pipefail
cd "$(dirname "$0")/.."
export EMOJILENS_DATABASE_URL="${EMOJILENS_DATABASE_URL:-sqlite:///$(pwd)/var/emojilens.db}"
uv run alembic -c apps/api/alembic.ini upgrade head
exec uv run uvicorn emojilens_api.main:create_app --factory \
  --host 127.0.0.1 --port "${EMOJILENS_PORT:-8000}" ${EMOJILENS_RELOAD:+--reload}
