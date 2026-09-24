# Jenkins delivery pipeline

## Controller and agent requirements

Use Jenkins Pipeline, Git, Credentials Binding, AWS Credentials, Workspace Cleanup and Docker Pipeline plugins. The Linux agent needs Git, Bash, Python 3.12, Docker with Compose v2, Node 20.19.3/npm 10.8.2, Terraform and AWS CLI v2. Configure multibranch discovery for pull requests and `main`.

The software pipeline runs only affected gates on pull requests. Non-PR builds run all software gates; only `main` may release. Every failed gate stops its branch of the pipeline and prevents release. Terraform changes under `infra/` are formatted, validated and planned only; review the redacted `infra/terraform-plan.json` artifact before applying outside this pipeline.

## Jenkins configuration contract

Define these non-secret global environment values: `AWS_REGION`, `ECR_REGISTRY`, `ECR_BACKEND_REPOSITORY`, `ECR_FRONTEND_REPOSITORY`, `CORPUS_S3_URI`, `STAGING_PUBLIC_API_URL`, `SSM_INSTANCE_ID`, `SSM_DOCUMENT_NAME`, `SSM_TIMEOUT_SECONDS`, `STAGING_DEPLOY_DIR`, `SMOKE_URL`, and `LAST_GOOD_PARAMETER`. `CORPUS_S3_URI` must identify a versioned, immutable release prefix; its computed digest is recorded in `release-images.env`. Values are deliberately absent from source. `SSM_DOCUMENT_NAME` must execute the supplied deployment command on the staging host. The host must have the repository checkout, Git, AWS CLI, Docker Compose, and runtime secrets supplied by its secret manager. The checkout may contain ignored runtime artifacts such as the GGUF model; Jenkins checks out the exact software revision without deleting those artifacts.

Create scoped AWS credentials named `heritage-staging-aws` with only read access to the release corpus prefix, ECR push/read, SSM command/status and read/write access to the single last-good Parameter Store key. Create read-only `heritage-terraform-plan-aws` credentials for Terraform planning. Create `heritage-model-aws` separately and configure `MODEL_SSM_DOCUMENT_NAME`. The staging EC2 runtime role is separate from all Jenkins roles and only needs ECR pull plus the application's runtime permissions. Enable immutable tags on both ECR repositories. Bind credentials only inside their stages. Never print environment variables or enable shell tracing.

## Model/prompt rollout

Create a separate multibranch or parameterized job using `Jenkinsfile.model`. Only `MODEL_DEPLOY_BRANCH` (default `main`) may use it; pull requests are rejected before credentials are bound. Configure `MODEL_APPROVERS` as a comma-separated Jenkins user/group allowlist and `MODEL_EVALUATOR` as a trusted absolute executable path on the agent. The evaluator receives revision, traffic percentage and output path, and must emit revision-bound JSON metrics. Set minimum quality/grounding thresholds such as `METRIC_MIN_QUALITY` and `METRIC_MIN_GROUNDING`, and maximum operational thresholds such as `METRIC_MAX_LATENCY_MS` and `METRIC_MAX_ERROR_RATE`. The job validates candidate metrics, deploys 10%, evaluates live 10% metrics, requires approval for 50%, evaluates live 50% metrics, and requires approval for 100%. Missing, non-finite, wrong-revision or wrong-traffic metrics fail without promotion.

## Rollback

After deploy verifies the running backend/frontend image digests and smoke succeeds, the pipeline writes the full Git SHA to the configured last-good parameter. A failed/partial deployment command attempts rollback immediately. A smoke failure also deploys a distinct last-good SHA through SSM, smoke-checks it, and still exits unsuccessfully. If automatic rollback fails, create a parameterized Jenkins recovery job that checks out this repository, binds `heritage-staging-aws`, exports the non-secret variables listed above, sets `GIT_COMMIT` to the selected known-good full SHA, and invokes `jenkins/deploy-staging.sh`. Never run the script from an uncredentialed shell and never substitute `latest` for a revision.

## Current adoption blockers

The pipeline intentionally does not suppress existing application failures. At the time it was added, backend Ruff and mypy report existing source issues. The test suite also has pre-existing collection failures from obsolete import/config paths; corpus-dependent tests need the external corpus; and one Docker Compose regression test disagrees with the current published database port. Until those application-owned failures are fixed, Jenkins correctly rejects backend builds and does not deploy them.
