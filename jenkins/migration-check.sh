#!/usr/bin/env bash
set -Eeuo pipefail

tag=${BUILD_TAG:-local}
tag=${tag//[^A-Za-z0-9_.-]/-}
name="heritage-migration-${tag}-$$"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
if [[ -n ${MIGRATION_DB_PORT:-} ]]; then
  publish=(--publish "127.0.0.1:${MIGRATION_DB_PORT}:5432")
else
  publish=(--publish "127.0.0.1::5432")
fi
docker run -d --name "$name" -e POSTGRES_PASSWORD=ci -e POSTGRES_DB=heritage_ci "${publish[@]}" postgres:16-alpine >/dev/null
port=$(docker port "$name" 5432/tcp | sed -E 's/.*:([0-9]+)$/\1/' | head -1)
[[ $port =~ ^[0-9]+$ ]] || { echo 'Could not determine migration database port' >&2; exit 1; }
for _ in {1..60}; do docker exec "$name" pg_isready -U postgres -d heritage_ci >/dev/null 2>&1 && break; sleep 1; done
docker exec "$name" pg_isready -U postgres -d heritage_ci >/dev/null
export DATABASE_URL="postgresql+psycopg://postgres:ci@127.0.0.1:${port}/heritage_ci"
alembic upgrade head
alembic downgrade base
alembic upgrade head
