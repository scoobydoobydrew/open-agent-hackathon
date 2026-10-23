#!/usr/bin/env bash
# Bring the local Zetaris stack up. After a Docker Desktop restart the `driver` container often fails with
# "error mounting .../spark-defaults.conf: not a directory" (exit 127); recreating that one container fixes it
# and keeps all data (it lives in volumes).
set -euo pipefail
DIR="${ZETARIS_DIR:-/c/Users/Master/Desktop/zetaris-platform}"
cd "$DIR"
docker compose up -d
if [ "$(docker inspect -f '{{.State.Status}}' zetaris-driver-1)" != "running" ]; then
  docker compose up -d --force-recreate --no-deps driver
fi
for i in $(seq 1 40); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' zetaris-driver-1)" = "healthy" ] && { echo "Zetaris is up"; exit 0; }
  sleep 5
done
echo "driver did not become healthy; see: docker logs zetaris-driver-1" >&2; exit 1
