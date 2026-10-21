#!/usr/bin/env bash
set -Eeuo pipefail

: "${AWS_REGION:?required}" "${SSM_INSTANCE_ID:?required}" "${SSM_DOCUMENT_NAME:?required}"
command=${1:?usage: ssm-command.sh COMMAND}
timeout=${SSM_TIMEOUT_SECONDS:-1800}
[[ $timeout =~ ^[1-9][0-9]*$ ]] || { echo 'SSM_TIMEOUT_SECONDS must be a positive integer' >&2; exit 1; }
parameters=$(python3 -c 'import json, sys; print(json.dumps({"commands": [sys.argv[1]]}))' "$command")
id=$(aws ssm send-command --region "$AWS_REGION" --instance-ids "$SSM_INSTANCE_ID" --document-name "$SSM_DOCUMENT_NAME" --parameters "$parameters" --query 'Command.CommandId' --output text)
deadline=$((SECONDS + timeout))
while (( SECONDS < deadline )); do
  status=$(aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$id" --instance-id "$SSM_INSTANCE_ID" --query 'Status' --output text 2>/dev/null || printf Pending)
  case "$status" in
    Success) exit 0 ;;
    Pending|InProgress|Delayed) sleep 5 ;;
    *)
      aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$id" --instance-id "$SSM_INSTANCE_ID" --query '{Status:Status,StandardError:StandardErrorContent,StandardOutput:StandardOutputContent}' --output json >&2 || true
      exit 1
      ;;
  esac
done
aws ssm cancel-command --region "$AWS_REGION" --command-id "$id" --instance-ids "$SSM_INSTANCE_ID" >/dev/null 2>&1 || true
echo "SSM command timed out after ${timeout}s and cancellation was requested" >&2
exit 1
