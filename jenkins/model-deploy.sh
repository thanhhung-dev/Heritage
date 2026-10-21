#!/usr/bin/env bash
set -Eeuo pipefail
level=${1:?usage: model-deploy.sh LEVEL REVISION}
revision=${2:?usage: model-deploy.sh LEVEL REVISION}
: "${MODEL_SSM_DOCUMENT_NAME:?required}"
[[ $level =~ ^(10|50|100)$ ]] || { echo 'Traffic level must be 10, 50, or 100' >&2; exit 1; }
[[ $revision =~ ^[A-Za-z0-9._:-]+$ ]] || { echo 'Invalid immutable revision' >&2; exit 1; }
SSM_DOCUMENT_NAME=$MODEL_SSM_DOCUMENT_NAME "$(dirname "$0")/ssm-command.sh" "model-rollout --revision '$revision' --traffic '$level'"
