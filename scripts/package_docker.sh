#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${MODEL:-$ROOT/models/qwen-fused.gguf}"
OUTPUT="${1:-$ROOT/heritagegraph-docker.tar.gz}"

if [[ ! -f "$MODEL" ]]; then
  echo "Thiếu $MODEL" >&2
  echo "Tạo trước bằng: python scripts/export_gguf.py --force" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
rm -f "$OUTPUT"
STAGING="$(mktemp -d "${TMPDIR:-/tmp}/heritagegraph-package.XXXXXX")"
APP="$STAGING/HeritageGraph"
trap 'rm -rf "$STAGING"' EXIT
mkdir -p "$APP/models"

COPYFILE_DISABLE=1 tar -cf - \
  --exclude='backend/.venv' \
  --exclude='backend/venv' \
  --exclude='backend/models/qwen2.5-7b' \
  --exclude='backend/models/*.safetensors' \
  --exclude='backend/**/__pycache__' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/.next' \
  --exclude='**/.DS_Store' \
  -C "$ROOT" \
  README.md \
  alembic.ini \
  docker-compose.yml \
  .dockerignore \
  .env.docker.example \
  backend \
  corpus \
  frontend \
  docs/docker-local.md \
  | tar -xf - -C "$APP"

cp "$MODEL" "$APP/models/qwen-fused.gguf"
DB_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
sed "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" \
  "$ROOT/.env.docker.example" > "$APP/.env"

COPYFILE_DISABLE=1 tar -czf "$OUTPUT" -C "$STAGING" HeritageGraph

echo "Đã tạo: $OUTPUT"
du -h "$OUTPUT"
echo "Gói đã có .env và model. Máy khách chỉ cần giải nén rồi chạy: docker compose up -d"
