#!/usr/bin/env bash
set -euo pipefail

mode="${1:-local}"
base_url="${BASE_URL:-http://localhost:8000}"
grafana_url="${GRAFANA_URL:-http://127.0.0.1:3001}"
langfuse_url="${LANGFUSE_URL:-http://127.0.0.1:3003}"
cid="$(python -c 'import uuid; print(uuid.uuid4())')"
headers="$(mktemp)"
trap 'rm -f "$headers"' EXIT

grafana_auth=()
if [[ -n "${GRAFANA_TOKEN:-}" ]]; then
  grafana_auth=(-H "Authorization: Bearer $GRAFANA_TOKEN")
elif [[ -n "${GRAFANA_AUTH:-}" ]]; then
  grafana_auth=(-u "$GRAFANA_AUTH")
elif [[ "$mode" == "local" ]]; then
  grafana_auth=(-u "admin:admin")
fi

wait_for_signal() {
  local uid="$1" path="$2" parameter="$3" query="$4" marker="$5"
  local response
  for _ in {1..30}; do
    response="$(
      curl -fsS "${grafana_auth[@]}" -G \
        "$grafana_url/api/datasources/proxy/uid/$uid/$path" \
        --data-urlencode "$parameter=$query" 2>/dev/null || true
    )"
    if grep -q "$marker" <<<"$response"; then
      return 0
    fi
    sleep 2
  done
  echo "Không tìm thấy $uid signal cho correlation ID $cid" >&2
  return 1
}

wait_for_grafana() {
  for _ in {1..30}; do
    if curl -fsS "${grafana_auth[@]}" "$grafana_url/api/health" 2>/dev/null \
      | grep -q '"database"'; then
      return 0
    fi
    sleep 2
  done
  echo "Grafana chưa sẵn sàng" >&2
  return 1
}

curl -fsS -D "$headers" -o /dev/null -H "X-Correlation-ID: $cid" "$base_url/"
grep -qi "^x-correlation-id: $cid" "$headers"

if [[ "$mode" == "local" ]]; then
  if [[ "${LANGFUSE_ENABLED:-false}" == "true" ]]; then
    curl -fsS "$langfuse_url/api/public/health" >/dev/null
  fi
  docker compose exec -T prometheus wget -qO- http://backend:8000/internal/metrics | grep -q heritage_http_requests_total
  for service_port in \
    "otel-collector 4317" "prometheus 9090" "loki 3100" "tempo 3200" \
    "langfuse-worker 3030" "langfuse-postgres 5432" \
    "langfuse-clickhouse 8123" "langfuse-clickhouse 9000" \
    "langfuse-redis 6379" "langfuse-minio 9000"; do
    [[ "${LANGFUSE_ENABLED:-false}" == "true" || "$service" != langfuse-* ]] || continue
    read -r service port <<<"$service_port"
    if docker compose port "$service" "$port" 2>/dev/null | grep -q .; then
      echo "Telemetry backend unexpectedly published: $service:$port" >&2
      exit 1
    fi
  done
else
  [[ "${ALLOW_PUBLIC_TELEMETRY:-false}" == "true" ]] || ! curl -fsS "$base_url/internal/metrics" >/dev/null
fi

wait_for_grafana
wait_for_signal \
  loki "loki/api/v1/query_range" query \
  "{service=\"heritage-api\"} | json | correlation_id=\"$cid\"" "$cid"
wait_for_signal \
  tempo "api/search" q \
  "{ span.correlation.id = \"$cid\" }" '"traceID"'

echo "Observability smoke check passed ($mode, correlation=$cid)"
