#!/usr/bin/env bash
set -Eeuo pipefail

level=${1:?usage: evaluate-model-rollout.sh LEVEL OUTPUT}
output=${2:?usage: evaluate-model-rollout.sh LEVEL OUTPUT}
: "${MODEL_REVISION:?required}" "${MODEL_EVALUATOR:?required}"
[[ $level =~ ^(10|50)$ ]] || { echo 'Canary traffic level must be 10 or 50' >&2; exit 1; }
[[ $MODEL_EVALUATOR =~ ^/[A-Za-z0-9._/-]+$ && $MODEL_EVALUATOR != *'/../'* && $MODEL_EVALUATOR != */.. ]] || { echo 'MODEL_EVALUATOR must be a safe absolute path' >&2; exit 1; }
[[ -x $MODEL_EVALUATOR ]] || { echo 'MODEL_EVALUATOR is not executable' >&2; exit 1; }
mkdir -p "$(dirname "$output")"
"$MODEL_EVALUATOR" "$MODEL_REVISION" "$level" "$output"
[[ -s $output ]] || { echo 'Model evaluator did not create a metric report' >&2; exit 1; }
