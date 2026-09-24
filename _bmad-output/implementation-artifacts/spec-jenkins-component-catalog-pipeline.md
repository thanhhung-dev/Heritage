---
title: 'Jenkins component-catalog path-based delivery'
type: 'refactor'
created: '2026-09-24'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'f7039a3086405ad9cfaa554375c4a626f90f2a0e'
context:
  - '{project-root}/docs/secrets-policy.md'
  - '{project-root}/docs/jenkins.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Jenkins hiện phân loại thay đổi bằng regex/boolean rải trong shell và khi release luôn build/deploy cả backend lẫn frontend, nên chưa đạt mô hình component-aware mà mỗi path, artifact và deploy unit có ownership rõ ràng.

**Approach:** Chuyển sang catalog JSON duy nhất để detector và release planner sinh `.ci-components.env` cùng `.ci-release-plan.json`; pipeline chỉ chạy CI, build/push image và cập nhật deploy unit bị ảnh hưởng, trong khi tài liệu được bỏ qua và runtime path chưa map phải fail closed. Giữ model/prompt rollout là job độc lập.

## Boundaries & Constraints

**Always:** Catalog phải bao phủ toàn bộ tracked runtime/config path; PR so sánh merge-base, push so sánh previous commit và chỉ fallback `HEAD~1` lần đầu; documentation-only cho kết quả `unchanged`; CI config chỉ chạy contract/config validation, không giả lập product component; image dùng full Git SHA và deploy bằng digest; migration/infrastructure/model vẫn giữ gate riêng.

**Never:** Không sao chép component GKE/Kubeflow không tồn tại trong Heritage; không deploy từ PR; không biến unknown path thành “run all”; không gộp model/prompt rollout vào software push pipeline; không thay AWS ECR/SSM/Docker Compose bằng Helm/GKE.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Documentation-only | Chỉ `docs/**`, Markdown hoặc generated planning evidence | `CHANGED_COMPONENTS=unchanged`; mọi product CI/build/deploy skipped | Build thành công, không publish |
| Unknown runtime path | File không ignore và không match component | Detector dừng với tên path chưa map | Build FAILED trước CI |
| Frontend-only | Chỉ `apps/frontend/**` | Chỉ frontend gates, image và frontend deploy unit | Backend/migration không chạy |
| Migration-only | Alembic/schema thay đổi | Backend dependency gate + clean DB cycle; chỉ backend image và migration/backend units | Lỗi migration chặn publish/deploy |
| CI config-only | Jenkins/catalog/script thay đổi | Chỉ detector/catalog/shell/Python/Compose contracts | Không tạo product image/unit |
| Model/prompt | Training/prompt rollout path | Root chỉ chạy model contract CI; rollout vẫn qua `Jenkinsfile.model` | Không tự deploy software/model |

</frozen-after-approval>

## Code Map

- `Jenkinsfile` -- đang dùng boolean flags và release cả hai image; cần chuyển sang env/release plan từ catalog.
- `jenkins/change-detection.sh` -- detector regex hiện tại; thay bằng Python catalog detector mỏng, test trực tiếp.
- `jenkins/ecr-build-push.sh`, `deploy-staging.sh`, `deploy-with-rollback.sh`, `smoke-and-rollback.sh` -- release scripts phải nhận selected images/units và bảo toàn component không đổi.
- `jenkins/docker-compose.staging.yml` -- Compose vẫn là deploy substrate; selected-unit commands không được recreate component ngoài plan.
- `Jenkinsfile.model`, `metric-gate.py`, `evaluate-model-rollout.sh` -- giữ rollout độc lập, chỉ catalog route source liên quan vào contract CI.
- `jenkins/tests/run.sh` -- mở rộng contract coverage cho catalog, docs-only, unmapped path, dedup image/unit và affected-only release.
- `docs/jenkins.md` -- cập nhật webhook/job flow, component table, generated files và ví dụ log.

## Tasks & Acceptance

**Execution:**
- [x] `jenkins/config/components.json` -- định nghĩa ignored paths, component triggers, CI profiles, images và deploy units cho Heritage.
- [x] `jenkins/python/change_detection/detector.py` -- phân loại diff từ catalog, hỗ trợ force component và fail closed, ghi `.ci-components.env`.
- [x] `jenkins/python/release_plan.py` -- deduplicate image/deploy fan-out, ghi `.ci-release-plan.json`.
- [x] `Jenkinsfile` -- tiêu thụ generated outputs và chỉ chạy stage/component branch liên quan.
- [x] `jenkins/ecr-build-push.sh` cùng deploy scripts -- build/push/deploy selected resources theo digest, không cập nhật component ngoài plan.
- [x] `jenkins/tests/` -- contract tests cho mọi matrix row và release planner.
- [x] `docs/jenkins.md` -- mô tả Pipeline-from-SCM webhook flow, component catalog và vận hành affected-only.

**Acceptance Criteria:**
- Given diff hợp lệ, when detector chạy, then mỗi changed runtime path được map rõ ràng và outputs deterministic.
- Given docs-only hoặc CI-only diff, when release planner chạy, then không có product image/deploy unit.
- Given một component product thay đổi, when main pipeline release, then chỉ image và deploy unit trong deduplicated plan được cập nhật.
- Given unknown runtime path, when detection chạy, then pipeline fail closed trước quality gates.
- Given model/prompt source thay đổi, when root pipeline chạy, then chỉ contract CI chạy và không tự rollout.

## Implementation Notes

- Detector bao gồm cả file bị xóa và xử lý glob `**/` cho file ở repository root; runtime/config path chưa map trả lỗi trước mọi quality gate.
- Release planner giữ thứ tự catalog, deduplicate backend image/deploy unit dùng chung và phát đồng thời JSON cùng environment contract cho Jenkins.
- Release scripts chỉ build, pull và chạy unit trong plan; backend artifact vẫn ghi `CORPUS_SHA256`, còn deploy xác minh digest của service được cập nhật.

## Spec Change Log

- 2026-09-24: Hoàn tất catalog-based detection, affected-only CI/release, contract tests và tài liệu vận hành.

## Review Triage Log

| # | Verdict | Route | Evidence |
|---|---|---|---|
| 1 | false | reject | Dùng `GIT_PREVIOUS_COMMIT` là yêu cầu rõ trong frozen constraints; thay đổi sau build lỗi vẫn nằm trong revision hiện tại và việc chọn previous successful sẽ mở rộng ngoài hợp đồng đã duyệt. |
| 2 | medium | patch | Root commit không có `HEAD~1`; đã khôi phục empty-tree fallback để first build vẫn phân loại toàn bộ tree. |
| 3 | medium | patch | `--name-only` bỏ source của rename/copy; detector nay parse name-status và phân loại cả hai path, có test rename runtime sang docs. |
| 4 | high | patch | `docker-compose.yml` release-less khiến cấu hình runtime không đến staging; `runtime_stack` nay build/deploy cả hai service. |
| 5 | medium | patch | `.dockerignore` ảnh hưởng root build context backend; ownership `runtime_stack` nay tạo lại cả hai image để fail safe. |
| 6 | medium | patch | Corpus cần import lại; `corpus/**` nay đồng thời chọn migration plan, tạo backend image và chạy import trước backend. |
| 7 | high | patch | SHA last-good toàn cục không bảo đảm có image selective; rollback nay dùng key theo backend/frontend, chỉ rollback runtime unit và hỗ trợ đọc key legacy. |
| 8 | medium | patch | Một số artifact trong data/model profile không được stage chạm tới; stage nay kiểm tra cả thư mục dữ liệu và root model dump ngoài compileall. |
| 9 | medium | patch | Catalog thiếu referential validation có thể silently drop unit; detector/planner nay fail closed khi profile/image/unit không tồn tại. |
| 10 | medium | patch | Coverage thiếu partial-release scenarios; đã thêm runtime-stack, rename, catalog validation, backend/frontend selective và component-scoped rollback assertions. |
| 11 | high | patch | Deployment-failure rollback có thể chạy lại migration/import; rollback nay chuẩn hóa mọi migration unit thành backend runtime unit. |
| 12 | medium | patch | Input deploy unit trùng có thể chạy migration hai lần; deploy script nay deduplicate trước pull/operation. |
| 13 | medium | patch | Input release image trùng có thể build/push hai lần; build script nay deduplicate image. |
| 14 | medium | patch | Root Jenkinsfile predicates chưa được contract test khóa; shell suite nay xác nhận mapping profile và `HAS_RELEASE`. |
| 15 | medium | patch | Deploy test chưa xác nhận digest enforcement; shell suite nay yêu cầu command chứa inspect và selected digest. |
| 16 | false | reject | Finding duplicate của #4/#5 về Compose/runtime ownership; cùng bad outcome đã được vá bằng release resources cho `runtime_stack`. |
| 17 | false | reject | Finding duplicate của #7/#11 về rollback selective; component-scoped keys và runtime-only rollback đã loại bỏ outcome được mô tả. |

## Design Notes

Catalog cho repo hiện tại gồm `ci_config`, `backend`, `frontend`, `migration`, `runtime_stack`, `data_pipeline`, `model_prompt`, và `infrastructure`. Path có thể thuộc nhiều component khi dependency thật yêu cầu; release planner chịu trách nhiệm deduplicate shared backend image hoặc deploy unit.

## Verification

**Commands:**
- `python3 -m unittest discover -s jenkins/tests -p 'test_*.py'` -- catalog/detector/planner contracts pass.
- `bash jenkins/tests/run.sh` -- shell release guards và affected-only command contracts pass.
- `groovyc Jenkinsfile && groovyc Jenkinsfile.model` -- Groovy syntax hợp lệ.
- Existing frontend, migration và Compose checks -- không regression.
