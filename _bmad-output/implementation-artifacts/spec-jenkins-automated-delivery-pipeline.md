---
title: 'Jenkins automated delivery pipeline'
type: 'feature'
created: '2026-09-24'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'adf05b7f486296a31f61a21d9c8aa0777d80c908'
context:
  - '{project-root}/docs/secrets-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Repository chưa có Jenkins pipeline nên pull request không có quality gate bắt buộc, migration chưa được thử trên database sạch, và release staging chưa có cơ chế gắn revision, smoke check hoặc rollback đáng tin cậy.

**Approach:** Tạo pipeline Jenkins khai báo bằng code để phát hiện component thay đổi, chạy gate có điều kiện, build/push image theo Git SHA và điều phối deploy staging qua AWS SSM; tách hoàn toàn model/prompt rollout thành pipeline có metric gate và manual approval riêng.

## Boundaries & Constraints

**Always:** Mỗi gate có stage riêng và lỗi phải dừng build; pull request chỉ chạy component liên quan; deploy chỉ chạy từ branch được phép sau mọi gate; image dùng full Git SHA; migration chạy upgrade–downgrade–upgrade trên PostgreSQL sạch; secret chỉ bind trong stage cần dùng và không xuất vào log/artifact; rollback thành công vẫn không được biến release lỗi thành SUCCESS.

**Never:** Không tạo hay apply Terraform/IAM, không hardcode AWS account/role/credential/URL, không tự động promote model 10% → 50% → 100%, không dùng `latest`, không sửa logic ứng dụng để làm xanh CI, và không deploy từ pull request.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR đổi backend | Diff chỉ thuộc backend | Chạy backend lint/type/test; stage frontend, migration và IaC hiển thị skipped | Gate lỗi làm build FAILED |
| PR đổi migration | Diff chứa Alembic revision | Chạy backend gate và migration upgrade–downgrade–upgrade trên PostgreSQL mới | Luôn dọn container; lỗi chặn build/deploy |
| Main đủ điều kiện | Mọi gate xanh và cấu hình deploy đầy đủ | Build hai image bằng full SHA, push ECR, deploy đúng SHA, smoke check | Chỉ ghi last-good sau smoke pass |
| Smoke lỗi | Revision mới không healthy | Rollback về last-good qua SSM và release vẫn FAILED | Nếu rollback cũng lỗi, báo cả hai lỗi và giữ FAILED |
| Model rollout | Metric chưa đạt hoặc chưa approve | Không chuyển traffic sang mức tiếp theo | Pipeline FAILED/ABORTED, không auto-promote |

</frozen-after-approval>

## Code Map

- `Jenkinsfile` -- pipeline phần mềm chính; repo hiện chưa có file này.
- `Jenkinsfile.model` -- pipeline rollout model/prompt độc lập.
- `jenkins/` -- script shell nhỏ, test được độc lập cho change detection, migration, ECR/deploy, smoke và rollback.
- `apps/backend/requirements.txt` -- dependency runtime hiện có; CI cần file dependency riêng cho Ruff, mypy và PyYAML thay vì cài phiên bản trôi nổi.
- `apps/backend/tests/` -- unittest hiện có; một số test phụ thuộc corpus không được commit và baseline hiện có một failure Compose, nên pipeline phải báo lỗi thật thay vì bỏ qua.
- `apps/frontend/package.json` -- đã có `lint`/`build` và TypeScript nhưng thiếu ESLint dependency/config, khiến lint hiện mở prompt tương tác.
- `apps/backend/migrations/` và `alembic.ini` -- migration có cả upgrade/downgrade; dùng PostgreSQL 16 tạm thời.
- `docker-compose.yml` -- đơn vị deploy đã chốt; cần override staging chỉ thay build bằng image ECR, không đổi local workflow.
- `docs/secrets-policy.md` -- nguồn quy tắc credential/log bắt buộc.

## Tasks & Acceptance

**Execution:**
- [x] `Jenkinsfile` -- thêm checkout, change detection, parallel quality gates, Terraform plan artifact, immutable build/push, branch guard, staging deploy, smoke và rollback.
- [x] `Jenkinsfile.model` -- thêm validate/evaluate/deploy 10/50/100 với metric gate và approval giữa các mức.
- [x] `jenkins/*.sh` -- tách hành vi có rủi ro khỏi Groovy, validate input, dùng `set -Eeuo pipefail`, không in secret và cleanup tài nguyên tạm.
- [x] `jenkins/docker-compose.staging.yml` -- ánh xạ service phần mềm sang image ECR theo revision mà không ảnh hưởng Compose local.
- [x] `jenkins/requirements-ci.txt`, `apps/frontend/package.json`, `.eslintrc.json` -- pin tooling để lint/type gates chạy non-interactive và tái lập được.
- [x] `docs/jenkins.md` -- ghi plugin/tool/credential IDs, branch policy, AWS contract, cách review Terraform plan và rollback thủ công.
- [x] `jenkins/tests/` -- kiểm tra change classification và các guard ngăn deploy/promote sai điều kiện.

**Acceptance Criteria:**
- Given diff của PR, when pipeline chạy, then chỉ gate component liên quan chạy và mọi gate bắt buộc có kết quả rõ ràng.
- Given migration thay đổi, when migration gate chạy, then clean database vượt qua upgrade–downgrade–upgrade trước mọi deploy.
- Given Terraform thay đổi, when IaC gate chạy, then fmt/validate/plan thành công và plan text được archive để review, không tự apply.
- Given branch deploy hợp lệ và mọi gate xanh, when release chạy, then ECR nhận image tag full SHA và staging chạy đúng revision đó.
- Given smoke thất bại, when rollback xử lý, then last-good được phục hồi nếu có và build vẫn FAILED.
- Given model/prompt rollout, when metric hoặc approval thiếu, then traffic không được tự động nâng mức.
- Given Jenkins credential, when stage sử dụng nó, then secret không nằm trong source, log hay artifact do pipeline tạo.

## Implementation Notes

- Pipeline phần mềm dùng merge-base cho pull request, hiển thị lint/type/test/build thành stage riêng, xuất JUnit và chỉ release từ `main`.
- Release tải corpus đã quản lý từ S3, build image theo full Git SHA, tra ECR digest và deploy digest chính xác qua SSM; smoke lỗi sẽ rollback, smoke lại revision cũ và vẫn trả FAILED.
- Terraform chỉ plan và chỉ archive plan sau secret-pattern check. Model/prompt pipeline dùng min/max metric gates và approval allowlist trước 50%/100%.
- Xác minh cục bộ: safety tests, frontend lint/type/build, Compose staging merge và migration upgrade–downgrade–upgrade đều pass. Backend gate đang reject đúng do lỗi Ruff/mypy và test collection có sẵn ngoài phạm vi Jenkins; chi tiết nằm trong `docs/jenkins.md`.

## Spec Change Log

## Review Triage Log

| Reviewer finding | Verdict | Evidence / resolution |
|---|---|---|
| Model rollout lacked trusted-branch/PR guard | high | Verified: credentials could be reached from an untrusted multibranch build. Added `guard-release.sh model` before metric/deploy stages. |
| Metric report was not bound to `MODEL_REVISION` | high | Verified. Metric gate now rejects mismatched revision metadata. |
| No fresh metric gate between 10%, 50% and 100% | high | Verified. Added trusted evaluator runs and revision/traffic-bound gates after 10% and 50%. |
| Non-finite metric values could pass | medium | Verified Python NaN comparison behavior. Added numeric and `math.isfinite` validation with regression coverage. |
| IaC detection omitted lock/policy/module inputs | medium | Verified. Any path under `infra/` now triggers Terraform gates. |
| Corpus-only changes skipped backend checks | medium | Verified because backend image copies `corpus/`. Added corpus classification and test. |
| Terraform plan used uncontrolled ambient AWS credentials | medium | Verified. Added dedicated read-only `heritage-terraform-plan-aws` binding. |
| Terraform artifact secret scan was too narrow | high | Verified against PEM/JWT/unquoted forms. Added sensitivity-aware JSON redaction, raw-plan deletion and broader final scan. |
| SSM waiter timeout could race a still-running deploy | high | Verified bounded waiter behavior. Replaced it with configurable polling, terminal-state output and cancellation on timeout. |
| Monolithic remote command could leave a partial deployment | high | Verified that a deploy-stage failure previously skipped smoke rollback. Added immediate rollback wrapper; command remains idempotent and pipeline remains failed. |
| Smoke could bless a stale container revision | high | Verified health alone did not identify image. Deploy now asserts running backend/frontend image references equal the selected ECR digests before smoke can update last-good. |
| Rollback could target the same failed SHA | medium | Verified. Both deploy-failure and smoke-failure rollback reject a no-op target. |
| Mutable corpus could make one Git tag represent different content | high | Verified external corpus is not Git-owned. ECR tags must be immutable, corpus source must be versioned, and its digest is archived in the release manifest. |
| Manual rollback documentation omitted required context | low | Verified. Documentation now requires an authorized parameterized Jenkins recovery job and lists its environment/credential contract. |
| Metric NaN edge case | medium | Duplicate verified finding; covered by finite-value validation and safety test. |
| Deploy directory allowed `..` traversal | medium | Verified regex admitted traversal. Added explicit traversal rejection. |
| `model-deploy.sh` accepted arbitrary traffic levels directly | medium | Verified direct invocation bypassed the outer guard. Added local 10/50/100 validation. |
| Secret scan missed PEM/JWT/unquoted values | high | Duplicate verified finding; scanner and Terraform redactor were hardened. |
| Model approval sequence was not exercised | medium | Verified: shell guards alone would not detect reordered stages. Added structural ordering/allowlist checks plus live evaluator gate ordering checks; Groovy compilation also runs locally. |

## Design Notes

Deployment dùng AWS CLI + SSM thay vì SSH key. Jenkins deploy role chỉ cần đọc corpus release, ECR push/read, SSM command/status và quyền đọc/ghi đúng parameter last-good; runtime role vẫn độc lập và được cấp ngoài task này. Các giá trị môi trường cụ thể được Jenkins quản trị cung cấp qua credentials/global environment, nên repository không chứa account ID, role ARN hoặc endpoint thật.

## Verification

**Commands:**
- `bash jenkins/tests/run.sh` -- change classification và safety guards pass.
- `npm ci && npm run lint && npx tsc --noEmit && npm run build` trong `apps/frontend` -- frontend gates chạy non-interactive.
- `python3.12 -m venv .ci-venv && .ci-venv/bin/pip install -r jenkins/requirements-ci.txt && .ci-venv/bin/ruff check apps/backend && .ci-venv/bin/mypy apps/backend` -- backend static gates chạy bằng dependency pin.
- `docker compose -f docker-compose.yml -f jenkins/docker-compose.staging.yml config` -- staging override hợp lệ khi truyền image URI mẫu.
- Jenkins Declarative Pipeline linter hoặc Jenkins test job -- cả hai Jenkinsfile parse được; nếu local không có Jenkins, ghi rõ giới hạn này.
