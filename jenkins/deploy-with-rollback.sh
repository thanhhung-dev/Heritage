#!/usr/bin/env bash
set -Eeuo pipefail

: "${GIT_COMMIT:?required}" "${AWS_REGION:?required}" "${LAST_GOOD_PARAMETER:?required}"
failed_revision=$GIT_COMMIT
if "$(dirname "$0")/deploy-staging.sh"; then
  exit 0
fi

echo 'Deployment command failed; attempting rollback' >&2
IFS=, read -r -a units <<<"${DEPLOY_UNITS:?required}"
seen=,
for unit in "${units[@]}"; do
  [[ $unit == frontend ]] || unit=backend
  [[ $seen == *",$unit,"* ]] && continue
  seen="$seen$unit,"
  last_good=$(aws ssm get-parameter --region "$AWS_REGION" --name "$LAST_GOOD_PARAMETER/$unit" --query 'Parameter.Value' --output text 2>/dev/null || aws ssm get-parameter --region "$AWS_REGION" --name "$LAST_GOOD_PARAMETER" --query 'Parameter.Value' --output text 2>/dev/null || true)
  if [[ $last_good == "$failed_revision" ]]; then
    echo "Last-good $unit revision equals the failed revision; rollback skipped" >&2
  elif [[ $last_good =~ ^[0-9a-f]{40}$ ]]; then
    GIT_COMMIT=$last_good DEPLOY_UNITS=$unit "$(dirname "$0")/deploy-staging.sh" || echo "Rollback of $unit after deployment failure also failed" >&2
  else
    echo "No valid last-good revision exists for $unit; rollback skipped" >&2
  fi
done
exit 1
