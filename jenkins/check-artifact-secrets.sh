#!/usr/bin/env bash
set -Eeuo pipefail

file=${1:?usage: check-artifact-secrets.sh FILE}
[[ -f $file ]] || { echo "Artifact does not exist: $file" >&2; exit 1; }

if grep -Ei '(AKIA[0-9A-Z]{16}|BEGIN ([A-Z0-9 ]+ )?PRIVATE KEY|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|(postgres(ql)?|mysql|mongodb(\+srv)?):\/\/[^[:space:]]+:[^[:space:]@]+@|(^|[^[:alnum:]_])(password|passwd|token|secret)[[:space:]]*[:=][[:space:]]*("[^"[:space:]]+"|[^[:space:],}]+))' "$file" | grep -Fiv '"<sensitive>"' >/dev/null; then
  echo "Potential secret found in artifact; refusing to archive $file" >&2
  exit 1
fi
