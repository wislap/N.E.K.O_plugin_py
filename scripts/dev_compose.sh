#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

usage() {
  cat <<'EOF'
Usage: scripts/dev_compose.sh <command>

Commands:
  config          Render the development compose config
  build           Build development images
  up              Build and start backend + frontend in the foreground
  up-d            Build and start backend + frontend in the background
  down            Stop the development stack
  logs [service]  Follow development logs
  ps              Show development containers
  restart         Restart development containers
  reset           Remove development volumes, then start fresh
  backend-shell   Open a shell in the backend container
  frontend-shell  Open a shell in the frontend container
EOF
}

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

command="${1:-}"
if [ "$#" -gt 0 ]; then
  shift
fi

case "$command" in
  config)
    compose config
    ;;
  build)
    compose build "$@"
    ;;
  up)
    compose up --build "$@"
    ;;
  up-d)
    compose up -d --build "$@"
    ;;
  down)
    compose down "$@"
    ;;
  logs)
    compose logs -f "$@"
    ;;
  ps)
    compose ps
    ;;
  restart)
    compose restart "$@"
    ;;
  reset)
    compose down -v
    compose up --build "$@"
    ;;
  backend-shell)
    compose exec backend sh
    ;;
  frontend-shell)
    compose exec frontend sh
    ;;
  *)
    usage
    exit 2
    ;;
esac
