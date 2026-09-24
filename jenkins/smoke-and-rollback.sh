#!/usr/bin/env bash
set -Eeuo pipefail

: "${SMOKE_URL:?required}" "${LAST_GOOD_PARAMETER:?required}" "${GIT_COMMIT:?required}" "${AWS_REGION:?required}"
if curl --fail --silent --show-error --retry 5 --retry-delay 3 --max-time 10 "$SMOKE_URL" >/dev/null; then
  aws ssm put-parameter --region "$AWS_REGION" --name "$LAST_GOOD_PARAMETER" --type String --value "$GIT_COMMIT" --overwrite >/dev/null
  exit 0
fi
echo 'Smoke check failed; attempting rollback' >&2
last_good=$(aws ssm get-parameter --region "$AWS_REGION" --name "$LAST_GOOD_PARAMETER" --query 'Parameter.Value' --output text 2>/dev/null || true)
if [[ $last_good == "$GIT_COMMIT" ]]; then
  echo 'Last-good revision equals the failed revision; refusing a no-op rollback' >&2
elif [[ $last_good =~ ^[0-9a-f]{40}$ ]]; then
  if GIT_COMMIT=$last_good "$(dirname "$0")/deploy-staging.sh"; then
    if curl --fail --silent --show-error --retry 5 --retry-delay 3 --max-time 10 "$SMOKE_URL" >/dev/null; then
      echo "Rolled back to last-good revision $last_good" >&2
    else
      echo 'Rollback completed but its smoke check failed' >&2
    fi
  else
    echo 'Rollback also failed' >&2
  fi
else
  echo 'No valid last-good revision exists; rollback skipped' >&2
fi
exit 1
