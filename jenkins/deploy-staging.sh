#!/usr/bin/env bash
set -Eeuo pipefail

: "${AWS_REGION:?required}" "${GIT_COMMIT:?required}" "${ECR_REGISTRY:?required}" "${STAGING_DEPLOY_DIR:?required}" "${DEPLOY_UNITS:?required}"
[[ $GIT_COMMIT =~ ^[0-9a-f]{40}$ ]] || { echo 'GIT_COMMIT must be a full SHA' >&2; exit 1; }
[[ $STAGING_DEPLOY_DIR =~ ^/[A-Za-z0-9._/-]+$ && $STAGING_DEPLOY_DIR != *'/../'* && $STAGING_DEPLOY_DIR != */.. ]] || { echo 'STAGING_DEPLOY_DIR must be a safe absolute path without traversal' >&2; exit 1; }
IFS=, read -r -a units <<<"$DEPLOY_UNITS"
exports="RELEASE_REVISION='$GIT_COMMIT'"
checks=""
operations=""
seen_units=,
for unit in "${units[@]}"; do
  [[ $seen_units == *",$unit,"* ]] && continue
  seen_units="$seen_units$unit,"
  case "$unit" in
    migrate|import-data|backend)
      : "${ECR_BACKEND_REPOSITORY:?required}"
      repository=$ECR_BACKEND_REPOSITORY; variable=BACKEND_IMAGE ;;
    frontend)
      : "${ECR_FRONTEND_REPOSITORY:?required}"
      repository=$ECR_FRONTEND_REPOSITORY; variable=FRONTEND_IMAGE ;;
    *) echo "Unknown deploy unit: $unit" >&2; exit 1 ;;
  esac
  digest=$(aws ecr describe-images --region "$AWS_REGION" --repository-name "$repository" --image-ids "imageTag=$GIT_COMMIT" --query 'imageDetails[0].imageDigest' --output text)
  [[ $digest == sha256:* ]] || { echo "Release image digest is unavailable for $unit" >&2; exit 1; }
  image="$ECR_REGISTRY/$repository@$digest"
  [[ $exports == *"$variable="* ]] || exports="$exports $variable='$image'"
  if [[ $unit == backend || $unit == frontend ]]; then
    checks="$checks && test \"\$(docker inspect --format '{{.Config.Image}}' \"\$(docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml ps -q '$unit')\")\" = '$image'"
  fi
  case "$unit" in
    migrate|import-data) operations="$operations && docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml run --rm --no-deps '$unit'" ;;
    backend|frontend) operations="$operations && docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml up -d --no-deps '$unit'" ;;
  esac
done
unit_args=${seen_units#,}
unit_args=${unit_args%,}
unit_args=${unit_args//,/ }
cmd="cd '$STAGING_DEPLOY_DIR' && git fetch --prune origin && git checkout --detach '$GIT_COMMIT' && aws ecr get-login-password --region '$AWS_REGION' | docker login --username AWS --password-stdin '$ECR_REGISTRY' >/dev/null && export $exports && docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml pull $unit_args$operations$checks"
"$(dirname "$0")/ssm-command.sh" "$cmd"
