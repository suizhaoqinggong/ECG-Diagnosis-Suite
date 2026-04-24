#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.production"
ENV_EXAMPLE="$PROJECT_ROOT/.env.production.example"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
TLS_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.tls.yml"

compose_files=(-f "$COMPOSE_FILE")

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is required"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "Created $ENV_FILE from template."
  echo "Edit it first, then rerun this script."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

case "${ENABLE_TLS:-False}" in
  True|true|1)
    if [[ ! -f "$TLS_COMPOSE_FILE" ]]; then
      echo "Missing TLS compose override: $TLS_COMPOSE_FILE"
      exit 1
    fi
    echo "Built-in TLS enabled; loading $TLS_COMPOSE_FILE"
    compose_files+=(-f "$TLS_COMPOSE_FILE")
    ;;
esac

COMPOSE=(docker compose --env-file "$ENV_FILE" "${compose_files[@]}")

mkdir -p \
  "$PROJECT_ROOT/data/uploads" \
  "$PROJECT_ROOT/data/reports" \
  "$PROJECT_ROOT/models/checkpoints" \
  "$PROJECT_ROOT/models/weights" \
  "$PROJECT_ROOT/deploy/certs"

if [[ ! -f "$PROJECT_ROOT/models/checkpoints/best.ckpt" && ! -f "$PROJECT_ROOT/models/weights/best.ckpt" ]]; then
  echo "Warning: no model checkpoint found under models/checkpoints or models/weights."
fi

echo "Building application images..."
"${COMPOSE[@]}" build backend frontend

echo "Starting database..."
"${COMPOSE[@]}" up -d db

echo "Waiting for database healthcheck..."
# Wait up to 150s to match MySQL healthcheck: start_period(30s) + retries(10)*interval(10s) = 130s max
for _ in {1..75}; do
  db_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' ecg-db 2>/dev/null || true)"
  if [[ "$db_status" == "healthy" ]]; then
    break
  fi
  sleep 2
done

db_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' ecg-db 2>/dev/null || true)"
if [[ "$db_status" != "healthy" ]]; then
  echo "Database failed to become healthy. Current status: ${db_status:-unknown}"
  "${COMPOSE[@]}" logs db
  exit 1
fi

echo "Running database migrations..."
"${COMPOSE[@]}" run --rm --no-deps backend alembic upgrade head

echo "Starting application services..."
"${COMPOSE[@]}" up -d backend frontend reverse-proxy
"${COMPOSE[@]}" ps
