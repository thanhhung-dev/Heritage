#!/usr/bin/env bash
set -Eeuo pipefail

: "${SMOKE_URL:?required}" "${LAST_GOOD_PARAMETER:?required}" "${GIT_COMMIT:?required}" "${AWS_REGION:?required}"
if curl --fail --silent --show-error --retry 5 --retry-delay 3 --max-time 10 "$SMOKE_URL" >/dev/null; then
  IFS=, read -r -a units <<<"${DEPLOY_UNITS:?required}"
  seen=,
  for unit in "${units[@]}"; do
    [[ $unit == frontend ]] || unit=backend
    [[ $seen == *",$unit,"* ]] && continue
    seen="$seen$unit,"
    aws ssm put-parameter --region "$AWS_REGION" --name "$LAST_GOOD_PARAMETER/$unit" --type String --value "$GIT_COMMIT" --overwrite >/dev/null
  done
  exit 0
fi
echo 'Smoke check failed; attempting rollback' >&2
IFS=, read -r -a units <<<"${DEPLOY_UNITS:?required}"
seen=,
rolled_back=false
for unit in "${units[@]}"; do
  [[ $unit == frontend ]] || unit=backend
  [[ $seen == *",$unit,"* ]] && continue
  seen="$seen$unit,"
  last_good=$(aws ssm get-parameter --region "$AWS_REGION" --name "$LAST_GOOD_PARAMETER/$unit" --query 'Parameter.Value' --output text 2>/dev/null || aws ssm get-parameter --region "$AWS_REGION" --name "$LAST_GOOD_PARAMETER" --query 'Parameter.Value' --output text 2>/dev/null || true)
  if [[ $last_good == "$GIT_COMMIT" ]]; then
    echo "Last-good $unit revision equals the failed revision; refusing a no-op rollback" >&2
  elif [[ $last_good =~ ^[0-9a-f]{40}$ ]]; then
    GIT_COMMIT=$last_good DEPLOY_UNITS=$unit "$(dirname "$0")/deploy-staging.sh" && rolled_back=true || echo "Rollback of $unit failed" >&2
  else
    echo "No valid last-good revision exists for $unit; rollback skipped" >&2
  fi
done
if $rolled_back && curl --fail --silent --show-error --retry 5 --retry-delay 3 --max-time 10 "$SMOKE_URL" >/dev/null; then
  echo 'Rolled back selected services to their last-good revisions' >&2
elif $rolled_back; then
  echo 'Rollback completed but its smoke check failed' >&2
fi
exit 1
