#!/usr/bin/env bash
set -euo pipefail

echo "→ running database migrations"
alembic upgrade head || { echo "migrations failed"; exit 1; }

if [ "${DEMO_MODE:-false}" = "true" ]; then
  if [ -f /app/scripts/seed_questions.py ]; then
    echo "→ seeding question bank (idempotent)"
    python /app/scripts/seed_questions.py --if-empty || echo "question seed skipped"
  fi
  if [ -f /app/scripts/seed_demo_data.py ]; then
    echo "→ seeding demo data (idempotent)"
    python /app/scripts/seed_demo_data.py --if-empty || echo "demo seed skipped"
  fi
fi

echo "→ starting PlaceMate API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
