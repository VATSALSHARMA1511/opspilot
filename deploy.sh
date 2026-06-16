#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# OpsPilot production deploy script
#
# 1. Brings up the prod stack (postgres, redis, backend, nginx)
# 2. Waits for the backend to report healthy
# 3. Runs Alembic migrations
# 4. Seeds the database only if it's currently empty
# =============================================================================

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Copy .env.example to .env and fill it in first."
    exit 1
fi

# Export vars from .env into this shell so we can use them below
# (e.g. POSTGRES_USER / POSTGRES_DB for the seed check).
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo ">> Building images..."
docker compose -f "$COMPOSE_FILE" build

echo ">> Starting stack (postgres, redis, backend, nginx)..."
docker compose -f "$COMPOSE_FILE" up -d

echo ">> Waiting for the backend to become healthy..."
ATTEMPTS=0
MAX_ATTEMPTS=30
until docker compose -f "$COMPOSE_FILE" exec -T backend curl -sf http://localhost:8000/health >/dev/null 2>&1; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
        echo "ERROR: backend did not become healthy in time."
        docker compose -f "$COMPOSE_FILE" logs backend
        exit 1
    fi
    sleep 2
done

echo ">> Running Alembic migrations..."
docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

echo ">> Checking whether the database needs seeding..."
TICKET_COUNT=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT COUNT(*) FROM tickets;" 2>/dev/null | tr -d '[:space:]')
TICKET_COUNT=${TICKET_COUNT:-0}

if [ "$TICKET_COUNT" -eq 0 ]; then
    echo ">> Database is empty. Running seed.py..."
    docker compose -f "$COMPOSE_FILE" exec -T backend python seed.py
else
    echo ">> Database already has $TICKET_COUNT ticket(s). Skipping seed."
fi

echo ">> Deployment complete."
docker compose -f "$COMPOSE_FILE" ps
