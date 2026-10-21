#!/usr/bin/env bash
set -Eeuo pipefail

: "${AWS_REGION:?required}" "${ECR_REGISTRY:?required}" "${GIT_COMMIT:?required}" "${RELEASE_IMAGES:?required}"
[[ $GIT_COMMIT =~ ^[0-9a-f]{40}$ ]] || { echo 'GIT_COMMIT must be a full SHA' >&2; exit 1; }
trap 'docker logout "$ECR_REGISTRY" >/dev/null 2>&1 || true' EXIT
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY" >/dev/null
printf 'RELEASE_REVISION=%s\n' "$GIT_COMMIT" > release-images.env
IFS=, read -r -a images <<<"$RELEASE_IMAGES"
seen_images=,
for image in "${images[@]}"; do
  [[ $seen_images == *",$image,"* ]] && continue
  seen_images="$seen_images$image,"
  case "$image" in
    backend)
      : "${ECR_BACKEND_REPOSITORY:?required}"
      [[ -s corpus/locations_index.json ]] || { echo 'Release corpus index is missing' >&2; exit 1; }
      [[ -n $(find corpus/wiki_by_location -type f -name '*.txt' -print -quit) ]] || { echo 'Release corpus documents are missing' >&2; exit 1; }
      corpus_digest=$(cat corpus.sha256)
      [[ $corpus_digest =~ ^[0-9a-f]{64}$ ]] || { echo 'Corpus digest is missing or invalid' >&2; exit 1; }
      printf 'CORPUS_SHA256=%s\n' "$corpus_digest" >> release-images.env
      repository=$ECR_BACKEND_REPOSITORY; image_variable=BACKEND_IMAGE
      dockerfile=apps/backend/Dockerfile; context=.; build_args=''
      ;;
    frontend)
      : "${ECR_FRONTEND_REPOSITORY:?required}" "${STAGING_PUBLIC_API_URL:?required}"
      repository=$ECR_FRONTEND_REPOSITORY; image_variable=FRONTEND_IMAGE
      dockerfile=apps/frontend/Dockerfile; context=apps/frontend
      build_args="--build-arg NEXT_PUBLIC_API_URL=$STAGING_PUBLIC_API_URL"
      ;;
    *) echo "Unknown release image: $image" >&2; exit 1 ;;
  esac
  tagged="$ECR_REGISTRY/$repository:$GIT_COMMIT"
  if [[ -n $build_args ]]; then
    docker build --build-arg "NEXT_PUBLIC_API_URL=$STAGING_PUBLIC_API_URL" -f "$dockerfile" -t "$tagged" "$context"
  else
    docker build -f "$dockerfile" -t "$tagged" "$context"
  fi
  docker push "$tagged"
  digest=$(aws ecr describe-images --region "$AWS_REGION" --repository-name "$repository" --image-ids "imageTag=$GIT_COMMIT" --query 'imageDetails[0].imageDigest' --output text)
  [[ $digest == sha256:* ]] || { echo "ECR did not return an immutable digest for $image" >&2; exit 1; }
  printf '%s=%s/%s@%s\n' "$image_variable" "$ECR_REGISTRY" "$repository" "$digest" >> release-images.env
done
