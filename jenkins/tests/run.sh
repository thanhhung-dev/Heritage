#!/usr/bin/env bash
set -Eeuo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cd "$root"
python3 -m unittest discover -s jenkins/tests -p 'test_*.py'
cd - >/dev/null

if CHANGE_ID=42 BRANCH_NAME=main GIT_COMMIT=$(printf a%.0s {1..40}) "$root/jenkins/guard-release.sh" deploy 2>/dev/null; then exit 1; fi
BRANCH_NAME=main GIT_COMMIT=$(printf a%.0s {1..40}) "$root/jenkins/guard-release.sh" deploy
if CHANGE_ID=42 BRANCH_NAME=PR-42 GIT_COMMIT=$(printf a%.0s {1..40}) "$root/jenkins/guard-release.sh" model 2>/dev/null; then exit 1; fi
BRANCH_NAME=main GIT_COMMIT=$(printf a%.0s {1..40}) "$root/jenkins/guard-release.sh" model
if MODEL_LEVEL=50 METRIC_GATE_PASSED=false MANUAL_APPROVED=true "$root/jenkins/guard-release.sh" promote 2>/dev/null; then exit 1; fi
if MODEL_LEVEL=50 METRIC_GATE_PASSED=true MANUAL_APPROVED=false "$root/jenkins/guard-release.sh" promote 2>/dev/null; then exit 1; fi
MODEL_LEVEL=10 METRIC_GATE_PASSED=true "$root/jenkins/guard-release.sh" promote
MODEL_LEVEL=50 METRIC_GATE_PASSED=true MANUAL_APPROVED=true "$root/jenkins/guard-release.sh" promote

cat >"$tmp/metrics.json" <<'EOF'
{"revision": "model-v1", "traffic_percent": 10, "quality": 0.91, "grounding": 0.88, "latency_ms": 420, "error_rate": 0.01}
EOF
METRIC_MIN_QUALITY=0.9 METRIC_MIN_GROUNDING=0.8 METRIC_MAX_LATENCY_MS=500 METRIC_MAX_ERROR_RATE=0.02 python3 "$root/jenkins/metric-gate.py" "$tmp/metrics.json" model-v1 10 >/dev/null
if METRIC_MIN_QUALITY=0.95 python3 "$root/jenkins/metric-gate.py" "$tmp/metrics.json" 2>/dev/null; then exit 1; fi
if METRIC_MAX_LATENCY_MS=400 python3 "$root/jenkins/metric-gate.py" "$tmp/metrics.json" 2>/dev/null; then exit 1; fi
if METRIC_MIN_QUALITY=0.9 python3 "$root/jenkins/metric-gate.py" "$tmp/metrics.json" model-v2 2>/dev/null; then exit 1; fi
printf '{"quality": NaN}\n' >"$tmp/non-finite.json"
if METRIC_MIN_QUALITY=0 python3 "$root/jenkins/metric-gate.py" "$tmp/non-finite.json" 2>/dev/null; then exit 1; fi

cat >"$tmp/terraform.raw.json" <<'EOF'
{"variables":{"db_password":{"value":"hidden"}},"planned_values":{"root_module":{"resources":[{"values":{"name":"public","password":"hidden"},"sensitive_values":{"password":true}}]}}}
EOF
python3 "$root/jenkins/redact-terraform-plan.py" "$tmp/terraform.raw.json" "$tmp/terraform.json"
! grep -q 'hidden' "$tmp/terraform.json"
grep -q '<sensitive>' "$tmp/terraform.json"

printf 'resource "x" "safe" {}\n' >"$tmp/safe-plan.txt"
"$root/jenkins/check-artifact-secrets.sh" "$tmp/safe-plan.txt"
printf 'DATABASE_URL = "postgresql://user:credential@example.invalid/db"\n' >"$tmp/unsafe-plan.txt"
if "$root/jenkins/check-artifact-secrets.sh" "$tmp/unsafe-plan.txt" 2>/dev/null; then exit 1; fi

approve_50=$(grep -n "stage('Approve 50%')" "$root/Jenkinsfile.model" | cut -d: -f1)
deploy_50=$(grep -n "stage('Deploy 50%')" "$root/Jenkinsfile.model" | cut -d: -f1)
approve_100=$(grep -n "stage('Approve 100%')" "$root/Jenkinsfile.model" | cut -d: -f1)
deploy_100=$(grep -n "stage('Deploy 100%')" "$root/Jenkinsfile.model" | cut -d: -f1)
(( approve_50 < deploy_50 && approve_100 < deploy_100 ))
grep -q 'submitter: env.MODEL_APPROVERS' "$root/Jenkinsfile.model"
evaluate_10=$(grep -n "stage('Evaluate 10% canary')" "$root/Jenkinsfile.model" | cut -d: -f1)
evaluate_50=$(grep -n "stage('Evaluate 50% canary')" "$root/Jenkinsfile.model" | cut -d: -f1)
(( evaluate_10 < approve_50 && evaluate_50 < approve_100 ))

cat >"$tmp/model-evaluator" <<'EOF'
#!/usr/bin/env bash
printf '{"revision":"%s","traffic_percent":%s,"quality":0.9}\n' "$1" "$2" >"$3"
EOF
chmod +x "$tmp/model-evaluator"
(cd "$tmp" && MODEL_REVISION=model-v1 MODEL_EVALUATOR="$tmp/model-evaluator" "$root/jenkins/evaluate-model-rollout.sh" 10 reports/model-10.json)
METRIC_MIN_QUALITY=0.8 python3 "$root/jenkins/metric-gate.py" "$tmp/reports/model-10.json" model-v1 10 >/dev/null

mkdir "$tmp/bin"
cat >"$tmp/bin/curl" <<'EOF'
#!/usr/bin/env bash
count=0
[[ -f ${MOCK_CURL_COUNT:?} ]] && read -r count <"$MOCK_CURL_COUNT"
count=$((count + 1)); printf '%s\n' "$count" >"$MOCK_CURL_COUNT"
if (( count == 1 )); then exit "${MOCK_FIRST_CURL_EXIT:-0}"; fi
exit "${MOCK_SECOND_CURL_EXIT:-0}"
EOF
cat >"$tmp/bin/aws" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$MOCK_AWS_LOG"
[[ $* == *'get-parameter'* ]] && printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n'
[[ $* == *'describe-images'* ]] && printf 'sha256:%064d\n' 0
[[ $* == *'send-command'* ]] && printf 'command-id\n'
[[ $* == *'get-command-invocation'* ]] && printf 'Success\n'
exit 0
EOF
cat >"$tmp/bin/docker" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$MOCK_DOCKER_LOG"
[[ ${1:-} == login ]] && cat >/dev/null
exit 0
EOF
chmod +x "$tmp/bin/curl" "$tmp/bin/aws" "$tmp/bin/docker"

mkdir -p "$tmp/corpus/wiki_by_location"
mkdir -p "$tmp/apps/backend" "$tmp/apps/frontend"
printf '{}\n' >"$tmp/corpus/locations_index.json"
printf 'document\n' >"$tmp/corpus/wiki_by_location/sample.txt"
printf '%064d\n' 1 >"$tmp/corpus.sha256"
touch "$tmp/apps/backend/Dockerfile" "$tmp/apps/frontend/Dockerfile"
: >"$tmp/aws.log"; : >"$tmp/docker.log"
(cd "$tmp" && env AWS_REGION=test ECR_REGISTRY=example.invalid ECR_FRONTEND_REPOSITORY=frontend RELEASE_IMAGES=frontend GIT_COMMIT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb STAGING_PUBLIC_API_URL=https://api.example.invalid MOCK_AWS_LOG="$tmp/aws.log" MOCK_DOCKER_LOG="$tmp/docker.log" PATH="$tmp/bin:$PATH" "$root/jenkins/ecr-build-push.sh")
! grep -q 'backend:' "$tmp/docker.log"
grep -q 'frontend:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' "$tmp/docker.log"
grep -q 'FRONTEND_IMAGE=example.invalid/frontend@sha256:' "$tmp/release-images.env"

: >"$tmp/aws.log"; : >"$tmp/docker.log"
(cd "$tmp" && env AWS_REGION=test ECR_REGISTRY=example.invalid ECR_FRONTEND_REPOSITORY=frontend RELEASE_IMAGES=frontend,frontend GIT_COMMIT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb STAGING_PUBLIC_API_URL=https://api.example.invalid MOCK_AWS_LOG="$tmp/aws.log" MOCK_DOCKER_LOG="$tmp/docker.log" PATH="$tmp/bin:$PATH" "$root/jenkins/ecr-build-push.sh")
[[ $(grep -c '^build .*frontend:' "$tmp/docker.log") == 1 ]]

: >"$tmp/aws.log"; : >"$tmp/docker.log"
(cd "$tmp" && env AWS_REGION=test ECR_REGISTRY=example.invalid ECR_BACKEND_REPOSITORY=backend RELEASE_IMAGES=backend GIT_COMMIT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb MOCK_AWS_LOG="$tmp/aws.log" MOCK_DOCKER_LOG="$tmp/docker.log" PATH="$tmp/bin:$PATH" "$root/jenkins/ecr-build-push.sh")
grep -q 'backend:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' "$tmp/docker.log"
! grep -q 'frontend:' "$tmp/docker.log"
grep -q 'BACKEND_IMAGE=example.invalid/backend@sha256:' "$tmp/release-images.env"
grep -q 'CORPUS_SHA256=' "$tmp/release-images.env"

: >"$tmp/aws.log"
(cd "$tmp" && env AWS_REGION=test ECR_REGISTRY=example.invalid ECR_FRONTEND_REPOSITORY=frontend DEPLOY_UNITS=frontend GIT_COMMIT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb STAGING_DEPLOY_DIR=/srv/heritage SSM_INSTANCE_ID=i-test SSM_DOCUMENT_NAME=deploy MOCK_AWS_LOG="$tmp/aws.log" PATH="$tmp/bin:$PATH" "$root/jenkins/deploy-staging.sh")
grep -q 'up -d --no-deps.*frontend' "$tmp/aws.log"
! grep -q 'up -d --no-deps.*backend' "$tmp/aws.log"
grep -q 'docker inspect --format' "$tmp/aws.log"
grep -q 'frontend@sha256:' "$tmp/aws.log"

: >"$tmp/aws.log"
(cd "$tmp" && env AWS_REGION=test ECR_REGISTRY=example.invalid ECR_FRONTEND_REPOSITORY=frontend DEPLOY_UNITS=frontend,frontend GIT_COMMIT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb STAGING_DEPLOY_DIR=/srv/heritage SSM_INSTANCE_ID=i-test SSM_DOCUMENT_NAME=deploy MOCK_AWS_LOG="$tmp/aws.log" PATH="$tmp/bin:$PATH" "$root/jenkins/deploy-staging.sh")
[[ $(grep -o 'up -d --no-deps.*frontend' "$tmp/aws.log" | wc -l | tr -d ' ') == 1 ]]

grep -q "CI_PROFILE_CONTRACTS == 'true'" "$root/Jenkinsfile"
grep -q "CI_PROFILE_FRONTEND == 'true'" "$root/Jenkinsfile"
grep -q "CI_PROFILE_BACKEND == 'true'" "$root/Jenkinsfile"
grep -q "CI_PROFILE_MIGRATION == 'true'" "$root/Jenkinsfile"
grep -q "HAS_RELEASE == 'true'" "$root/Jenkinsfile"
for assignment in \
  'env.CI_PROFILE_CONTRACTS = line.substring(21)' \
  'env.CI_PROFILE_BACKEND = line.substring(19)' \
  'env.CI_PROFILE_FRONTEND = line.substring(20)' \
  'env.CI_PROFILE_MIGRATION = line.substring(21)' \
  'env.CI_PROFILE_INFRASTRUCTURE = line.substring(26)' \
  'env.CI_PROFILE_DATA_PIPELINE = line.substring(25)' \
  'env.CI_PROFILE_MODEL_CONTRACT = line.substring(26)' \
  'env.RELEASE_IMAGES = line.substring(15)' \
  'env.DEPLOY_UNITS = line.substring(13)' \
  'env.HAS_RELEASE = line.substring(12)'; do
  grep -Fq "$assignment" "$root/Jenkinsfile"
done
! grep -Eq 'env[[:space:]]*\[[^=;]+\][[:space:]]*=' "$root/Jenkinsfile"
grep -q 'git rev-parse HEAD~1 2>/dev/null || git hash-object -t tree /dev/null' "$root/Jenkinsfile"

common=(AWS_REGION=test LAST_GOOD_PARAMETER=/test/last-good DEPLOY_UNITS=backend GIT_COMMIT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb SMOKE_URL=https://example.invalid/health MOCK_AWS_LOG="$tmp/aws.log" MOCK_CURL_COUNT="$tmp/curl.count" PATH="$tmp/bin:$PATH")
: >"$tmp/aws.log"; rm -f "$tmp/curl.count"
env "${common[@]}" "$root/jenkins/smoke-and-rollback.sh"
grep -q 'put-parameter.*--name /test/last-good/backend.*bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' "$tmp/aws.log"
: >"$tmp/aws.log"; rm -f "$tmp/curl.count"
if env "${common[@]}" MOCK_FIRST_CURL_EXIT=1 MOCK_SECOND_CURL_EXIT=0 ECR_REGISTRY=example.invalid ECR_BACKEND_REPOSITORY=backend DEPLOY_UNITS=backend STAGING_DEPLOY_DIR=/srv/heritage SSM_INSTANCE_ID=i-test SSM_DOCUMENT_NAME=deploy "$root/jenkins/smoke-and-rollback.sh" 2>/dev/null; then exit 1; fi
grep -q 'send-command' "$tmp/aws.log"
grep -q 'git checkout --detach.*aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' "$tmp/aws.log"
[[ $(cat "$tmp/curl.count") == 2 ]]

: >"$tmp/aws.log"; rm -f "$tmp/curl.count"
if env "${common[@]}" DEPLOY_UNITS=migrate,import-data,backend MOCK_FIRST_CURL_EXIT=1 MOCK_SECOND_CURL_EXIT=0 ECR_REGISTRY=example.invalid ECR_BACKEND_REPOSITORY=backend STAGING_DEPLOY_DIR=/srv/heritage SSM_INSTANCE_ID=i-test SSM_DOCUMENT_NAME=deploy "$root/jenkins/smoke-and-rollback.sh" 2>/dev/null; then exit 1; fi
grep -q 'up -d --no-deps.*backend' "$tmp/aws.log"
! grep -q 'run --rm --no-deps.*migrate' "$tmp/aws.log"
! grep -q 'run --rm --no-deps.*import-data' "$tmp/aws.log"
echo 'Jenkins safety tests passed'
