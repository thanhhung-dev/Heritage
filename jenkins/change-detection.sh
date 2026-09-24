#!/usr/bin/env bash
set -Eeuo pipefail

base=${1:?usage: change-detection.sh BASE [HEAD]}
head=${2:-HEAD}
git rev-parse --verify "$base" >/dev/null
git rev-parse --verify "$head" >/dev/null
files=$(git diff --name-only "$base" "$head")

matches() { grep -Eq "$1" <<<"$files"; }
backend=false; frontend=false; migration=false; iac=false; ci=false
matches '^(apps/backend/|corpus/|alembic\.ini$|jenkins/requirements-ci\.txt$)' && backend=true
matches '^apps/frontend/' && frontend=true
matches '^(apps/backend/migrations/|alembic\.ini$)' && migration=true
matches '^infra/' && iac=true
matches '^(Jenkinsfile(\.model)?|jenkins/)' && ci=true
$migration && backend=true
if $ci || matches '^docker-compose\.yml$'; then
  backend=true; frontend=true; migration=true
fi
printf 'BACKEND_CHANGED=%s\nFRONTEND_CHANGED=%s\nMIGRATION_CHANGED=%s\nIAC_CHANGED=%s\nCI_CHANGED=%s\n' \
  "$backend" "$frontend" "$migration" "$iac" "$ci"
