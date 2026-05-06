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
  echo "No .env.production found. Auto-generating with sensible defaults..."

  DETECTED_IP=""
  if command -v curl >/dev/null 2>&1; then
    DETECTED_IP="$(curl -s --connect-timeout 5 ifconfig.me 2>/dev/null || true)"
  fi
  DOMAIN="${DETECTED_IP:-localhost}"

  cat > "$ENV_FILE" <<EOF
APP_DOMAIN=${DOMAIN}
CLIENT_MAX_BODY_SIZE=20m
ENABLE_TLS=False
TLS_CERT_FILENAME=
TLS_KEY_FILENAME=
BACKEND_DEBUG=False
BACKEND_SECRET_KEY=$(openssl rand -hex 32)
BACKEND_API_DOCS_ENABLED=True
BACKEND_DEVICE=cpu
BACKEND_CONFIDENCE_THRESHOLD=0.7
BACKEND_MODEL_CHECKPOINT_PATH=models/checkpoints/best.ckpt
BACKEND_MODEL_TEMPERATURE=0.5
BACKEND_MODEL_NORMAL_BIAS=1.8
BACKEND_CORS_ORIGINS='["*"]'
BACKEND_ALLOWED_HOSTS='["*"]'
BACKEND_LLM_REPORT_ENABLED=False
BACKEND_LLM_REPORT_PROVIDER=openai
BACKEND_OPENAI_API_KEY=
BACKEND_OPENAI_BASE_URL=https://api.openai.com/v1
BACKEND_OPENAI_REPORT_MODEL=gpt-4o-mini
BACKEND_OPENAI_TIMEOUT_SECONDS=30
MYSQL_DATABASE=ecg_db
MYSQL_USER=ecg
MYSQL_PASSWORD=$(openssl rand -hex 16)
MYSQL_ROOT_PASSWORD=$(openssl rand -hex 16)
EOF

  echo "Generated $ENV_FILE with auto-secrets."
  echo "Review it later for production hardening."

  FRESH_ENV=true
  echo ""
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
  echo "WARNING: No model checkpoint found."
  echo "  Place best.ckpt under models/checkpoints/ or models/weights/"
  echo "  Or set BACKEND_MODEL_CHECKPOINT_PATH in .env.production"
  echo ""
fi

if [[ "${FRESH_ENV:-false}" == "true" ]]; then
  echo "New config detected — cleaning any stale database volume..."
  docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
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

echo "Waiting for backend to become healthy..."
for _ in {1..60}; do
  backend_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' ecg-backend 2>/dev/null || true)"
  if [[ "$backend_status" == "healthy" ]]; then
    echo "Backend is healthy."
    break
  fi
  sleep 3
done

echo ""
echo "===== Deployment Complete ====="
echo ""
"${COMPOSE[@]}" ps
echo ""
if [[ "${BACKEND_API_DOCS_ENABLED:-False}" == "True" ]]; then
  echo "API docs: http://${APP_DOMAIN:-localhost}/api/docs"
fi
echo "Health check: curl http://${APP_DOMAIN:-localhost}/api/health"
