#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
CMD="${1:-help}"

step() {
  echo "[$1] $2"
}

wait_docker() {
  step "docker" "checking if Docker daemon is running..."
  for i in $(seq 1 30); do
    if docker ps -q >/dev/null 2>&1; then
      return 0
    fi
    step "docker" "waiting for Docker daemon to initialize..."
    sleep 2
  done
  step "docker" "ERROR: Docker daemon is not running. Please start Docker and try again."
  exit 1
}

wait_backend() {
  step "backend" "waiting for http://localhost:8000..."
  for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
      step "backend" "ready"
      return 0
    fi
    sleep 1
  done
  step "backend" "ERROR: did not start in time. Check Docker logs with: ./run.sh logs"
  exit 1
}

up() {
  wait_docker
  step "docker" "starting postgres + backend + frontend..."
  docker compose -f "$COMPOSE_FILE" up -d
  wait_backend
  echo ""
  echo "  Frontend:  http://localhost:3000"
  echo "  Backend:   http://localhost:8000"
  echo "  API docs:  http://localhost:8000/docs"
  echo ""
  echo "  Logs:  ./run.sh logs"
  echo "  Stop:  ./run.sh down"
}

down() {
  step "docker" "stopping containers..."
  docker compose -f "$COMPOSE_FILE" down
  step "docker" "stopped"
}

case "$CMD" in
  up)       up ;;
  down)     down ;;
  restart)  down; up ;;
  logs)     docker compose -f "$COMPOSE_FILE" logs -f ;;
  status)   docker compose -f "$COMPOSE_FILE" ps ;;
  *)
    echo "Usage: ./run.sh [up|down|restart|logs|status]"
    echo ""
    echo "  up                  start everything (postgres, backend, frontend) inside Docker"
    echo "  down                stop everything"
    echo "  restart             down + up"
    echo "  logs                follow logs for all containers"
    echo "  status              show what's running"
    ;;
esac
