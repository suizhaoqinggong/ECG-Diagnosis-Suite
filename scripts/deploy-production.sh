#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.production"
ENV_EXAMPLE="$PROJECT_ROOT/.env.production.example"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"

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

mkdir -p \
  "$PROJECT_ROOT/data/uploads" \
  "$PROJECT_ROOT/data/reports" \
  "$PROJECT_ROOT/models/checkpoints" \
  "$PROJECT_ROOT/models/weights"

if [[ ! -f "$PROJECT_ROOT/models/checkpoints/best.ckpt" && ! -f "$PROJECT_ROOT/models/weights/best.ckpt" ]]; then
  echo "Warning: no model checkpoint found under models/checkpoints or models/weights."
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
