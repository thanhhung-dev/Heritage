#!/usr/bin/env bash
set -Eeuo pipefail

: "${AWS_REGION:?required}" "${GIT_COMMIT:?required}" "${ECR_REGISTRY:?required}" "${ECR_BACKEND_REPOSITORY:?required}" "${ECR_FRONTEND_REPOSITORY:?required}" "${STAGING_DEPLOY_DIR:?required}"
[[ $GIT_COMMIT =~ ^[0-9a-f]{40}$ ]] || { echo 'GIT_COMMIT must be a full SHA' >&2; exit 1; }
[[ $STAGING_DEPLOY_DIR =~ ^/[A-Za-z0-9._/-]+$ && $STAGING_DEPLOY_DIR != *'/../'* && $STAGING_DEPLOY_DIR != */.. ]] || { echo 'STAGING_DEPLOY_DIR must be a safe absolute path without traversal' >&2; exit 1; }
backend_digest=$(aws ecr describe-images --region "$AWS_REGION" --repository-name "$ECR_BACKEND_REPOSITORY" --image-ids "imageTag=$GIT_COMMIT" --query 'imageDetails[0].imageDigest' --output text)
frontend_digest=$(aws ecr describe-images --region "$AWS_REGION" --repository-name "$ECR_FRONTEND_REPOSITORY" --image-ids "imageTag=$GIT_COMMIT" --query 'imageDetails[0].imageDigest' --output text)
[[ $backend_digest == sha256:* && $frontend_digest == sha256:* ]] || { echo 'Release image digest is unavailable' >&2; exit 1; }
backend="$ECR_REGISTRY/$ECR_BACKEND_REPOSITORY@$backend_digest"
frontend="$ECR_REGISTRY/$ECR_FRONTEND_REPOSITORY@$frontend_digest"
cmd="cd '$STAGING_DEPLOY_DIR' && git fetch --prune origin && git checkout --detach '$GIT_COMMIT' && aws ecr get-login-password --region '$AWS_REGION' | docker login --username AWS --password-stdin '$ECR_REGISTRY' >/dev/null && export BACKEND_IMAGE='$backend' FRONTEND_IMAGE='$frontend' RELEASE_REVISION='$GIT_COMMIT' && docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml pull backend frontend migrate import-data && docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml up -d && test \"\$(docker inspect --format '{{.Config.Image}}' \"\$(docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml ps -q backend)\")\" = '$backend' && test \"\$(docker inspect --format '{{.Config.Image}}' \"\$(docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml ps -q frontend)\")\" = '$frontend'"
"$(dirname "$0")/ssm-command.sh" "$cmd"
