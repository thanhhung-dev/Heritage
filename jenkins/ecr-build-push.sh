#!/usr/bin/env bash
set -Eeuo pipefail

: "${AWS_REGION:?required}" "${ECR_REGISTRY:?required}" "${ECR_BACKEND_REPOSITORY:?required}" "${ECR_FRONTEND_REPOSITORY:?required}" "${GIT_COMMIT:?required}" "${STAGING_PUBLIC_API_URL:?required}"
[[ $GIT_COMMIT =~ ^[0-9a-f]{40}$ ]] || { echo 'GIT_COMMIT must be a full SHA' >&2; exit 1; }
[[ -s corpus/locations_index.json ]] || { echo 'Release corpus index is missing' >&2; exit 1; }
[[ -n $(find corpus/wiki_by_location -type f -name '*.txt' -print -quit) ]] || { echo 'Release corpus documents are missing' >&2; exit 1; }
trap 'docker logout "$ECR_REGISTRY" >/dev/null 2>&1 || true' EXIT
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY" >/dev/null
backend_image="$ECR_REGISTRY/$ECR_BACKEND_REPOSITORY:$GIT_COMMIT"
frontend_image="$ECR_REGISTRY/$ECR_FRONTEND_REPOSITORY:$GIT_COMMIT"
docker build -f apps/backend/Dockerfile -t "$backend_image" .
docker build --build-arg "NEXT_PUBLIC_API_URL=$STAGING_PUBLIC_API_URL" -f apps/frontend/Dockerfile -t "$frontend_image" apps/frontend
docker push "$backend_image"
docker push "$frontend_image"
backend_digest=$(aws ecr describe-images --region "$AWS_REGION" --repository-name "$ECR_BACKEND_REPOSITORY" --image-ids "imageTag=$GIT_COMMIT" --query 'imageDetails[0].imageDigest' --output text)
frontend_digest=$(aws ecr describe-images --region "$AWS_REGION" --repository-name "$ECR_FRONTEND_REPOSITORY" --image-ids "imageTag=$GIT_COMMIT" --query 'imageDetails[0].imageDigest' --output text)
[[ $backend_digest == sha256:* && $frontend_digest == sha256:* ]] || { echo 'ECR did not return immutable image digests' >&2; exit 1; }
corpus_digest=$(cat corpus.sha256)
[[ $corpus_digest =~ ^[0-9a-f]{64}$ ]] || { echo 'Corpus digest is missing or invalid' >&2; exit 1; }
printf 'RELEASE_REVISION=%s\nCORPUS_SHA256=%s\nBACKEND_IMAGE=%s/%s@%s\nFRONTEND_IMAGE=%s/%s@%s\n' \
  "$GIT_COMMIT" "$corpus_digest" "$ECR_REGISTRY" "$ECR_BACKEND_REPOSITORY" "$backend_digest" \
  "$ECR_REGISTRY" "$ECR_FRONTEND_REPOSITORY" "$frontend_digest" > release-images.env
