#!/usr/bin/env bash
set -Eeuo pipefail

action=${1:?usage: guard-release.sh deploy|model|promote}
case "$action" in
  deploy)
    [[ ${CHANGE_ID:-} == "" ]] || { echo 'Refusing deployment from a pull request' >&2; exit 1; }
    [[ ${BRANCH_NAME:-} == "${DEPLOY_BRANCH:-main}" ]] || { echo 'Branch is not permitted to deploy' >&2; exit 1; }
    [[ ${GIT_COMMIT:-} =~ ^[0-9a-f]{40}$ ]] || { echo 'GIT_COMMIT must be a full SHA' >&2; exit 1; }
    ;;
  model)
    [[ ${CHANGE_ID:-} == "" ]] || { echo 'Refusing model rollout from a pull request' >&2; exit 1; }
    [[ ${BRANCH_NAME:-} == "${MODEL_DEPLOY_BRANCH:-main}" ]] || { echo 'Branch is not permitted to roll out models' >&2; exit 1; }
    [[ ${GIT_COMMIT:-} =~ ^[0-9a-f]{40}$ ]] || { echo 'GIT_COMMIT must be a full SHA' >&2; exit 1; }
    ;;
  promote)
    [[ ${MODEL_LEVEL:-} =~ ^(10|50|100)$ ]] || { echo 'MODEL_LEVEL must be 10, 50, or 100' >&2; exit 1; }
    [[ ${METRIC_GATE_PASSED:-false} == true ]] || { echo 'Metric gate has not passed' >&2; exit 1; }
    [[ ${MODEL_LEVEL} == 10 || ${MANUAL_APPROVED:-false} == true ]] || { echo 'Manual approval is required' >&2; exit 1; }
    ;;
  *) echo "Unknown action: $action" >&2; exit 2 ;;
esac
