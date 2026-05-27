#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.production"
EXAMPLE_FILE="$ROOT_DIR/.env.production.example"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"

usage() {
  cat <<'EOF'
Usage: scripts/prod_compose.sh <command>

Commands:
  init      Create .env.production from the example if it does not exist
  config    Render the production compose config
  build     Build production images
  up        Build and start the Caddy + frontend + backend stack
  down      Stop the production stack
  logs      Follow production stack logs
  backup    Run the SQLite online backup job
EOF
}

ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    cp "$EXAMPLE_FILE" "$ENV_FILE"
    cat >&2 <<EOF
Created $ENV_FILE from .env.production.example.
Edit it before starting production:
  - SECRET_KEY
  - INITIAL_ADMIN_PASSWORD
  - MARKET_SITE_ADDRESS
  - FRONTEND_BASE_URL
  - ALLOWED_HOSTS
  - EMAIL_DELIVERY_MODE / SMTP_* when email verification is enabled
EOF
    exit 1
  fi
}

guard_placeholders() {
  if grep -Eq 'change-me-with-openssl-rand-hex-32|change-me-before-first-start' "$ENV_FILE"; then
    cat >&2 <<EOF
$ENV_FILE still contains placeholder secrets.
Please update SECRET_KEY and INITIAL_ADMIN_PASSWORD before starting production.
EOF
    exit 1
  fi
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

command="${1:-}"
case "$command" in
  init)
    if [ -f "$ENV_FILE" ]; then
      echo "$ENV_FILE already exists."
    else
      cp "$EXAMPLE_FILE" "$ENV_FILE"
      echo "Created $ENV_FILE. Edit it before running up."
    fi
    ;;
  config)
    ensure_env
    compose config
    ;;
  build)
    ensure_env
    guard_placeholders
    compose build
    ;;
  up)
    ensure_env
    guard_placeholders
    compose up -d --build
    ;;
  down)
    ensure_env
    compose down
    ;;
  logs)
    ensure_env
    compose logs -f
    ;;
  backup)
    ensure_env
    compose run --rm backup
    ;;
  *)
    usage
    exit 2
    ;;
esac
