---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - ARCHITECH-TECHNOLOGY.png
  - schema.sql
  - docs/chatbot.md
  - docs/planning-artifacts/prds/prd-HeritageGraph-2026-09-08/prd.md
  - docs/planning-artifacts/architecture/architecture-HeritageGraph-2026-09-15/ARCHITECTURE-SPINE.md
  - docs/planning-artifacts/ux-designs/ux-HeritageGraph-2026-09-15/DESIGN.md
  - docs/planning-artifacts/ux-designs/ux-HeritageGraph-2026-09-15/EXPERIENCE.md
  - docs/specs/spec-heritagegraph-v2/SPEC.md
  - docs/specs/spec-heritagegraph-v2/features.md
---

# HeritageGraph - Epic Breakdown

## Overview

Tài liệu này phân rã toàn bộ yêu cầu HeritageGraph thành epic và story có thể triển khai. `ARCHITECH-TECHNOLOGY.png` sau khi được review và hiệu chỉnh là baseline công nghệ mới nhất. `docs/chatbot.md`, `schema.sql` và workflow Admin Knowledge Studio → draft corpus → Airflow validation/indexing → human review → publish là baseline hành vi. PRD cũ chỉ cung cấp mục tiêu sản phẩm và các yêu cầu không xung đột; quyết định công nghệ cũ không còn binding.

## Requirements Inventory

### Functional Requirements

- FR01: Quản trị viên đăng nhập an toàn và mọi thao tác quản trị được xác thực, phân quyền và ghi audit.
- FR02: Người dùng có thể hỏi đáp tiếng Việt bằng văn bản về di sản Huế–Đà Nẵng.
- FR03: Chatbot chỉ trả lời từ evidence thuộc một corpus release đã publish; thiếu bằng chứng thì clarify hoặc abstain.
- FR04: Mọi khẳng định thực tế trong câu trả lời có citation hợp lệ tới passage và document nguồn.
- FR05: Chatbot đính chính tiền đề sai ngay phần mở đầu khi evidence chứng minh tiền đề không đúng.
- FR06: Hệ thống chuẩn hóa câu hỏi, sửa gần đúng và resolve canonical entity/alias; trường hợp mơ hồ phải hỏi lại.
- FR07: Intent router phân loại overview, field, timeline, relationship, section, comparison, open_text hoặc out_of_scope.
- FR08: Query planner chọn exact claim, timeline, graph 1–2 hop, narrative section, text retrieval hoặc multi-operator plan theo intent.
- FR09: Text retrieval kết hợp tìm từ, tìm không dấu/lỗi gõ, vector khi được eval chứng minh có lợi, rồi hợp nhất thứ hạng.
- FR10: Entity Dossier/Evidence Context Builder hợp nhất, loại trùng, giữ xung đột nguồn và cấp citation label cho evidence.
- FR11: Pre-generation gate kiểm tra entity scope, trạng thái publish, độ mới, corpus version và ngưỡng evidence.
- FR12: Post-generation gate kiểm tra citation, số, ngày, factual claims, mức chắc chắn và xung đột nguồn trước khi trả lời.
- FR13: Qwen3-4B + LoRA chỉ tổng hợp evidence và định dạng câu trả lời; không tự truy vấn DB hoặc bổ sung tri thức ngoài evidence.
- FR14: Graph Service cho phép truy vấn entity, predicate, relation và traversal giới hạn 1–2 hop trên published corpus, đồng thời dùng các path có evidence để gợi ý câu hỏi đào sâu liên quan.
- FR15: Recommendation Service hỗ trợ cold start và hồ sơ sở thích ẩn danh được frontend suy ra từ view, click, dwell, save và dismiss có consent rồi lưu trong `localStorage`.
- FR16: Candidate Generator kết hợp graph projection, pgvector và metadata; Rank & Diversify tránh kết quả quá giống hoặc đã xem.
- FR17: Mỗi gợi ý có score và reason path giải thích được; frontend cập nhật hồ sơ cục bộ từ tương tác mới theo quy tắc xác định và có thể tái lập.
- FR18: Tại Preferences, người dùng xem trạng thái consent, tắt cá nhân hóa, xuất hoặc đặt lại hồ sơ cùng interaction history lưu trên thiết bị.
- FR19: Nội dung chi tiết hỗ trợ guided story gồm 1–6 narrative scenes với ảnh/panorama hoặc 3D, hotspot, audio, transcript và tài nguyên liên quan.
- FR20: Media asset lưu provenance, license, contributor và URL gốc; script audio phải qua kiểm tra evidence trước khi tổng hợp.
- FR21: Khi S3 hoặc media delivery lỗi, trang vẫn phục vụ text, transcript và tri thức; media hiển thị trạng thái không khả dụng.
- FR22: Admin Knowledge Studio cung cấp CRUD có hướng dẫn cho document và metadata nguồn.
- FR23: Admin có thể tạo hoặc điều chỉnh passage từ raw text, xem char span, content hash và corpus version.
- FR24: Admin có thể tạo, tìm và rà trùng entity; quản lý alias, place profile, primary evidence và supporting evidence.
- FR25: Admin có thể nhập typed claim từ claim_field, timeline event cùng participant role, và relation từ predicate đóng.
- FR26: Admin có thể biên soạn narrative section bằng Markdown và gắn nhiều supporting passages.
- FR27: Mọi knowledge record mới được lưu ở trạng thái draft và không xuất hiện trong online serving trước khi publish.
- FR28: Admin có thể chọn evidence trực tiếp từ passage; UI không yêu cầu nhập UUID hoặc foreign key thủ công.
- FR29: FastAPI kiểm tra tức thời required fields, type, foreign key, exact duplicate và business constraint khi lưu draft.
- FR30: Admin submit một document package hoặc corpus revision để chạy deep validation bất đồng bộ, không chạy DAG nặng sau mỗi lần save.
- FR31: Airflow điều phối RAG data pipeline: validate, deduplicate, provenance/version checks, semantic chunking, content hash, embedding, index build và manifest.
- FR32: Mỗi submission tạo hoặc tái sử dụng một validation run idempotent và xuất validation issues phân loại error/warning.
- FR33: Admin xem trạng thái DAG, quality report, lỗi theo record/evidence và sửa draft rồi resubmit.
- FR34: Corpus chỉ được publish khi validation pass và human reviewer phê duyệt; publish là chuyển đổi atomic và có audit.
- FR35: Online QA và Recommendation pin một published corpus version xuyên suốt request, retrieval, evidence persistence và response.
- FR36: Dashboard quản trị hiển thị sức khỏe corpus/KG, validation queue, provenance gaps, index status, model/prompt version và eval metrics.
- FR37: Public Heritage Portal dùng visual language kể chuyện di sản thống nhất xuyên suốt Home, Explore, search/filter theo khu vực và loại, Entity Detail, Chat, Recommendation và Preferences; có đầy đủ loading/empty/error/not-found/clarify/abstained/responsive states trên published content.

### NonFunctional Requirements

- NFR01: PostgreSQL là system of record cho knowledge, release, audit, chat evidence và trạng thái vận hành có cấu trúc.
- NFR02: Passage đã thuộc published release là bất biến; re-ingestion tạo revision mới thay vì sửa evidence đã trích dẫn.
- NFR03: Mọi write path đi qua FastAPI/service transaction; Admin UI và Airflow không chỉnh production tables tùy ý.
- NFR04: Database constraints bảo vệ type, range, foreign key, uniqueness và provenance bắt buộc; app validation không thay thế DB integrity.
- NFR05: Import, submit và Airflow retry phải idempotent; cùng submission/revision không tạo knowledge hoặc job trùng.
- NFR06: Publish không thể xảy ra khi validation pending/failed hoặc chưa có human review.
- NFR07: Online serving không đọc draft, retired, withdrawn, out-of-scope hoặc evidence khác corpus version.
- NFR08: Một request không được trộn graph, lexical index, vector index hoặc evidence từ các release khác nhau.
- NFR09: Citation faithfulness ≥85%, citation coverage ≥90% và refusal accuracy ≥90%; báo cáo cùng nhau để tránh tối ưu lệch.
- NFR10: Retrieval recall@1 ≥95% trên tên chuẩn, alias, không dấu và paraphrase trong tập đánh giá đã version hóa.
- NFR11: Chat p95 ≤8 giây trong môi trường mục tiêu; recommendation không gồm generation ≤2 giây; trang chi tiết ≤3 giây.
- NFR12: Dịch vụ ngoài hoặc media store lỗi phải degrade tường minh, không bịa dữ liệu và không gây trang trắng.
- NFR13: Qwen inference chạy local; llama.cpp chỉ dùng GGUF/adapter tương thích, còn MLX base+adapter là runtime riêng.
- NFR14: Model release manifest ghi base model, adapter, tokenizer, quantization/GGUF hash, prompt version, corpus version và rollout id.
- NFR15: MLX adapter không được đưa trực tiếp vào llama.cpp; mọi conversion/fusion phải qua regression evaluation trước rollout.
- NFR16: Airflow là orchestrator cho deep validation/indexing; immediate field validation vẫn thuộc FastAPI/PostgreSQL.
- NFR17: RAG pipeline tạo manifest tái lập gồm chunk ids, content hashes, embedding contract, model và corpus revision.
- NFR18: Candidate graph trong NetworkX là projection có version từ PostgreSQL published corpus, không phải source of truth song song.
- NFR19: Hồ sơ và interaction history cục bộ chỉ được ghi khi có consent, dùng schema có version và giới hạn dung lượng; backend không lưu định danh/hồ sơ Public User và phải kiểm tra payload hồ sơ ẩn danh trong recommendation request.
- NFR20: WCAG 2.1 AA áp dụng cho chat, Admin Studio, validation report, media controls và keyboard workflow.
- NFR21: Prometheus thu metrics, Loki thu logs, Grafana hiển thị dashboard và Langfuse truy vết prompt/evidence/model trong giới hạn privacy.
- NFR22: Không ghi raw password, token, IP hoặc nội dung nhạy cảm vào logs/traces; secret nằm ngoài source control.
- NFR23: GitHub → Jenkins chạy unit, integration, contract và E2E tests trước build/publish/deploy component image.
- NFR24: Terraform quản lý infrastructure; software deployment và model/prompt rollout là hai pipeline tách biệt có rollback.
- NFR25: Rollout model/prompt 10% → 50% → 100% chỉ tiến bước khi quality, grounding, latency và error metrics đạt gate.

### Additional Requirements

- Sơ đồ đích chia bốn boundary: Offline Knowledge Lifecycle, Online Serving/Read-only QA, Storage và Cross-cutting Operations.
- Apache Airflow trigger RAG Data Pipeline nhưng không tự publish knowledge; output của pipeline là validation report, prepared indexes và manifest cho draft revision.
- FastAPI Backend là entry point; Chat Service, Graph Service và Recommendation Service có ownership riêng, không đặt SQL/planning/prompt trong endpoint.
- Chat flow chuẩn: normalize → resolve entity → classify intent → query plan → operators → Entity Dossier/Evidence Builder → pre-generation gate → Qwen → post-generation gate → answered/clarify/abstained.
- Evidence Builder dùng token budget cấu hình và chọn evidence theo intent; giới hạn `2 adjacent chunks / 2200 characters` trong ảnh chỉ là cấu hình Text operator cũ, không phải invariant toàn hệ thống.
- PostgreSQL FTS/pg_trgm phải được gọi đúng tên; nếu yêu cầu BM25 thật, phải có custom implementation hoặc search component được sở hữu rõ ràng.
- pgvector dùng embedding dimension theo model contract; thay model/dimension cần migration/reindex plan.
- Amazon S3 là canonical object store cho MVP; upload path, canonical URL, access policy và reconciliation khi DB/object write thất bại phải được xác định theo asset class.
- Recommendation branches `local profile available` và `cold start` cùng hội tụ vào Candidate Generator rồi Rank & Diversify; Recommendation Service không lưu hồ sơ Public User.
- Inference deployment tách rõ MLX base+adapter và llama.cpp GGUF; không mô tả chúng như một runtime hỗn hợp.
- GitHub/Jenkins/Terraform là delivery plane; Prometheus/Loki/Grafana/Langfuse là observability plane; cả hai cắt ngang offline và online.
- Prompt/template configuration phải được version hóa, phân quyền, audit và rollback; developer không chỉnh production table trực tiếp.
- Tên sơ đồ cần đổi từ `ARCHITECH-TECHNOLOGY.png` thành `ARCHITECTURE-TECHNOLOGY.png`; chuẩn hóa các nhãn `Rank & Diversify`, `Graph Service`, `QA Solver`, `Chunk IDs`.

### UX Design Requirements

- UX-DR01: Admin dashboard cho biết draft release hiện tại, validation status, issue counts, review status và khả năng publish.
- UX-DR02: Document wizard thu thập URL, title, region, source type, tier, observed date, license và raw text với lỗi theo field.
- UX-DR03: Passage workspace hiển thị raw text và passage song song, làm nổi char span và cho phép chọn evidence trực tiếp.
- UX-DR04: Entity editor có canonical/normalized name, type/subtype, aliases, scope/status và cảnh báo duplicate/fuzzy candidate.
- UX-DR05: Claim form sinh control theo `claim_field.value_type`, tự đề xuất default unit và hiển thị validity/confidence/canonical state.
- UX-DR06: Timeline editor hỗ trợ year/range/precision, event type, participant roles, actor, artifact và evidence.
- UX-DR07: Relation builder hiển thị `subject ─ predicate → object`, chỉ cho chọn predicate đã đăng ký và cảnh báo triple trùng.
- UX-DR08: Narrative editor hỗ trợ Markdown, section ordering, primary/supporting evidence và preview nội dung.
- UX-DR09: Validation center hiển thị trạng thái Airflow, tiến độ theo stage, lỗi/warning có link về đúng record và retry/resubmit an toàn.
- UX-DR10: Review workspace hiển thị diff, provenance, conflicting sources, reviewer decision và audit history trước publish.
- UX-DR11: Publish action yêu cầu xác nhận release/version, tóm tắt gate đã pass và thông báo rõ rollback/retire path.
- UX-DR12: Toàn bộ Public Portal — Home, Explore, Entity Detail, Chat, Recommendation, Preferences và Multimedia — dùng chung heritage storytelling design system: editorial composition giàu hình ảnh, card bất đối xứng có hierarchy, narrative flow giữa các thực thể và responsive states nhất quán. Admin Studio vẫn dùng dashboard/form/table nghiệp vụ, không áp dụng bố cục kể chuyện của Public Portal.

### FR Coverage Map

- FR01: Epic 1 — Admin truy cập Knowledge Studio an toàn; thao tác quản trị được phân quyền và audit.
- FR02: Epic 4 — Người dùng hỏi đáp tiếng Việt bằng văn bản.
- FR03: Epic 4 — Chỉ published evidence được dùng; thiếu evidence thì clarify/abstain.
- FR04: Epic 4 — Câu trả lời factual có citation tới passage/document.
- FR05: Epic 4 — Đính chính tiền đề sai bằng evidence.
- FR06: Epic 4 — Chuẩn hóa, fuzzy correction và entity resolution.
- FR07: Epic 4 — Intent router tám lớp.
- FR08: Epic 4 — Query planner và retrieval operators.
- FR09: Epic 4 — Hybrid text/vector retrieval có đánh giá.
- FR10: Epic 4 — Entity Dossier và Evidence Context Builder.
- FR11: Epic 4 — Pre-generation gate.
- FR12: Epic 4 — Post-generation citation/grounding gate.
- FR13: Epic 4 — Qwen3-4B chỉ tổng hợp evidence.
- FR14: Epic 4 — Graph Service, traversal giới hạn và gợi ý câu hỏi đào sâu từ path có evidence.
- FR15: Epic 6 — Cold start và hồ sơ sở thích ẩn danh cục bộ có consent.
- FR16: Epic 6 — Candidate generation và rank/diversify.
- FR17: Epic 6 — Recommendation có score/reason path và cập nhật local profile.
- FR18: Epic 6 — Quản lý consent, xuất và đặt lại dữ liệu cục bộ.
- FR19: Epic 5 — Scene-based story, 3D, audio, transcript và media liên quan.
- FR20: Epic 5 — Media provenance và evidence gate cho audio.
- FR21: Epic 5 — Media failure degradation.
- FR22: Epic 1 — Document source CRUD trong Admin Knowledge Studio.
- FR23: Epic 1 — Passage editor và corpus metadata.
- FR24: Epic 1 — Entity/alias/place profile và evidence management.
- FR25: Epic 1 — Typed claim, timeline và relation editors.
- FR26: Epic 1 — Narrative editor và supporting evidence.
- FR27: Epic 1 — Knowledge mới luôn ở trạng thái draft.
- FR28: Epic 1 — Evidence selection không yêu cầu UUID/FK thủ công.
- FR29: Epic 1 — FastAPI/PostgreSQL validation tức thời.
- FR30: Epic 2 — Submit revision để deep validation bất đồng bộ.
- FR31: Epic 2 — Airflow RAG data pipeline.
- FR32: Epic 2 — Idempotent validation run và issues.
- FR33: Epic 2 — Validation Center và resubmit workflow.
- FR34: Epic 2 — Human review và atomic publish.
- FR35: Epic 2 — Published corpus version contract cho online consumers.
- FR36: Epic 2 — Corpus/KG/validation/index/eval dashboard.
- FR37: Epics 0, 3, 4, 5 và 6 — Design foundations dùng chung; Home, Explore/Search/Filter, Map 2D, Content Landing, Chat, Recommendation, Preferences và Multimedia có đủ trạng thái trên published content.

## Epic List

### Epic 0: Engineering Foundation

Nhóm phát triển có một nền tảng triển khai tái lập cho local, test và AWS staging gồm cấu hình môi trường, PostgreSQL/Alembic, S3/ECR/IAM/networking, Jenkins/Terraform, observability, application shells, API mocks và test harness trước khi phát triển tính năng.

**Requirements covered:** Shared foundation cho FR37; NFR01, NFR03–NFR05, NFR12–NFR14, NFR16–NFR25 và các architecture requirements về AWS, delivery, observability, testing.

### Epic 1: Admin Knowledge Studio

Quản trị viên đăng nhập và biên soạn trọn một knowledge package — document, passage, entity/alias/place profile, claim, timeline, relation, narrative và evidence — ở trạng thái draft mà không cần thao tác SQL, UUID hoặc foreign key thủ công.

**FRs covered:** FR01, FR22–FR29

### Epic 2: Kiểm định và phát hành corpus đáng tin cậy

Biên tập viên submit draft để Airflow kiểm tra sâu, tạo embedding/index/manifest, xử lý issues, review và publish một corpus release atomically; dashboard cho biết sức khỏe và khả năng phục vụ của từng release.

**FRs covered:** FR30–FR36

### Epic 3: Cổng khám phá và kể chuyện di sản

Người dùng tìm và chọn published heritage content qua Home, Explore/Library, bản đồ 2D Huế–Đà Nẵng và Content Landing; từ đó tiếp tục sang trải nghiệm scene, Chat, Recommendation hoặc nội dung liên quan khi các capability tương ứng khả dụng.

**FRs covered:** FR37

### Epic 4: Trợ lý hỏi đáp có căn cứ

Người dùng hỏi bằng tiếng Việt từ portal hoặc trang chat; hệ thống resolve entity, lập query plan, lấy evidence đúng published corpus, dùng Qwen3-4B tổng hợp và chỉ trả answered, clarify hoặc abstained sau grounding validation.

**FRs covered:** FR02–FR14

### Epic 5: Trải nghiệm di sản theo scene, 3D và đa phương tiện

Người dùng đi qua một guided story gồm các scene có thứ tự, hình ảnh/panorama hoặc 3D, audio, transcript và tài nguyên có provenance; khi media storage hoặc delivery lỗi, scene fallback và nội dung cốt lõi vẫn hoạt động.

**FRs covered:** FR19–FR21

### Epic 6: Khám phá cá nhân hóa có thể giải thích

Người dùng mới nhận cold-start recommendations; người dùng có consent nhận kết quả dựa trên hồ sơ ẩn danh lưu trong `localStorage`, xem reason path, đồng thời có thể xuất, đặt lại hoặc tắt cá nhân hóa mà không cần đăng nhập. Hệ thống không hỗ trợ đồng bộ hồ sơ giữa các thiết bị.

**FRs covered:** FR15–FR18

## Delivery Ownership Matrix

Mỗi story có một owner chính để sprint planning, estimate và giao việc không trộn lẫn trách nhiệm. Các vai trò hỗ trợ chỉ tham gia review, contract hoặc integration; nếu phần việc hỗ trợ đủ lớn thì phải tách thành story riêng.

| Role | Trách nhiệm chính |
|---|---|
| **DES** | User flow, wireframe, Figma component, responsive screen, prototype và design handoff |
| **FE** | Web UI, client state, accessibility, responsive behavior và API integration |
| **BE** | FastAPI/service, authentication, transaction, database contract và online API |
| **AI** | Retrieval, GraphRAG, prompting, inference, grounding gate và model evaluation |
| **DATA** | Schema/migration, ingestion, Airflow, validation, embedding/index và corpus release |
| **DEVOPS** | Environment, AWS, CI/CD, observability và runtime operations |

| Epic | DES | FE | BE | AI | DATA | DEVOPS |
|---|---|---|---|---|---|---|
| **0 — Engineering Foundation** | 0.8, 0.9 | 0.6 | 0.7 | — | 0.2 | 0.1, 0.3, 0.4, 0.5 |
| **1 — Admin Knowledge Studio** | — | — | 1.1–1.8 | — | — | — |
| **2 — Corpus Validation & Publishing** | — | 2.4, 2.7 | 2.1, 2.5, 2.6 | — | 2.2, 2.3 | — |
| **3 — Heritage Portal** | — | 3.1–3.4 | — | — | — | — |
| **4 — Grounded Q&A** | — | 4.6 | 4.1 | 4.2–4.5, 4.7, 4.8 | — | — |
| **5 — Scene/3D/Multimedia** | — | 5.3, 5.5, 5.6 | 5.1, 5.2 | 5.4 | — | — |
| **6 — Personalization** | — | 6.1, 6.3, 6.6, 6.7 | 6.2 | 6.4, 6.5, 6.8 | — | — |

Các ô trong bảng chỉ ghi **primary owner**; dependency hoặc reviewer từ role khác nằm trong acceptance criteria và không làm thay đổi ownership.

**Sprint rule:** một story chỉ được kéo vào sprint khi owner chính đã rõ, dependency từ role hỗ trợ đã có contract, và acceptance criteria có deliverable kiểm chứng được cho đúng role đó.

# Epic 0: Engineering Foundation

Nhóm phát triển có một nền tảng triển khai tái lập cho local, test và AWS staging gồm cấu hình môi trường, PostgreSQL/Alembic, S3/ECR/IAM/networking, Jenkins/Terraform, observability, application shells, API mocks và test harness trước khi phát triển tính năng.

### Story 0.1: Chuẩn hóa repository, môi trường và cấu hình secrets

As a developer,
I want a documented and reproducible configuration for local, test and staging environments,
So that I can run and verify HeritageGraph without relying on undocumented machine-specific settings or committing secrets.

**Acceptance Criteria:**

**Given** một bản clone mới của repository
**When** developer làm theo hướng dẫn thiết lập
**Then** backend và frontend cài được dependency bằng các phiên bản runtime/package manager đã quy định
**And** các lệnh chạy, test và kiểm tra health cơ bản được tài liệu hóa.

**Given** các thành phần backend, frontend, data pipeline và observability cần configuration
**When** developer xem các file environment mẫu
**Then** mọi biến bắt buộc được liệt kê với mô tả và giá trị phát triển an toàn
**And** file mẫu không chứa credential hoặc secret thật
**And** secret/runtime artifacts được loại khỏi source control.

**Given** ứng dụng khởi động trong local, test hoặc staging
**When** configuration bắt buộc bị thiếu hoặc sai định dạng
**Then** ứng dụng dừng sớm với thông báo chỉ rõ tên configuration không hợp lệ
**And** không ghi giá trị secret vào log.

**Given** repository đã có code và configuration trước đó
**When** story này được triển khai
**Then** cấu trúc hiện hữu được tái sử dụng hoặc chuẩn hóa thay vì tạo song song một hệ configuration mới
**And** các thay đổi không làm mất khả năng chạy những test hiện có.

### Story 0.2: Thiết lập PostgreSQL, extensions và Alembic baseline

As a backend developer,
I want a reproducible PostgreSQL 16 database baseline for local, test and AWS staging,
So that schema changes can be developed, verified and deployed consistently.

**Acceptance Criteria:**

**Given** developer đã hoàn tất cấu hình môi trường ở Story 0.1
**When** khởi động database local theo hướng dẫn
**Then** PostgreSQL 16 sẵn sàng qua health check
**And** dữ liệu được lưu trong managed volume
**And** database không dùng credential production.

**Given** một database trống
**When** chạy Alembic upgrade tới revision mới nhất
**Then** schema baseline hiện có được tạo thành công
**And** các extension `pgvector` và `pg_trgm` cần thiết được bật
**And** chạy lại migration không gây lỗi hoặc tạo object trùng.

**Given** migration thay đổi database
**When** CI hoặc developer kiểm tra migration
**Then** upgrade được chạy trên database sạch
**And** downgrade/rollback được kiểm tra khi migration hỗ trợ rollback
**And** lỗi migration làm check thất bại thay vì bị bỏ qua.

**Given** backend kết nối local, test hoặc RDS staging
**When** ứng dụng khởi động
**Then** connection URL, pool và SSL behavior được lấy từ environment configuration
**And** health endpoint phân biệt được trạng thái API sống với trạng thái database sẵn sàng
**And** credential/connection string không xuất hiện trong logs.

**Given** repository đã có `schema.sql` và Alembic migrations
**When** thiết lập baseline
**Then** migration history hiện có được kiểm kê và dùng làm nguồn triển khai
**And** không tạo một schema song song hoặc tạo trước bảng chỉ phục vụ các story tương lai.

### Story 0.3: Provision AWS staging, storage và container foundation

As a platform developer,
I want a minimal, reproducible AWS staging environment,
So that HeritageGraph components can be deployed and integrated before feature development begins.

**Acceptance Criteria:**

**Given** lựa chọn AWS compute vẫn đang mở
**When** story bắt đầu
**Then** một ADR so sánh phương án hiện có, ECS/Fargate và EC2-based containers theo chi phí, độ phức tạp, thời gian triển khai, inference và rollback
**And** ADR chọn phương án nhỏ nhất đáp ứng staging/demo
**And** EKS hoặc MWAA không được chọn nếu chưa có nhu cầu được chứng minh.

**Given** AWS account và staging configuration hợp lệ
**When** áp dụng infrastructure definition
**Then** staging có container registry ECR, S3 canonical bucket, networking cần thiết và các IAM roles tách theo trách nhiệm
**And** infrastructure có thể được tạo hoặc cập nhật lặp lại mà không sinh resource ngoài kiểm soát
**And** state và secrets không được commit vào repository.

**Given** RDS PostgreSQL staging được kết nối với backend
**When** kiểm tra network access
**Then** RDS không public trực tiếp
**And** chỉ workload/role được cấp quyền mới kết nối được
**And** migration baseline từ Story 0.2 chạy thành công trên staging.

**Given** backend image được đưa lên ECR
**When** triển khai lên compute target đã chọn
**Then** public ingress chỉ expose endpoint cần thiết qua HTTPS
**And** backend truy cập được RDS và S3 bằng IAM/configuration phù hợp
**And** frontend hoặc smoke client gọi được FastAPI health endpoint.

**Given** một raw document, manifest hoặc test asset
**When** workload được cấp quyền ghi/đọc S3
**Then** object được lưu dưới prefix/policy đã quy định
**And** workload không thể thực hiện hành động ngoài quyền tối thiểu của nó
**And** S3 vẫn là canonical MVP object store, không có critical-path dual-write sang R2/Azure.

**Given** staging deployment lỗi hoặc cần loại bỏ
**When** operator làm theo runbook
**Then** có quy trình rollback/cleanup được tài liệu hóa
**And** resource ownership và chi phí dự kiến có thể kiểm tra được.

### Story 0.4: Tự động hóa Jenkins CI/CD và Terraform delivery

As a developer,
I want an automated delivery pipeline with enforceable quality gates,
So that changes reach AWS staging consistently and unsafe builds are rejected before deployment.

**Acceptance Criteria:**

**Given** một pull request thay đổi backend, frontend, migration hoặc infrastructure
**When** Jenkins pipeline chạy
**Then** pipeline chỉ chạy các component checks liên quan nhưng luôn áp dụng lint/type checks và tests bắt buộc
**And** failure ở bất kỳ required gate nào chặn build/deploy
**And** kết quả từng gate được hiển thị rõ.

**Given** thay đổi có database migration
**When** pipeline kiểm tra migration
**Then** migration được chạy trên database kiểm thử sạch
**And** lỗi upgrade hoặc rollback check làm pipeline thất bại
**And** staging không được migrate nếu build chưa vượt qua các gate trước đó.

**Given** thay đổi có Terraform
**When** CI chạy infrastructure checks
**Then** formatting, validation và plan được thực hiện
**And** plan có thể review trước apply
**And** Jenkins deploy role tách biệt với runtime roles và chỉ có quyền cần thiết.

**Given** branch/revision được phép deploy đã vượt qua mọi gate
**When** pipeline build và phát hành component
**Then** container image được gắn immutable revision tag và push lên ECR
**And** staging deploy đúng image revision đó
**And** health/smoke checks chạy sau deploy.

**Given** smoke check sau deploy thất bại
**When** pipeline xử lý deployment failure
**Then** release được đánh dấu thất bại
**And** hệ thống rollback về revision tốt gần nhất hoặc cung cấp thao tác rollback được tài liệu hóa
**And** pipeline không báo thành công giả.

**Given** model hoặc prompt mới cần rollout
**When** delivery được cấu hình
**Then** model/prompt rollout là pipeline riêng với software deployment
**And** không tự động promote 10% → 50% → 100% nếu quality, grounding, latency hoặc error gate chưa đạt.

**Given** credential được Jenkins sử dụng
**When** pipeline ghi log hoặc xuất artifact
**Then** secrets được lấy từ credential store phù hợp
**And** token, password và connection string không xuất hiện trong log/artifact.

### Story 0.5: Thiết lập observability baseline

As an operator,
I want correlated metrics, logs and traces across HeritageGraph,
So that I can detect failures and diagnose requests without exposing sensitive data.

**Acceptance Criteria:**

**Given** một request đi qua frontend và FastAPI
**When** request được xử lý thành công hoặc thất bại
**Then** hệ thống gán hoặc truyền correlation/trace ID
**And** structured logs có service, environment, severity, timestamp và correlation ID
**And** response/log không làm lộ password, token, raw IP hoặc dữ liệu cá nhân nhạy cảm.

**Given** API và dependency hoạt động
**When** Prometheus thu metrics
**Then** có tối thiểu request count, error count, duration histogram và dependency health
**And** metric labels không chứa giá trị unbounded như raw URL, user input hoặc entity ID tùy ý
**And** p50/p95/p99 có thể tính từ dữ liệu thu được.

**Given** một request gọi database hoặc service nội bộ
**When** OpenTelemetry tracing được bật
**Then** trace thể hiện đường đi qua API và dependency adapter phù hợp
**And** span lỗi giữ đủ metadata để chẩn đoán mà không chứa secret hoặc raw sensitive content
**And** trace được gửi tới Tempo/X-Ray target đã cấu hình.

**Given** ứng dụng hoặc pipeline ghi structured logs
**When** Loki thu thập log
**Then** operator có thể lọc theo service, environment, severity và correlation ID
**And** retention/configuration phù hợp môi trường demo được tài liệu hóa.

**Given** một lượt gọi Qwen hoặc grounded QA trong các story sau
**When** Langfuse integration được sử dụng
**Then** trace contract hỗ trợ model, prompt, corpus version, evidence IDs, token usage, latency và grounding result
**And** raw prompt/evidence chỉ được lưu theo privacy policy đã cấu hình
**And** observability failure không làm request nghiệp vụ thất bại.

**Given** telemetry baseline đang chạy
**When** operator mở Grafana
**Then** dashboard hiển thị service health, request/error rate và latency
**And** có alert baseline cho service unavailable, error-rate spike và latency threshold
**And** dashboard/alert definitions được version hóa.

**Given** một smoke request trên AWS staging
**When** request hoàn tất
**Then** operator truy vết được request từ health/API signal qua logs và service trace
**And** smoke test xác nhận telemetry endpoint không public ngoài policy cho phép.

### Story 0.6: Thiết lập design foundations, application shells và API mocks

As a frontend developer,
I want approved design foundations and runnable public/admin application shells backed by API mocks,
So that UI stories can be developed consistently before all backend features are available.

**Acceptance Criteria:**

**Given** UX contract hiện hành
**When** Figma foundations và frontend theme được thiết lập
**Then** color, typography, spacing, radius, elevation và motion tokens có tên semantic thống nhất
**And** mapping giữa Figma tokens và code tokens được tài liệu hóa
**And** contrast cơ bản đáp ứng WCAG 2.1 AA.

**Given** người dùng mở Public Portal shell
**When** điều hướng giữa `/`, `/explore`, `/map`, `/chat` và `/preferences`
**Then** các route có shared heritage-storytelling navigation/layout và placeholder state phù hợp
**And** desktop/mobile giữ cùng hierarchy
**And** shell không giả vờ cung cấp feature chưa được triển khai.

**Given** admin đã vào `/admin/*` shell
**When** điều hướng giữa các khu vực quản trị placeholder
**Then** giao diện dùng Ant Design dashboard/form/table conventions thay vì Tapestry composition
**And** public và admin theme không làm rò style hoặc layout sang nhau
**And** route structure sẵn sàng cho auth guard ở Story 1.1.

**Given** OpenAPI contract hoặc response schema được xác định
**When** frontend gọi API mock
**Then** mock trả response đúng schema cho representative success, empty và error cases
**And** frontend dùng generated/shared types thay vì khai báo payload trùng lặp
**And** contract drift có thể được phát hiện bởi automated check.

**Given** một page đang loading, không có dữ liệu hoặc gặp lỗi
**When** shell render state tương ứng
**Then** có reusable loading, empty và error primitives
**And** focus, keyboard navigation, landmark và accessible name cơ bản hoạt động
**And** trạng thái không chỉ được phân biệt bằng màu sắc.

**Given** frontend shell được chạy local hoặc staging
**When** thực hiện smoke test ở viewport desktop và mobile đại diện
**Then** navigation và route rendering hoạt động không có horizontal overflow ngoài ý muốn
**And** frontend có thể chuyển giữa mock base URL và FastAPI base URL bằng environment configuration
**And** không cần chỉnh source code để đổi môi trường.

### Story 0.7: Thiết lập test harness, fixtures và documentation templates

As a developer,
I want reusable automated test infrastructure and documentation templates,
So that every later story can prove its behavior and leave consistent implementation evidence.

**Acceptance Criteria:**

**Given** backend code cần unit, database hoặc integration test
**When** developer chạy test suite theo documented command
**Then** pytest discovery, markers và test configuration hoạt động nhất quán local/CI
**And** test database được cô lập và reset giữa các test phù hợp
**And** test không phụ thuộc credential hoặc shared staging data.

**Given** story cần representative knowledge data
**When** test sử dụng fixture/factory
**Then** fixture có document, passage, entity và provenance tối thiểu với ID xác định
**And** có thể mở rộng cho draft/published/version-isolation cases
**And** expected result được xác định độc lập với implementation đang test.

**Given** frontend và API contract cần kiểm tra
**When** contract test chạy
**Then** representative success, validation error và service error payload được kiểm tra với schema hiện hành
**And** mismatch giữa generated frontend types/mock và OpenAPI làm test thất bại.

**Given** Public/Admin shell chạy với mock hoặc test backend
**When** Playwright smoke suite chạy
**Then** suite kiểm tra route chính, navigation và một viewport desktop/mobile đại diện
**And** lưu screenshot/trace khi thất bại
**And** selector ưu tiên role/accessible name thay vì phụ thuộc CSS structure dễ vỡ.

**Given** AI/retrieval behavior được thêm trong các epic sau
**When** developer thêm regression case
**Then** harness hỗ trợ fixed query, versioned evidence và deterministic expected gate/result
**And** report có chỗ ghi model, prompt, corpus và evaluation dataset version
**And** test không được coi là pass chỉ vì request không crash.

**Given** một story thay đổi API, database, operations hoặc architecture
**When** story hoàn tất
**Then** có template phù hợp cho API/data docs, migration/rollback note, ADR hoặc runbook
**And** test evidence và demo evidence có vị trí/link convention thống nhất
**And** tài liệu không yêu cầu sao chép cùng một nguồn sự thật vào nhiều nơi.

**Given** Jenkins pipeline từ Story 0.4
**When** test harness được tích hợp
**Then** unit, integration, contract và Playwright smoke checks chạy ở stage phù hợp
**And** failure artifact được giữ để chẩn đoán
**And** required test failure chặn deployment.

### Story 0.8: Thiết lập Figma foundations và component library

**Primary owner:** DES
**Supporting roles:** FE (token mapping and component feasibility review)

As a product designer,
I want reusable Figma foundations and a shared component library,
So that product screens can be designed and implemented with an accessible and consistent visual system.

**Acceptance Criteria:**

**Given** UX requirements và heritage visual direction hiện hành
**When** designer thiết lập Figma foundations
**Then** color, typography, spacing, grid, radius, elevation, icon và motion tokens được định nghĩa bằng semantic names
**And** light/default states và contrast đáp ứng WCAG 2.1 AA
**And** token naming có mapping rõ sang frontend theme.

**Given** các interaction pattern dùng chung của Public Portal và Admin Studio
**When** designer tạo Figma component library
**Then** button, input, select, date field, upload, table, pagination, tabs, modal, drawer, toast, status badge, navigation và data-display components có variants/states cần thiết
**And** component có auto layout, responsive constraints và interactive states
**And** public storytelling components được tách khỏi admin dashboard/form/table components.

**Given** component library sẵn sàng handoff
**When** DES review cùng FE
**Then** Figma library, token definitions, component anatomy, variants và usage guidance được đặt tên/version rõ ràng
**And** component states gồm default, hover, focus, active, disabled, loading, success và error khi áp dụng
**And** FE xác nhận component feasibility trước khi story chuyển done.

### Story 0.9: Thiết kế Figma Admin Console

**Primary owner:** DES
**Supporting roles:** FE (implementation feasibility), BE/DATA (workflow and data contract review)

As a product designer,
I want a complete Admin Console, including its Dashboard and Admin Knowledge Studio screens, built from the approved Figma component library,
So that frontend implementation can follow reviewed workflows, UI states and responsive behavior without guessing requirements.

**Acceptance Criteria:**

**Given** Figma foundations và component library từ Story 0.8
**When** designer bắt đầu thiết kế Admin Console
**Then** Dashboard và các màn hình Admin chỉ dùng approved tokens/components hoặc ghi rõ component mới cần bổ sung
**And** admin dashboard/form/table patterns được tách khỏi Public Portal storytelling patterns
**And** mọi deviation khỏi component library được review trước handoff.

**Given** scope Epic 1 và Epic 2
**When** designer hoàn thiện Admin Dashboard và các màn hình liên quan
**Then** có designs cho Login và Admin Dashboard, Document wizard/list/detail, Passage workspace, Entity/Alias/Place editor, Claim/Timeline/Relation/Narrative editor, Validation Center, Review và Publish flow
**And** mỗi flow có loading, empty, error, success, permission-denied và confirmation states phù hợp
**And** evidence selection không yêu cầu người dùng nhập UUID hoặc foreign key thủ công.

**Given** Admin cần làm việc ở nhiều kích thước màn hình
**When** responsive behavior được đặc tả
**Then** desktop, tablet và minimum supported viewport có layout/hierarchy rõ ràng
**And** keyboard flow, focus order, accessible name và screen-reader notes được ghi cho các interaction phức tạp
**And** cards, tables, editors và workspaces có phương án overflow hoặc alternative layout có chủ đích.

**Given** một end-to-end Admin workflow
**When** reviewer chạy Figma prototype
**Then** prototype thể hiện navigation, create/edit, validation, submit, review và publish transitions với điểm bắt đầu/kết thúc rõ ràng
**And** destructive, blocked, retry và recovery paths được thể hiện
**And** prototype không giả định data, metric hoặc API behavior chưa được BE/DATA xác nhận.

**Given** Admin Console design sẵn sàng handoff
**When** DES review cùng FE, BE và DATA
**Then** Figma pages, prototype links, annotations và acceptance-state inventory được đặt tên/version rõ ràng
**And** API/data assumptions và unresolved questions được ghi thay vì để FE tự suy đoán
**And** FE xác nhận implementation feasibility trước khi story chuyển done.

## Epic 0 Sprint Subtasks

| Parent | Subtask | Primary owner | Priority | Definition of Done |
|---|---|---|---|---|
| 0.1 | 0.1.1 Pin runtime and package manager versions | DEVOPS | Highest | Phiên bản runtime/package manager được pin và lệnh kiểm tra phiên bản chạy đạt. |
| 0.1 | 0.1.2 Create environment templates and secrets policy | DEVOPS | Highest | Template môi trường và chính sách secrets được lưu tài liệu, không chứa secret thật. |
| 0.1 | 0.1.3 Implement startup configuration validation | BE | Highest | Khởi động thất bại rõ ràng khi thiếu/sai cấu hình và đạt với cấu hình hợp lệ. |
| 0.1 | 0.1.4 Document local setup and health checks | DEVOPS | High | Hướng dẫn cài đặt cục bộ và health check được chạy lại thành công. |
| 0.2 | 0.2.1 Provision local PostgreSQL 16 volume and health check | DATA | Highest | PostgreSQL 16 giữ dữ liệu qua restart và health check báo healthy. |
| 0.2 | 0.2.2 Enable pgvector and pg_trgm through migrations | DATA | Highest | Migration bật pgvector/pg_trgm và kiểm tra extension đạt. |
| 0.2 | 0.2.3 Reconcile schema.sql with the Alembic baseline and verify idempotency | DATA | Highest | schema.sql khớp baseline Alembic và chạy migration lặp không đổi schema. |
| 0.2 | 0.2.4 Configure connection pool, SSL, readiness health and log redaction | BE | High | Pool, SSL, readiness và che dữ liệu nhạy cảm được cấu hình và kiểm tra. |
| 0.3 | 0.3.1 Decide the staging compute approach in an ADR | DEVOPS | High | ADR staging compute được phê duyệt với quyết định và hệ quả rõ ràng. |
| 0.3 | 0.3.2 Provision networking, IAM, ECR and S3 with Terraform | DEVOPS | High | Terraform provision thành công networking, IAM, ECR và S3 trên staging. |
| 0.3 | 0.3.3 Define S3 canonical paths, access policies and reconciliation | DEVOPS | High | Path, policy và quy trình reconciliation S3 được định nghĩa và kiểm tra quyền. |
| 0.3 | 0.3.4 Run staging deployment, smoke and repeatability checks | DEVOPS | High | Deploy staging lặp lại thành công và smoke checks đạt. |
| 0.4 | 0.4.1 Build Jenkins pull-request validation stages | DEVOPS | High | Jenkins chạy các stage PR bắt buộc và chặn merge khi thất bại. |
| 0.4 | 0.4.2 Build, scan and push component images to ECR | DEVOPS | High | Image được build, scan đạt policy và push ECR với tag truy vết được. |
| 0.4 | 0.4.3 Add Terraform plan/apply environment gates | DEVOPS | High | Plan được lưu và apply chỉ chạy qua đúng environment gate. |
| 0.4 | 0.4.4 Verify deployment health checks and rollback evidence | DEVOPS | High | Health checks đạt và rollback được thực hiện với evidence lưu lại. |
| 0.5 | 0.5.1 Instrument service and infrastructure metrics with Prometheus | DEVOPS | Medium | Prometheus scrape được metrics dịch vụ/hạ tầng đã định nghĩa. |
| 0.5 | 0.5.2 Centralize structured logs in Loki with redaction | DEVOPS | Medium | Loki truy vấn được structured logs và dữ liệu nhạy cảm được che. |
| 0.5 | 0.5.3 Define Langfuse trace contracts and privacy controls | AI | Medium | Trace contract và privacy controls được tài liệu hóa và kiểm tra payload mẫu. |
| 0.5 | 0.5.4 Create Grafana dashboards, alerts and staging telemetry smoke checks | DEVOPS | Medium | Dashboard/alert hoạt động và telemetry smoke checks staging đạt. |
| 0.6 | 0.6.1 Configure frontend workspace, routes and environment API switching | FE | Highest | Workspace build đạt, routes hoạt động và API đổi đúng theo môi trường. |
| 0.6 | 0.6.2 Build the responsive Public Portal shell and navigation | FE | Highest | Public Portal shell/navigation đạt kiểm tra desktop và mobile. |
| 0.6 | 0.6.3 Build the Admin shell with isolated theme and layout | FE | Highest | Admin shell dùng theme/layout cô lập và routes chính render đúng. |
| 0.6 | 0.6.4 Create OpenAPI-aligned mocks and reusable accessible UI states | FE | Highest | Mocks khớp OpenAPI và UI states dùng lại đạt kiểm tra accessibility. |
| 0.7 | 0.7.1 Set up pytest unit, database and integration harnesses | BE | High | Các harness pytest chạy độc lập và đạt trên CI. |
| 0.7 | 0.7.2 Create deterministic knowledge fixtures and factories | DATA | High | Fixtures/factories tạo dữ liệu tri thức xác định và tái lập được. |
| 0.7 | 0.7.3 Set up frontend contract tests and Playwright smoke harness | FE | High | Contract tests và Playwright smoke suite chạy đạt, lưu artifact khi lỗi. |
| 0.7 | 0.7.4 Set up AI regression harness, evidence templates and CI integration | AI | High | AI regression cases chạy trên CI với evidence template và kết quả xác định. |
| 0.8 | 0.8.1 Define Figma foundations and semantic tokens | DES | Highest | Foundations/token ngữ nghĩa hoàn chỉnh và mapping FE được review. |
| 0.8 | 0.8.2 Build core input, action and navigation components | DES | Highest | Component input/action/navigation có variants và states đã review. |
| 0.8 | 0.8.3 Build data-display and feedback components with variants | DES | Highest | Component data-display/feedback có variants và states đã review. |
| 0.8 | 0.8.4 Document accessibility, usage guidance and FE handoff | DES | High | Hướng dẫn accessibility/usage và gói handoff được FE xác nhận. |
| 0.9 | 0.9.1 Define Admin Console information architecture and end-to-end flows | DES | High | IA và end-to-end flows được review cùng FE/BE/DATA. |
| 0.9 | 0.9.2 Design Login and Admin Dashboard states | DES | High | Login/Admin Dashboard có đầy đủ states và được review. |
| 0.9 | 0.9.3 Design Document, Passage and Knowledge editors | DES | High | Các editor Document, Passage, Knowledge có luồng/states được review. |
| 0.9 | 0.9.4 Design Validation Center, Review and Publish flows | DES | High | Luồng Validation, Review, Publish và recovery states được review. |
| 0.9 | 0.9.5 Complete responsive states, accessibility notes, prototype and handoff | DES | High | Responsive states, accessibility notes, prototype và handoff được xác nhận. |

# Epic 1: Admin Knowledge Studio

Quản trị viên đăng nhập và biên soạn trọn một knowledge package — document, passage, entity/alias/place profile, claim, timeline, relation, narrative và evidence — ở trạng thái draft mà không cần thao tác SQL, UUID hoặc foreign key thủ công.

### Story 1.1: Xác thực, phân quyền và audit cho Admin

As an administrator,
I want to sign in securely and have administrative actions authorized and audited,
So that only permitted users can modify cultural knowledge and every change is accountable.

**Acceptance Criteria:**

**Given** một Admin account được provision hợp lệ
**When** Admin đăng nhập bằng đúng thông tin
**Then** password được kiểm tra bằng Argon2id
**And** session được cấp qua cookie `HttpOnly`, `Secure` trên staging/production và `SameSite` phù hợp
**And** raw password hoặc session token không xuất hiện trong response body, log hoặc trace.

**Given** credential sai hoặc account không được phép đăng nhập
**When** gửi login request
**Then** hệ thống từ chối bằng thông báo không tiết lộ email/account nào tồn tại
**And** không tạo authenticated session
**And** sự kiện thất bại được ghi ở mức đủ để điều tra nhưng không chứa password, token hoặc raw IP.

**Given** request tới `/admin/*` hoặc Admin API
**When** request không có session hợp lệ hoặc không có quyền cần thiết
**Then** UI chuyển tới login hoặc hiển thị access-denied phù hợp
**And** API trả `401` cho unauthenticated hoặc `403` cho unauthorized
**And** không thực hiện partial write.

**Given** Admin đã đăng nhập
**When** session hết hạn hoặc Admin logout
**Then** cookie/session không còn dùng được
**And** protected API từ chối các request tiếp theo
**And** logout nhiều lần không gây lỗi ngoài ý muốn.

**Given** một authenticated Admin thực hiện create, update, submit, review hoặc publish action
**When** service transaction xử lý action
**Then** audit record lưu actor, action, target kind/ID, timestamp và correlation ID
**And** audit record không thể bị sửa/xóa qua Admin CRUD thông thường
**And** failed transaction không để lại trạng thái nghiệp vụ giả thành công.

**Given** login và authorization foundation được kiểm thử
**When** chạy unit/integration/contract tests
**Then** test phân biệt success, invalid credentials, expired session, `401` và `403`
**And** test chứng minh unauthenticated write không thay đổi database
**And** audit output không chứa secret hoặc dữ liệu nhạy cảm bị cấm.

### Story 1.2: Tạo và quản lý source document ở trạng thái draft

As a knowledge manager,
I want to create and manage source documents with complete provenance metadata,
So that cultural knowledge starts from a traceable source without direct database operations.

**Acceptance Criteria:**

**Given** Admin mở Document wizard
**When** tạo source document
**Then** form thu thập URL nguồn, title, region, source type, source tier, observed date, license và raw text/file theo contract
**And** required fields, URL/date/type constraints được hiển thị tại đúng field
**And** UI không yêu cầu nhập UUID hoặc foreign key thủ công.

**Given** payload hợp lệ
**When** Admin lưu document
**Then** FastAPI/service transaction tạo document trong draft corpus revision hiện hành
**And** document mặc định có trạng thái `draft`, không phải `published`
**And** document không xuất hiện trong online serving query
**And** audit record được ghi cho thao tác tạo.

**Given** URL/content hash hoặc metadata trùng với document hiện có
**When** Admin lưu draft
**Then** exact duplicate bị chặn theo business constraint
**And** response chỉ rõ field/candidate gây trùng để Admin sửa hoặc mở record hiện có
**And** không tạo document thứ hai hay object rác.

**Given** raw document/file được lưu trên S3
**When** database write hoặc object write thất bại
**Then** hệ thống không báo lưu thành công
**And** không để lại database row trỏ tới object không tồn tại
**And** orphan object được rollback hoặc đánh dấu cho reconciliation theo policy đã tài liệu hóa.

**Given** Admin tìm hoặc mở document draft
**When** xem danh sách/chi tiết
**Then** có thể lọc/tìm theo title, region, source type và status
**And** metadata, raw-content availability và provenance được hiển thị
**And** loading, empty và error states có hành vi accessible.

**Given** document vẫn thuộc draft revision chưa submit/publish
**When** Admin cập nhật hoặc xóa document
**Then** thay đổi được validation và thực hiện atomically
**And** dependent-record conflict được báo rõ thay vì xóa mồ côi
**And** audit lưu before/after metadata cần thiết.

**Given** document đã thuộc published release
**When** Admin cố sửa hoặc xóa evidence đã publish
**Then** hệ thống từ chối mutation trực tiếp
**And** hướng Admin tạo revision/draft mới thay vì thay đổi historical evidence.

### Story 1.3: Tạo passage và chọn evidence trực tiếp từ nguồn

As a knowledge manager,
I want to create passages from a draft document and select them as evidence visually,
So that downstream knowledge records can cite exact source text without manual IDs.

**Acceptance Criteria:**

**Given** một source document draft có raw text
**When** Admin mở Passage workspace
**Then** raw text và danh sách/preview passage hiển thị song song
**And** passage đang chọn được highlight đúng trên raw text
**And** workspace hỗ trợ keyboard navigation và không chỉ dùng màu để biểu thị selection.

**Given** Admin chọn một đoạn raw text hoặc nhập char span hợp lệ
**When** tạo passage
**Then** `char_start` và `char_end` nằm trong giới hạn document
**And** passage content khớp chính xác substring được tham chiếu theo convention đã quy định
**And** system tự tạo content hash và gắn draft corpus revision
**And** Admin không phải nhập document UUID thủ công.

**Given** char span rỗng, đảo ngược, vượt giới hạn hoặc content không khớp raw text
**When** Admin lưu passage
**Then** FastAPI từ chối với lỗi gắn đúng field/span
**And** không tạo partial passage hoặc evidence record.

**Given** passage có cùng document, span hoặc content hash đã tồn tại trong revision
**When** Admin lưu
**Then** exact duplicate bị chặn
**And** UI dẫn tới passage hiện có hoặc cho phép điều chỉnh selection
**And** không tạo record trùng.

**Given** passage draft hợp lệ
**When** Admin sửa hoặc xóa passage
**Then** content hash/span được tính lại và validation chạy trong transaction
**And** hệ thống chặn xóa nếu passage đang được knowledge record tham chiếu, đồng thời liệt kê dependency
**And** audit record ghi thao tác.

**Given** một form knowledge record cần evidence trong các story sau
**When** Admin mở Evidence Picker
**Then** có thể tìm passage theo document/title/text và chọn trực tiếp từ preview
**And** component trả reference hợp lệ nhưng không yêu cầu người dùng nhập UUID/FK
**And** selected evidence hiển thị source title và excerpt để kiểm tra.

**Given** passage đã thuộc published release
**When** Admin cố sửa nội dung/span
**Then** hệ thống từ chối mutation trực tiếp
**And** yêu cầu tạo passage revision mới để citation lịch sử vẫn bất biến.

### Story 1.4: Quản lý entity, alias và place profile

As a knowledge manager,
I want to create and manage entities, aliases and place profiles with evidence,
So that cultural concepts are canonical, searchable and traceable before publication.

**Acceptance Criteria:**

**Given** Admin mở Entity editor
**When** tạo entity
**Then** form thu thập canonical name, normalized name, type, subtype, scope và status theo registry
**And** entity được gắn draft corpus revision và mặc định không phục vụ online
**And** Admin không phải nhập corpus/entity UUID thủ công.

**Given** canonical/normalized name giống hoặc gần với entity/alias hiện có
**When** Admin nhập hoặc lưu entity
**Then** exact duplicate bị chặn
**And** fuzzy candidates được hiển thị với tên, type và region/context đủ để so sánh
**And** Admin có thể mở candidate thay vì vô tình tạo entity trùng.

**Given** entity draft đã tồn tại
**When** Admin thêm, sửa hoặc xóa alias
**Then** alias được normalize nhất quán với entity resolution contract
**And** alias rỗng, trùng trong cùng entity hoặc xung đột không hợp lệ bị từ chối rõ ràng
**And** mutation được audit và thực hiện atomically.

**Given** entity có type địa điểm
**When** Admin tạo place profile
**Then** có thể nhập tọa độ và các trường địa lý/hành chính theo schema
**And** latitude/longitude được kiểm tra range và cặp giá trị
**And** non-place entity không thể nhận place profile trái constraint.

**Given** entity cần provenance
**When** Admin dùng Evidence Picker từ Story 1.3
**Then** có thể chọn primary evidence và một hoặc nhiều supporting passages
**And** evidence phải thuộc revision/context hợp lệ
**And** UI hiển thị source title và excerpt, không yêu cầu nhập passage ID.

**Given** Admin tìm entity để biên tập hoặc liên kết sau này
**When** tìm theo canonical name, alias, type hoặc region
**Then** kết quả phân biệt canonical name với alias match
**And** draft/published status được hiển thị rõ
**And** loading, empty, duplicate-warning và error states hỗ trợ keyboard/screen reader.

**Given** entity draft đang được knowledge record khác tham chiếu
**When** Admin cố xóa entity
**Then** hệ thống chặn orphan references và liệt kê dependency
**And** không thực hiện partial delete.

**Given** entity/alias/place profile đã thuộc published release
**When** Admin cố sửa trực tiếp
**Then** hệ thống từ chối mutation lịch sử
**And** hướng Admin tạo revision draft mới.

### Story 1.5: Biên soạn typed claims có evidence

As a knowledge manager,
I want to author typed claims for an entity using a governed field registry,
So that factual attributes are validated, versioned and traceable to source passages.

**Acceptance Criteria:**

**Given** Admin chọn một entity draft và `claim_field`
**When** Claim form được hiển thị
**Then** control được sinh theo `value_type`: `text`, `number`, `boolean`, `date`, `year`, `money` hoặc `json`
**And** form hiển thị `label_vi`, default unit và time-sensitive guidance
**And** Admin không nhập entity ID hoặc field code bằng tay.

**Given** Admin nhập claim value
**When** value không khớp kiểu của `claim_field`
**Then** UI/FastAPI báo lỗi tại field trước hoặc khi lưu
**And** database constraint/trigger vẫn từ chối payload không hợp lệ nếu application validation bị bỏ qua
**And** không tạo partial claim.

**Given** một claim hợp lệ
**When** Admin không nhập unit và field có `default_unit`
**Then** default unit được áp dụng nhất quán
**And** unit được hiển thị trong preview trước khi lưu.

**Given** Admin nhập `observed_at`, `valid_from`, `valid_until`, confidence và canonical state
**When** lưu claim
**Then** confidence chỉ chấp nhận từ 0 đến 1
**And** `valid_until` không thể trước `valid_from`
**And** time-sensitive claim yêu cầu metadata thời gian theo contract
**And** claim được lưu ở trạng thái `draft`.

**Given** claim cần provenance
**When** Admin chọn evidence
**Then** phải có một primary passage và có thể có nhiều supporting passages
**And** claim, entity và passages thuộc cùng draft corpus version hợp lệ
**And** source title/excerpt được hiển thị thay vì UUID.

**Given** một claim cùng entity, field và giá trị đã tồn tại trong revision
**When** Admin lưu
**Then** exact duplicate bị chặn hoặc được dẫn tới record hiện có
**And** canonical-state conflict được cảnh báo rõ
**And** không tạo claim trùng ngoài ý muốn.

**Given** claim draft đã tồn tại
**When** Admin sửa hoặc xóa claim
**Then** type, validity, confidence và evidence được validation lại trong transaction
**And** thao tác được audit
**And** published claim không thể bị sửa trực tiếp mà phải tạo revision mới.

### Story 1.6: Biên soạn timeline events và participants

As a knowledge manager,
I want to author evidence-backed timeline events with typed participant roles,
So that an entity’s history can be presented and queried consistently.

**Acceptance Criteria:**

**Given** Admin mở Timeline editor cho một entity
**When** tạo event
**Then** form thu thập title, `year_start`, optional `year_end`, precision, event type, summary, actor và artifact theo schema
**And** precision chỉ nhận `year`, `decade`, `century`, `range` hoặc `circa`
**And** event type được chọn từ registry, không nhập code tự do.

**Given** Admin nhập mốc thời gian
**When** `year_end` nhỏ hơn `year_start` hoặc precision/range không hợp lệ
**Then** UI và FastAPI báo lỗi tại trường liên quan
**And** database constraint vẫn bảo vệ year range
**And** không tạo partial event.

**Given** event có các cá nhân, tổ chức, địa điểm hoặc hiện vật tham gia
**When** Admin thêm participant
**Then** entity được tìm/chọn theo canonical name hoặc alias
**And** role được chọn từ `participant_role` registry
**And** cùng entity/role không bị thêm trùng vào một event
**And** Admin không nhập entity ID hoặc role code thủ công.

**Given** Admin chọn actor hoặc artifact
**When** lưu event
**Then** reference phải trỏ tới entity hợp lệ trong corpus context
**And** type mismatch rõ ràng bị cảnh báo hoặc từ chối theo business rule
**And** deleted/invalid reference không tạo orphan relation.

**Given** timeline event cần provenance
**When** Admin chọn evidence
**Then** phải có primary passage và có thể có supporting passages
**And** event và evidence thuộc cùng draft corpus version
**And** source title/excerpt được hiển thị trong editor.

**Given** event tương đương đã tồn tại cho cùng entity, time range, type và title
**When** Admin lưu
**Then** exact duplicate bị chặn hoặc dẫn tới event hiện có
**And** event cùng thời gian nhưng nội dung khác được phép tồn tại và được trình bày riêng.

**Given** event và participant list hợp lệ
**When** Admin lưu hoặc cập nhật
**Then** event, participants và evidence được ghi atomically ở trạng thái `draft`
**And** thao tác được audit
**And** failure ở bất kỳ phần nào rollback toàn bộ thay đổi.

**Given** timeline event đã thuộc published release
**When** Admin cố sửa hoặc xóa trực tiếp
**Then** hệ thống từ chối mutation lịch sử
**And** yêu cầu tạo revision draft mới.

### Story 1.7: Xây dựng typed entity relations

As a knowledge manager,
I want to connect two entities with a governed predicate and supporting evidence,
So that graph relationships remain valid, explainable and queryable.

**Acceptance Criteria:**

**Given** Admin mở Relation builder
**When** chọn subject, predicate và object
**Then** UI hiển thị cấu trúc `subject ─ predicate → object`
**And** subject/object được tìm theo canonical name hoặc alias
**And** predicate được chọn từ registry đóng, không nhập code hoặc UUID thủ công.

**Given** predicate có `is_symmetric` hoặc `inverse_of`
**When** Admin chọn predicate
**Then** builder hiển thị semantics/inverse phù hợp để Admin kiểm tra hướng quan hệ
**And** không tự tạo inverse relation ngoài contract đã quy định.

**Given** subject và object giống nhau
**When** Admin lưu relation
**Then** UI, FastAPI và database từ chối self-loop
**And** không tạo partial relation/evidence.

**Given** cùng subject, predicate, object và corpus version đã tồn tại
**When** Admin lưu
**Then** exact triple duplicate bị chặn và record hiện có được hiển thị
**And** không hợp nhất âm thầm các evidence hoặc confidence khác nhau.

**Given** Admin nhập confidence và evidence
**When** lưu relation
**Then** confidence chỉ chấp nhận từ 0 đến 1
**And** primary passage là bắt buộc, supporting passages là tùy chọn
**And** relation, entities và passages thuộc cùng draft corpus context.

**Given** relation hợp lệ
**When** Admin tạo, cập nhật hoặc xóa
**Then** relation và evidence được ghi atomically ở trạng thái `draft`
**And** thao tác được audit
**And** published relation không thể bị sửa trực tiếp mà phải tạo revision mới.

### Story 1.8: Biên soạn narrative sections có evidence

As a knowledge manager,
I want to compose ordered Markdown narrative sections for an entity with source evidence,
So that published heritage content can tell a coherent story without losing provenance.

**Acceptance Criteria:**

**Given** Admin mở Narrative editor cho một entity
**When** tạo section
**Then** section code được chọn từ registry được phép, gồm tổng quan, tên gọi, khởi lập, vai trò lịch sử, kiến trúc, hiện vật, nhân vật, biến động hiện đại hoặc tham quan
**And** form thu thập title, Markdown body và order index
**And** Admin không nhập entity ID hoặc section code tự do.

**Given** cùng entity, section code và corpus version đã có section
**When** Admin tạo thêm
**Then** exact section duplicate bị chặn và section hiện có được mở để chỉnh sửa
**And** section khác code vẫn được phép tồn tại.

**Given** Admin soạn Markdown
**When** mở preview
**Then** headings, lists, links và emphasis được render nhất quán với public content contract
**And** unsafe HTML/script bị sanitize
**And** editor/preview dùng được bằng keyboard và có accessible labels.

**Given** narrative section cần provenance
**When** Admin chọn evidence
**Then** một primary passage là bắt buộc và supporting passages có thể chọn nhiều
**And** selected sources hiển thị title/excerpt thay vì UUID
**And** section và evidence thuộc cùng draft corpus version.

**Given** Admin thay đổi order index hoặc nội dung
**When** lưu narrative package
**Then** ordering, Markdown và evidence được validation và ghi atomically
**And** section mặc định ở trạng thái `draft`
**And** thao tác được audit.

**Given** narrative section đã thuộc published release
**When** Admin cố sửa hoặc xóa trực tiếp
**Then** hệ thống từ chối mutation lịch sử
**And** yêu cầu tạo revision draft mới.

# Epic 2: Kiểm định và phát hành corpus đáng tin cậy

Biên tập viên submit draft để Airflow kiểm tra sâu, tạo embedding/index/manifest, xử lý issues, review và publish một corpus release atomically; dashboard cho biết sức khỏe và khả năng phục vụ của từng release.

### Story 2.1: Submit draft revision và tạo validation run idempotent

As a knowledge manager,
I want to submit a draft corpus revision for asynchronous validation,
So that deep validation runs once per logical submission without blocking normal authoring saves.

**Acceptance Criteria:**

**Given** một authenticated Admin có draft revision
**When** Admin chọn Submit for Validation
**Then** FastAPI thực hiện preflight checks tối thiểu về revision, ownership/status và required package records
**And** save thông thường không tự trigger Airflow
**And** submission không làm draft trở thành published.

**Given** submission hợp lệ với idempotency key mới
**When** service xử lý request
**Then** validation run được tạo atomically với revision ID, requester, timestamps và trạng thái ban đầu
**And** run ID được trả ngay để UI theo dõi bất đồng bộ
**And** thao tác được audit.

**Given** cùng revision và idempotency key được gửi lại
**When** request retry do timeout hoặc network failure
**Then** service trả lại validation run đã tồn tại
**And** không tạo run hoặc DAG execution thứ hai.

**Given** idempotency key đã được dùng cho revision/payload khác
**When** client tái sử dụng key
**Then** API trả conflict rõ ràng
**And** không thay đổi run hiện có.

**Given** nhiều request submit đồng thời cùng revision
**When** service xử lý concurrency
**Then** database uniqueness/transaction bảo đảm chỉ một logical run được tạo
**And** các request còn lại nhận cùng run hoặc conflict xác định.

**Given** validation run đã commit
**When** Airflow trigger thành công
**Then** run lưu external DAG/run reference và chuyển sang trạng thái queued/running phù hợp
**And** correlation ID nối được API submission với Airflow execution.

**Given** Airflow trigger thất bại sau khi run đã được tạo
**When** service ghi nhận lỗi
**Then** run có trạng thái retryable/trigger-failed rõ ràng
**And** retry dùng lại cùng logical run thay vì tạo run mới
**And** UI không báo validation đang chạy nếu DAG chưa được trigger.

**Given** revision thay đổi sau một submission
**When** Admin muốn kiểm định nội dung mới
**Then** phải tạo submission/version identity mới
**And** report của run cũ vẫn tham chiếu đúng snapshot/revision đã kiểm định.

### Story 2.2: Chạy Airflow deep validation và ghi validation issues

As a knowledge manager,
I want the submitted knowledge package to be checked deeply with actionable issues,
So that I can correct invalid or incomplete records before indexes or a release are prepared.

**Acceptance Criteria:**

**Given** validation run đã được trigger cho một revision snapshot
**When** Airflow bắt đầu deep validation
**Then** pipeline chỉ đọc dữ liệu thuộc đúng snapshot/revision đã submit
**And** trạng thái hiện tại cùng thời điểm bắt đầu/kết thúc của từng stage được ghi nhận
**And** thay đổi draft về sau không làm đổi kết quả của run đang thực hiện.

**Given** package chứa document, passage, entity, claim, timeline, relation và narrative
**When** validation stages chạy
**Then** hệ thống kiểm required fields, type/range, foreign key, exact duplicate, provenance và corpus-version consistency
**And** business constraints của từng record type được kiểm tra
**And** lỗi chặn chất lượng được phân loại là `error`, vấn đề cần xem xét được phân loại là `warning`.

**Given** một validation rule phát hiện vấn đề
**When** issue được ghi
**Then** issue chứa run, stage, severity, rule/code, record kind/ID, field/path và thông báo có thể hành động
**And** UI có đủ reference để mở đúng record cần sửa
**And** issue không yêu cầu Admin đọc Airflow log để xác định đối tượng lỗi.

**Given** cùng run/stage được retry
**When** pipeline ghi lại kết quả
**Then** issues được upsert/reconcile theo identity ổn định
**And** không sinh issue trùng chỉ vì retry
**And** issue không còn đúng sau lần kiểm tra lại được đánh dấu giải quyết hoặc thay thế theo policy.

**Given** một stage validation thất bại do lỗi vận hành
**When** run dừng
**Then** run không được đánh dấu pass
**And** stage lỗi, thông báo an toàn và kết quả đã ghi được giữ lại để chẩn đoán
**And** retry tiếp tục an toàn mà không tạo logical run mới.

**Given** validation có bất kỳ `error` chưa giải quyết
**When** pipeline chuẩn bị chuyển sang embedding/indexing hoặc publish
**Then** bước sau bị chặn
**And** warnings được hiển thị để review nhưng không tự biến thành pass/fail ngoài policy đã định.

**Given** validation hoàn tất
**When** Admin xem summary
**Then** tổng số error/warning và kết quả theo stage khớp với issue records
**And** metrics/logs/traces liên kết được bằng validation run/correlation ID
**And** Airflow không có quyền tự publish corpus.

### Story 2.3: Tạo embeddings, indexes và reproducible manifest

As a knowledge manager,
I want every validated revision prepared as one reproducible serving package,
So that search, graph and chatbot components can use consistent artifacts after publication.

**Acceptance Criteria:**

**Given** validation run hoàn tất và không còn blocking error
**When** preparation pipeline bắt đầu
**Then** passages được chia thành semantic chunks theo versioned chunking contract
**And** mỗi chunk có stable ID, source passage reference và content hash
**And** cùng input/configuration tạo lại cùng chunk identities.

**Given** chunks cần vector embedding
**When** embedding stage chạy
**Then** model, model version và vector dimension khớp embedding contract
**And** vector có dimension sai bị từ chối thay vì ghi lẫn vào index
**And** chunk không đổi có thể tái sử dụng artifact theo content hash và contract version.

**Given** validated records và chunks đã sẵn sàng
**When** indexing stages chạy
**Then** lexical, accent-insensitive/trigram, vector và graph projection artifacts đều gắn cùng corpus revision
**And** artifacts được ghi vào staging namespace, chưa được online consumers sử dụng
**And** partial artifacts không được đánh dấu ready.

**Given** mọi preparation stage thành công
**When** pipeline tạo manifest
**Then** manifest ghi corpus revision, chunk IDs/hashes, embedding contract, index versions, graph projection version, record counts và artifact checksums/locations
**And** manifest được lưu có version trên S3
**And** secrets hoặc private infrastructure credentials không xuất hiện trong manifest.

**Given** cùng revision/configuration được retry
**When** pipeline ghi chunks, embeddings, indexes hoặc manifest
**Then** writes là idempotent hoặc được reconcile theo deterministic artifact identity
**And** không sinh duplicate serving package
**And** artifact stale/partial được thay thế hoặc dọn theo policy đã tài liệu hóa.

**Given** bất kỳ preparation stage hoặc manifest verification thất bại
**When** run kết thúc
**Then** release không được đánh dấu publish-ready
**And** active published artifacts hiện tại không bị thay đổi
**And** stage/error được ghi để retry và quan sát.

### Story 2.4: Theo dõi Validation Center, sửa lỗi và resubmit

As a knowledge manager,
I want to see validation progress and navigate directly to records that need correction,
So that I can repair a failed package and submit a clean revision without reading infrastructure logs.

**Acceptance Criteria:**

**Given** Admin mở Validation Center
**When** có validation runs
**Then** danh sách hiển thị revision, run status, current stage, thời gian, error count và warning count
**And** queued, running, failed, passed và retryable states được phân biệt bằng text/icon chứ không chỉ màu
**And** loading, empty, stale và service-error states được hiển thị rõ.

**Given** một run có issues
**When** Admin mở quality report
**Then** có thể lọc theo severity, stage, record kind và rule
**And** mỗi issue hiển thị thông báo, field/path, source context khả dụng và trạng thái hiện tại
**And** tổng số hiển thị khớp issue records của run.

**Given** issue tham chiếu một knowledge record
**When** Admin chọn Fix/Open
**Then** UI mở đúng editor và record cần sửa
**And** giữ context về run/issue để Admin quay lại report
**And** Admin không phải sao chép UUID hoặc tra database.

**Given** run thất bại vì lỗi vận hành và snapshot không đổi
**When** Admin chọn Retry
**Then** hệ thống retry cùng logical run/snapshot an toàn
**And** không tạo issue/artifact trùng
**And** action và kết quả được audit.

**Given** Admin đã sửa knowledge content
**When** chọn Resubmit
**Then** hệ thống tạo submission/run mới cho revision snapshot mới
**And** report cũ vẫn bất biến để đối chiếu
**And** UI cho biết issues nào đã giải quyết, còn tồn tại hoặc mới xuất hiện theo rule/record identity.

**Given** Admin không có quyền validation/retry/resubmit
**When** cố thực hiện action
**Then** API/UI từ chối phù hợp
**And** không trigger Airflow hoặc thay đổi run.

### Story 2.5: Human review và atomic corpus publish

As a human reviewer,
I want to inspect a validated release and explicitly approve or reject it before atomic publication,
So that unreviewed or partially activated knowledge never reaches users.

**Acceptance Criteria:**

**Given** release candidate đã validation pass và serving package ready
**When** Reviewer mở Review workspace
**Then** workspace hiển thị revision diff, provenance summary, warnings, conflicting sources, manifest/index status và validation history
**And** Reviewer có thể đi tới record/evidence liên quan
**And** dữ liệu draft không được hiển thị như đã published.

**Given** candidate còn blocking error, preparation chưa ready hoặc manifest không hợp lệ
**When** Reviewer cố approve/publish
**Then** action bị chặn với danh sách gate chưa đạt
**And** Airflow pass giả hoặc warning bị đổi thành pass ngoài policy không thể bỏ qua gate.

**Given** Reviewer quyết định reject
**When** nhập lý do và xác nhận
**Then** candidate giữ trạng thái không published
**And** decision, reviewer, timestamp và note được audit
**And** active release hiện tại không thay đổi.

**Given** Reviewer approve một candidate đủ điều kiện
**When** mở Publish confirmation
**Then** UI hiển thị release/version sẽ kích hoạt, gates đã pass, artifact manifest và rollback/retire path
**And** publish chỉ tiếp tục sau explicit confirmation
**And** Airflow không trực tiếp gọi publish.

**Given** publish được xác nhận
**When** Publishing Service activate release
**Then** database transaction đảm bảo release mới trở thành active và release trước được chuyển trạng thái theo policy như một thao tác nhất quán
**And** online release/artifact pointer chỉ chuyển sang serving package đã verify
**And** publish event, reviewer và manifest identity được audit.

**Given** transaction, artifact activation hoặc concurrent publish gặp lỗi
**When** publish không hoàn tất đầy đủ
**Then** online consumers tiếp tục dùng release tốt gần nhất
**And** không tồn tại trạng thái database mới nhưng index cũ được coi là cùng release
**And** lỗi/conflict được báo rõ để retry hoặc review lại.

### Story 2.6: Bảo đảm published corpus version isolation

As an end user,
I want each request to use one complete published corpus version,
So that pages, recommendations and chatbot answers never mix old and new knowledge.

**Acceptance Criteria:**

**Given** một online request bắt đầu
**When** service resolve active release
**Then** release ID được pin cho toàn bộ vòng đời request
**And** database, lexical/vector indexes, graph projection và evidence queries đều dùng release đó
**And** response/trace ghi release ID phù hợp.

**Given** release mới được publish trong khi request cũ đang chạy
**When** request cũ tiếp tục retrieval hoặc persistence
**Then** request vẫn hoàn tất trên release đã pin
**And** request mới có thể dùng release mới
**And** không trộn artifacts của hai release.

**Given** record có trạng thái draft, retired, withdrawn hoặc thuộc release khác
**When** online consumer truy vấn
**Then** record không xuất hiện trong kết quả serving của active release
**And** repository/service boundary áp dụng filter thay vì phụ thuộc endpoint tự nhớ lọc.

**Given** một required artifact của pinned release thiếu hoặc checksum/version không khớp
**When** request cần artifact đó
**Then** service trả trạng thái unavailable/degraded phù hợp thay vì fallback âm thầm sang release khác
**And** không tạo answer, citation hoặc recommendation từ mixed versions
**And** failure được đo và trace.

**Given** response factual được lưu hoặc trả về
**When** hệ thống ghi evidence/citation
**Then** corpus release ID được lưu cùng response/evidence
**And** cited passage của published release vẫn bất biến để truy vết lịch sử.

**Given** version isolation được kiểm thử
**When** chạy concurrent publish và online-request integration tests
**Then** tests chứng minh không có draft leakage hoặc cross-version reads
**And** expected values kiểm tra đúng record/version, không chỉ kiểm tra request không crash.

### Story 2.7: Hiển thị corpus health và publish readiness dashboard

**Primary owner:** FE
**Supporting roles:** DES (design QA), BE/DATA (dashboard API and operational data contracts)

As a knowledge manager,
I want one dashboard showing corpus, validation, index and evaluation health,
So that I can know whether the current draft and published releases are safe and ready to serve.

**Acceptance Criteria:**

**Given** Admin mở dashboard
**When** dữ liệu vận hành khả dụng
**Then** dashboard hiển thị current draft release, active published release, validation queue, issue counts, review status và publish eligibility
**And** mỗi trạng thái có timestamp/freshness
**And** stale hoặc unavailable data không được trình bày như healthy.

**Given** corpus health data khả dụng
**When** dashboard render
**Then** hiển thị record counts theo loại/status, provenance gaps, duplicate/quality summary và graph coverage phù hợp
**And** số liệu liên kết tới report hoặc filtered records có thể hành động
**And** dashboard không tự sửa dữ liệu.

**Given** serving artifacts đã được chuẩn bị hoặc publish
**When** xem index/model health
**Then** dashboard hiển thị manifest identity, lexical/vector/graph status, embedding/model contract, prompt/model version liên quan và last successful build
**And** artifact/release mismatch được đánh dấu blocking hoặc degraded rõ ràng.

**Given** evaluation reports tồn tại
**When** dashboard hiển thị quality metrics
**Then** citation faithfulness, citation coverage, abstention accuracy, retrieval recall và latency được gắn với model, prompt, corpus và dataset versions
**And** thiếu metric không được hiển thị như đạt target.

**Given** một validation, pipeline, index hoặc publish gate lỗi
**When** operator xem dashboard hoặc alert
**Then** có link tới run/release/correlation ID liên quan
**And** Prometheus/Grafana/Langfuse signals hỗ trợ chẩn đoán thay vì thay thế source-of-truth status
**And** sensitive content, password, token và raw IP không xuất hiện.

**Given** người dùng không có quyền quản trị
**When** truy cập dashboard API/UI
**Then** access bị từ chối phù hợp
**And** corpus operational details không bị lộ ra public surface.

**Given** component library và Admin Console handoff từ Stories 0.8–0.9 cùng Admin shell từ Story 0.6
**When** FE triển khai `/admin`
**Then** layout, typography, spacing, components và responsive behavior bám approved Figma design
**And** FE dùng shared/generated API types thay vì hard-code production metrics
**And** visual deviations cần được DES chấp thuận hoặc ghi lại.

**Given** dashboard đang loading, không có dữ liệu, lỗi một phần hoặc thất bại hoàn toàn
**When** UI render trạng thái tương ứng
**Then** có loading skeleton, empty guidance, partial-data warning và retryable error state đúng phạm vi
**And** một widget lỗi không gây blank page cho toàn dashboard
**And** status không chỉ được phân biệt bằng màu sắc.

**Given** viewport desktop, tablet và minimum supported width
**When** chạy component/Playwright tests và design QA
**Then** dashboard không có horizontal overflow ngoài chủ đích
**And** keyboard navigation, landmarks và focus order hoạt động
**And** representative rendered states được DES đối chiếu với Figma trước khi story done.

# Epic 3: Cổng khám phá và kể chuyện di sản

Người dùng tìm và chọn published heritage content qua Home, Explore/Library, bản đồ 2D Huế–Đà Nẵng và Content Landing; từ đó tiếp tục sang trải nghiệm scene, Chat, Recommendation hoặc nội dung liên quan khi các capability tương ứng khả dụng.

### Story 3.1: Khám phá các trải nghiệm di sản nổi bật

As a visitor,
I want to browse featured heritage experiences from the public home page,
So that I can quickly choose a place or story to explore without knowing what to search for first.

**Acceptance Criteria:**

**Given** người dùng mở trang Home
**When** active published corpus có featured content
**Then** trang hiển thị các nhóm nội dung nổi bật theo cấu hình biên tập
**And** mọi card đều thuộc cùng published corpus release đã pin
**And** draft, withdrawn hoặc content thuộc release khác không xuất hiện.

**Given** một experience card được hiển thị
**When** người dùng xem card
**Then** card ưu tiên hình ảnh và tên trải nghiệm, không nhồi timeline, nguồn hoặc mô tả dài
**And** có hai hành động rõ ràng để tiếp tục khám phá và mở Content Landing
**And** button/link có accessible name và keyboard focus rõ ràng.

**Given** người dùng chọn hành động khám phá
**When** điều hướng sang Explore
**Then** context phù hợp như khu vực, chủ đề hoặc loại nội dung được truyền qua URL/state có thể chia sẻ
**And** back navigation đưa người dùng về đúng vị trí trên Home.

**Given** người dùng chọn mở nội dung
**When** Content Landing tồn tại trong release hiện tại
**Then** điều hướng tới đúng content slug/ID
**And** không dùng mock hoặc dữ liệu từ release khác.

**Given** ảnh card chưa tải, lỗi hoặc nằm ngoài viewport
**When** Home render
**Then** ảnh dùng kích thước responsive, placeholder/fallback và lazy loading phù hợp
**And** lỗi ảnh không làm card hoặc navigation mất khả dụng
**And** layout không nhảy bất thường khi ảnh hoàn tất.

**Given** Home không có featured content hoặc API lỗi
**When** trang tải
**Then** hiển thị empty/error state có hướng đi tiếp rõ ràng
**And** không hiển thị trang trắng hoặc dữ liệu draft làm fallback.

### Story 3.2: Tìm kiếm và lọc kho nội dung di sản

As a visitor,
I want to search and filter the published heritage library,
So that I can find experiences relevant to a name, region or cultural category.

**Acceptance Criteria:**

**Given** người dùng mở Explore/Library
**When** chưa nhập điều kiện
**Then** trang hiển thị published experiences có phân trang hoặc incremental loading xác định
**And** card dùng cùng visual/action contract với Home
**And** không tải toàn bộ media hoặc toàn bộ corpus cùng lúc.

**Given** người dùng nhập từ khóa
**When** thực hiện tìm kiếm
**Then** hệ thống tìm trên published content theo tên chuẩn và alias phù hợp
**And** query được normalize theo search contract
**And** kết quả không gọi Qwen chỉ để xếp hạng danh sách Explore.

**Given** người dùng chọn region hoặc category filters
**When** áp dụng riêng lẻ hoặc kết hợp
**Then** kết quả chỉ chứa records đáp ứng mọi filter đang hoạt động
**And** hỗ trợ ít nhất Huế, Đà Nẵng và các nhóm nội dung trong phạm vi dự án
**And** filter state được thể hiện trong URL để reload/share không mất lựa chọn.

**Given** query/filter không có kết quả
**When** search hoàn tất
**Then** trang hiển thị empty state, điều kiện đang áp dụng và cách xóa/sửa điều kiện
**And** không tự thay bằng kết quả không liên quan hoặc draft content.

**Given** request chậm, lỗi hoặc hết trang
**When** Explore cập nhật kết quả
**Then** loading, retry, end-of-results và stale-result states được phân biệt rõ
**And** keyboard/screen reader nhận được thông báo thay đổi kết quả
**And** card cũ không bị gắn nhầm với query mới.

### Story 3.3: Khám phá địa điểm trên bản đồ 2D Huế–Đà Nẵng

As a visitor,
I want to discover published heritage experiences on a two-dimensional map,
So that I can understand where places are located and enter an experience geographically.

**Acceptance Criteria:**

**Given** người dùng mở `/map`
**When** bản đồ overview tải
**Then** hiển thị bản đồ 2D Việt Nam, không phải globe hoặc trái đất 3D
**And** Huế và Đà Nẵng được thể hiện bằng hai điểm/vùng nhấn sáng
**And** animation tôn trọng reduced-motion preference.

**Given** người dùng chọn Huế hoặc Đà Nẵng
**When** bản đồ chuyển sang regional view
**Then** hiển thị các marker của published places có tọa độ hợp lệ trong khu vực đó
**And** marker thuộc cùng pinned corpus release
**And** content thiếu hoặc có tọa độ sai không được đặt tại vị trí giả.

**Given** người dùng chọn marker
**When** place preview mở
**Then** preview hiển thị hình ảnh, tên và các hành động khám phá/mở Content Landing theo cùng contract với card
**And** chỉ một preview active được liên kết rõ với marker đang chọn
**And** đóng preview trả focus về marker.

**Given** người dùng không thể hoặc không muốn thao tác trực tiếp với map
**When** dùng keyboard, screen reader hoặc chọn list view
**Then** có danh sách địa điểm tương đương về nội dung và hành động
**And** lựa chọn trong list đồng bộ với marker tương ứng
**And** map không phải con đường duy nhất để truy cập content.

**Given** viewport mobile
**When** người dùng chọn khu vực hoặc marker
**Then** preview/list hiển thị bằng layout hoặc bottom sheet không che mất toàn bộ ngữ cảnh
**And** thao tác đóng, cuộn và focus hoạt động rõ ràng.

**Given** map tiles/data lỗi
**When** map không render được
**Then** danh sách địa điểm Huế–Đà Nẵng vẫn hoạt động
**And** không hiển thị trang trắng hoặc chặn đường tới Content Landing.

### Story 3.4: Xem Content Landing trước khi bắt đầu trải nghiệm scene

As a visitor,
I want to review the identity and context of a heritage experience before starting it,
So that I understand what I am about to explore and can choose my next action.

**Acceptance Criteria:**

**Given** người dùng mở một Content Landing hợp lệ
**When** content thuộc active published release
**Then** trang hiển thị ảnh đại diện, tên, subtitle/mô tả ngắn, khu vực, loại nội dung và provenance/partner information phù hợp
**And** response và trace gắn cùng pinned corpus release
**And** không hiển thị draft hoặc mixed-version data.

**Given** content có scene experience đã publish và sẵn sàng
**When** landing render
**Then** hiển thị hành động `Bắt đầu trải nghiệm` theo published scene capability/route contract
**And** landing không tự tải model 3D, audio hoặc toàn bộ scene assets trước khi người dùng bắt đầu.

**Given** scene experience chưa khả dụng
**When** landing render
**Then** trang vẫn cung cấp thông tin giới thiệu, nguồn và nội dung liên quan
**And** không hiển thị dead link hoặc giả vờ rằng trải nghiệm đã sẵn sàng
**And** trạng thái khả dụng được diễn đạt rõ ràng.

**Given** content có related published experiences
**When** người dùng xem phần liên quan
**Then** có thể tiếp tục tới Content Landing khác hoặc Explore context phù hợp
**And** related links không trỏ tới draft/withdrawn records
**And** back navigation giữ được hành trình trước đó.

**Given** hero image hoặc media preview lỗi
**When** trang render
**Then** fallback image/state được hiển thị nhưng title, description, provenance và navigation vẫn hoạt động
**And** không tải 3D/audio làm fallback tự động.

**Given** content không tồn tại trong pinned release
**When** route được mở
**Then** hiển thị not-found state với đường quay lại Home, Explore hoặc Map
**And** không fallback sang cùng ID ở draft hay release khác.

**Given** Content Landing được đo trong môi trường mục tiêu
**When** tải representative published content
**Then** đáp ứng ngân sách tải trang chi tiết ≤3 giây theo điều kiện đo đã ghi nhận
**And** desktop/mobile duy trì hierarchy, focus order và không có horizontal overflow ngoài ý muốn.

# Epic 4: Trợ lý hỏi đáp có căn cứ

Người dùng hỏi bằng tiếng Việt từ trang Chat hoặc panel bên cạnh Content; hệ thống xác định đúng thực thể và ý định, tìm evidence trong một published corpus release, dùng Qwen3-4B để diễn đạt, rồi chỉ trả `answered`, `clarify` hoặc `abstained` sau khi kiểm tra citation và grounding.

### Story 4.1: Hiểu câu hỏi và xác định đúng thực thể

As a user,
I want the assistant to understand Vietnamese names, aliases and typing variations,
So that my question is connected to the correct heritage entity or I am asked to clarify.

**Acceptance Criteria:**

**Given** người dùng gửi câu hỏi tiếng Việt
**When** query understanding bắt đầu
**Then** hệ thống giữ nguyên raw query và tạo normalized query theo contract
**And** xử lý nhất quán chữ hoa/thường, dấu tiếng Việt, khoảng trắng và biến thể ký tự
**And** normalization không làm mất raw text cần hiển thị hoặc audit.

**Given** câu hỏi chứa canonical name hoặc alias đã review
**When** entity resolution chạy
**Then** canonical name exact, normalized alias exact và accent-insensitive match được ưu tiên theo thứ tự xác định
**And** typo/fuzzy matching chỉ dùng trong ngưỡng đã hiệu chỉnh
**And** chỉ entity thuộc pinned published release và `in_scope` mới được chọn để trả lời.

**Given** có đúng một candidate vượt ngưỡng tin cậy
**When** resolver hoàn tất
**Then** trả entity ID/canonical name cùng match reason có thể trace
**And** context hint từ Content Landing được kiểm tra chứ không tự động ghi đè nội dung câu hỏi.

**Given** có nhiều candidate hợp lý hoặc tên không đủ phân biệt
**When** resolver không thể chọn an toàn
**Then** terminal result là `clarify`
**And** response đưa ra các lựa chọn ngắn gọn có thông tin phân biệt như loại hoặc khu vực
**And** hệ thống không chọn ngẫu nhiên một entity.

**Given** câu hỏi không cần entity cụ thể hoặc không tìm thấy entity
**When** resolver hoàn tất
**Then** contract ghi rõ `entity_ids`, `needs_clarification` và trạng thái scope
**And** query generic hợp lệ có thể đi tiếp
**And** entity ngoài phạm vi không được giả thành entity trong corpus.

**Given** resolver được kiểm thử
**When** chạy cases tên chuẩn, alias, không dấu, lỗi gõ, trùng tên và ngoài phạm vi
**Then** expected entity/clarify outcome được xác minh cụ thể
**And** test không chỉ kiểm tra request không crash.

### Story 4.2: Xác định ý định và lập kế hoạch tìm bằng chứng

As a user,
I want the assistant to recognize what kind of answer I need,
So that it looks in the right knowledge structures instead of applying one generic search to every question.

**Acceptance Criteria:**

**Given** query đã normalized và entity resolution đã hoàn tất hoặc không cần entity
**When** intent router chạy
**Then** phân loại vào một trong `overview`, `field`, `timeline`, `relationship`, `section`, `comparison`, `open_text` hoặc `out_of_scope`
**And** output ghi confidence/reason phù hợp để trace
**And** trường hợp dưới ngưỡng được clarify hoặc xử lý theo fallback đã định.

**Given** query chứa field, khoảng thời gian hoặc relation request có thể nhận biết
**When** router tạo structured query contract
**Then** contract điền `field_code`, `time_range` hoặc `requested_relations` khi phù hợp
**And** không tự phát minh field/predicate ngoài registry.

**Given** intent đã xác định
**When** Query Planner lập kế hoạch
**Then** planner chọn danh sách operator nhỏ, xác định trước và phù hợp intent
**And** plan ghi input, limit/budget và thứ tự operator cần chạy
**And** planner không sinh SQL tự do hoặc hoạt động như autonomous agent.

**Given** câu hỏi so sánh hoặc cần nhiều loại evidence
**When** planner tạo multi-operator plan
**Then** các nhánh evidence cần thiết được nêu rõ và cùng pin một corpus release
**And** duplicate operator không được chạy chỉ vì cùng dữ kiện xuất hiện trong nhiều nhánh.

**Given** intent là `out_of_scope`
**When** planning hoàn tất
**Then** hệ thống không chạy retrieval/generation tốn kém không cần thiết
**And** trả trạng thái phù hợp, không bịa câu trả lời ngoài phạm vi.

**Given** router/planner được kiểm thử
**When** chạy representative questions cho tám intent
**Then** expected intent, fields và operator plan được so sánh với gold set
**And** thay đổi prompt/rule làm lệch plan được phát hiện bởi regression tests.

### Story 4.3: Tìm evidence từ facts, timeline, graph, narrative và text

As a user,
I want the assistant to retrieve evidence that matches my question,
So that answers are based on the most appropriate published knowledge rather than model memory.

**Acceptance Criteria:**

**Given** plan yêu cầu exact fact
**When** Exact operator chạy
**Then** lấy claim/canonical value phù hợp entity, field, validity và pinned release
**And** trả supporting passage references
**And** stale/time-sensitive value không được trình bày như hiện hành ngoài validity contract.

**Given** plan yêu cầu sự kiện hoặc chronology
**When** Timeline operator chạy
**Then** lọc timeline events theo entity, event type và time range phù hợp
**And** giữ actor/participant/artifact cùng evidence
**And** sắp xếp theo time semantics đã định.

**Given** plan yêu cầu quan hệ
**When** Graph operator chạy
**Then** traversal giới hạn 1–2 hop qua predicate allowlist phù hợp intent
**And** mọi node/edge thuộc cùng pinned published release
**And** path và supporting passages được trả để giải thích kết quả.

**Given** plan yêu cầu nội dung chuyên đề
**When** Section operator chạy
**Then** lấy narrative sections đúng entity/section intent và evidence liên kết
**And** không thay narrative đã review bằng model-generated summary không nguồn.

**Given** plan yêu cầu tìm trong văn bản hoặc paraphrase
**When** Text operator chạy
**Then** kết hợp PostgreSQL FTS, pg_trgm/accent-insensitive search và vector channel theo contract
**And** kết quả được hợp nhất theo ranking method đã công bố
**And** vector dimension/model phải khớp manifest của pinned release.

**Given** một operator không có đủ kết quả hoặc dependency lỗi
**When** retrieval kết thúc
**Then** trace ghi operator, candidate counts, ranks và failure/degradation
**And** không fallback sang draft hoặc corpus release khác
**And** downstream nhận evidence rỗng/thiếu rõ ràng thay vì dữ liệu bịa.

### Story 4.4: Xây dựng evidence package và chặn câu hỏi thiếu bằng chứng

As a user,
I want the assistant to answer only when it has enough relevant evidence,
So that confident wording is not produced from weak, mismatched or conflicting sources.

**Acceptance Criteria:**

**Given** retrieval operators trả candidates
**When** Entity Dossier/Evidence Context Builder chạy
**Then** hợp nhất claims, events, relations, narrative và passages phù hợp intent
**And** loại duplicate evidence theo stable identity/content
**And** giữ lại các nguồn mâu thuẫn thay vì âm thầm chọn một nguồn.

**Given** evidence vượt quá context budget
**When** builder chọn evidence
**Then** áp dụng budget cấu hình theo intent và ưu tiên provenance/relevance
**And** không dùng giới hạn Text operator cũ như invariant cho toàn hệ thống
**And** selection order và lý do có thể trace.

**Given** evidence được đưa vào package
**When** package hoàn tất
**Then** mỗi item có citation ID ổn định trong request, source/passage reference và corpus release ID
**And** model chỉ nhìn thấy citation IDs thuộc package
**And** evidence text được coi là dữ liệu, không phải instruction có quyền thay đổi system behavior.

**Given** pre-generation gate chạy
**When** entity/scope, publish status, freshness, release consistency hoặc evidence threshold không đạt
**Then** Qwen không được gọi
**And** kết quả là `clarify` nếu người dùng có thể làm rõ, hoặc `abstained` nếu evidence không đủ
**And** lý do gate được lưu cho trace/evaluation.

**Given** evidence đủ và nhất quán theo policy
**When** pre-generation gate pass
**Then** package chỉ chứa evidence của một pinned release
**And** generation request nhận bounded package cùng prompt/model version
**And** package có thể được lưu/tái hiện cho regression investigation.

### Story 4.5: Sinh và kiểm tra câu trả lời có citation

As a user,
I want a clear Vietnamese answer whose factual claims are supported by visible citations,
So that I can trust the response or understand when the system cannot answer.

**Acceptance Criteria:**

**Given** pre-generation gate đã pass
**When** Qwen3-4B nhận generation request
**Then** model chỉ nhận query, structured context và bounded evidence package
**And** không có quyền truy vấn database, tạo entity/relation/source hoặc bổ sung facts từ model memory
**And** output tuân theo response schema và citation IDs đã cấp.

**Given** evidence chứng minh tiền đề câu hỏi sai
**When** model tạo câu trả lời
**Then** câu trả lời đính chính tiền đề ngay phần mở đầu
**And** đính chính có citation hỗ trợ
**And** không lặp lại tiền đề sai như một sự thật.

**Given** generation hoàn tất
**When** post-generation gate chạy
**Then** kiểm tra citation IDs thuộc package, factual claims có support, số/ngày khớp evidence, certainty phù hợp và conflict được trình bày
**And** citation không tồn tại hoặc claim không được hỗ trợ làm gate fail
**And** output không được trả như `answered` chỉ vì có định dạng hợp lệ.

**Given** grounding fail nhưng lỗi có thể sửa bằng một lần regeneration
**When** retry policy cho phép
**Then** hệ thống retry tối đa một lần với failure feedback an toàn
**And** nếu vẫn fail thì trả `abstained`
**And** không lặp vô hạn hoặc bỏ qua gate.

**Given** model timeout hoặc unavailable
**When** request không thể hoàn tất
**Then** trả trạng thái lỗi/abstained thân thiện, không bịa fallback answer
**And** evidence/release hiện tại không bị thay đổi
**And** failure được đo và trace.

**Given** response hoàn tất
**When** lưu và trả kết quả
**Then** terminal status chỉ là `answered`, `clarify` hoặc `abstained`
**And** lưu query, pinned release, evidence references, model/prompt version, grounding result và latency theo privacy policy
**And** `answered` luôn có citations hợp lệ cho factual content.

### Story 4.6: Sử dụng Chat độc lập và bên cạnh Content

As a user,
I want to ask questions either from a dedicated Chat page or beside the content I am viewing,
So that I can get grounded help without losing my exploration context.

**Acceptance Criteria:**

**Given** người dùng mở `/chat`
**When** bắt đầu conversation
**Then** có thể gửi câu hỏi tiếng Việt mà không cần đăng nhập
**And** UI hiển thị rõ trạng thái sending, answered, clarify, abstained và service error
**And** conversation không giả định entity context nếu người dùng chưa chọn.

**Given** người dùng mở Chat từ Content Landing
**When** contextual panel xuất hiện
**Then** UI hiển thị chip/label cho entity đang được hỏi
**And** gửi entity ID như context hint được backend xác minh trên pinned release
**And** người dùng có thể bỏ hoặc thay đổi context rõ ràng, không có context ẩn.

**Given** viewport desktop đủ rộng
**When** Chat panel mở bên cạnh Content
**Then** Content và Chat hiển thị ngang hàng mà không che controls/nội dung chính
**And** panel có thể thu gọn/mở lại
**And** tải hoặc lỗi Chat không làm Content Landing ngừng hoạt động.

**Given** viewport mobile hoặc hẹp
**When** người dùng chọn `Hỏi AI`
**Then** Chat mở bằng drawer/bottom sheet hoặc full-screen panel có close/back rõ ràng
**And** đóng Chat trả người dùng về đúng vị trí Content
**And** focus được quản lý và background interaction bị giới hạn phù hợp.

**Given** assistant trả `answered`
**When** response render
**Then** citations là controls có accessible label và mở source/excerpt phù hợp
**And** number/date/source formatting dễ đọc
**And** citation click không làm mất conversation ngoài ý muốn.

**Given** assistant trả `clarify` hoặc `abstained`
**When** response render
**Then** UI giải thích người dùng cần làm rõ gì hoặc vì sao evidence chưa đủ
**And** cung cấp next action phù hợp mà không trình bày đó như lỗi kỹ thuật chung
**And** không hiển thị answer text không qua gate.

**Given** contextual Chat component được compose trong một representative host bằng public integration contract
**When** host truyền scene/entity context
**Then** component dùng lại cùng Chat implementation, không yêu cầu một chatbot thứ hai
**And** context được hiển thị minh bạch trước khi gửi câu hỏi
**And** contract có automated component/contract test để các host như Scene Player có thể tích hợp mà không sửa luồng Chat cốt lõi.

### Story 4.7: Gợi ý câu hỏi đào sâu từ GraphRAG

As a user,
I want relevant follow-up questions after an answer,
So that I can continue exploring connected people, places, events and cultural themes without knowing what to ask next.

**Acceptance Criteria:**

**Given** assistant trả một grounded `answered` response cho entity/topic
**When** hệ thống tạo follow-up suggestions
**Then** đề xuất từ 2 đến 4 câu hỏi dựa trên evidence, timeline hoặc graph paths 1–2 hop thuộc cùng pinned release
**And** mỗi suggestion có target entity/intent/path basis có thể trace
**And** không đề xuất câu hỏi chỉ vì nghe hấp dẫn nhưng corpus không có khả năng hỗ trợ.

**Given** graph có nhiều hướng khám phá hợp lệ
**When** chọn suggestions
**Then** ưu tiên các hướng khác nhau như quan hệ, sự kiện, so sánh hoặc nội dung chuyên đề
**And** tránh lặp lại câu hỏi vừa trả lời hoặc các suggestion gần như giống nhau
**And** không dẫn tới draft, withdrawn hoặc out-of-scope entity.

**Given** suggestion được suy ra bởi model hoặc template
**When** suggestion chuẩn bị trả về UI
**Then** backend xác minh referenced entities/relations/evidence tồn tại trong pinned release
**And** invalid/unverifiable suggestion bị loại
**And** suggestion text không được trình bày như một factual claim đã trả lời.

**Given** người dùng chọn một suggested question
**When** câu hỏi mới được gửi
**Then** nó đi qua đầy đủ resolver, planner, retrieval, evidence và grounding gates như câu hỏi bình thường
**And** không tái sử dụng answer cũ hoặc bỏ qua evidence gate
**And** conversation giữ được context hiển thị rõ ràng.

**Given** response là `clarify` hoặc `abstained`
**When** UI cần next actions
**Then** chỉ hiển thị lựa chọn làm rõ/rephrase hoặc các hướng có evidence an toàn
**And** không dùng deep-dive suggestions để che giấu việc hệ thống thiếu bằng chứng.

**Given** Chat UI render suggestions
**When** người dùng dùng mouse, keyboard hoặc screen reader
**Then** suggestions là controls có accessible name và focus state
**And** chọn suggestion thể hiện rõ rằng một câu hỏi mới sẽ được gửi
**And** loading/error của suggestions không làm mất answer/citations hiện tại.

### Story 4.8: Đánh giá chất lượng và hiệu năng trợ lý trước phát hành

As a product owner,
I want reproducible evidence that the assistant retrieves, cites and refuses correctly,
So that model, prompt or corpus changes cannot silently reduce answer quality.

**Acceptance Criteria:**

**Given** versioned evaluation dataset
**When** chạy retrieval evaluation
**Then** dataset phủ tên chuẩn, alias, không dấu, lỗi gõ, paraphrase, ambiguous và out-of-scope queries
**And** expected entity, intent, operator và evidence được định nghĩa độc lập với implementation
**And** retrieval recall@1 đạt mục tiêu ≥95% trên tập đã công bố.

**Given** fixed evidence packages và representative questions
**When** chạy generation/grounding evaluation
**Then** đo citation faithfulness ≥85%, citation coverage ≥90% và abstention accuracy ≥90%
**And** ba chỉ số được báo cáo cùng nhau để tránh tối ưu lệch
**And** false-premise, conflicting-source, unsupported-number/date cases được kiểm tra riêng.

**Given** assistant chạy trong môi trường demo mục tiêu
**When** thực hiện load profile đã ghi nhận
**Then** chat end-to-end p95 ≤8 giây hoặc report chỉ rõ gate chưa đạt
**And** latency được tách theo resolver, retrieval, evidence, inference và post-gate
**And** timeout/error rate được báo cáo cùng chất lượng.

**Given** evaluation hoàn tất
**When** report được lưu
**Then** report ghi model/base/adapter hoặc GGUF hash, tokenizer/quantization, prompt version, corpus release, retrieval configuration và dataset version
**And** kết quả có thể tái chạy từ cùng inputs/configuration
**And** thiếu metadata làm report không đủ điều kiện release.

**Given** model, prompt, retrieval config hoặc corpus thay đổi
**When** CI/release gate chạy regression suite
**Then** thay đổi vượt ngưỡng suy giảm đã định chặn promotion
**And** không hard-code câu trả lời chỉ để làm tập test pass
**And** failure cases có trace/evidence package để điều tra mà không lộ dữ liệu nhạy cảm.

# Epic 5: Trải nghiệm di sản theo scene, 3D và đa phương tiện

Người dùng bắt đầu từ Content Landing và đi qua một guided story gồm 1–6 narrative scenes có thứ tự. Mỗi scene kết hợp nội dung có evidence với ảnh/panorama hoặc vị trí 3D, hotspot, audio và transcript; khi một media asset lỗi, scene fallback và phần còn lại của trải nghiệm vẫn hoạt động.

### Story 5.1: Biên soạn guided story gồm 1–6 narrative scenes

As a knowledge manager,
I want to compose an ordered guided story from evidence-backed narrative scenes,
So that visitors can follow a purposeful experience instead of viewing an unstructured 3D model.

**Acceptance Criteria:**

**Given** Admin tạo một guided story cho Content Landing/site
**When** lưu story draft
**Then** story có title, description, owning entity/site, language và draft corpus context phù hợp
**And** story mặc định không xuất hiện với public users
**And** Admin không phải nhập entity/site UUID thủ công.

**Given** Admin thêm narrative scenes
**When** cấu hình story
**Then** story chấp nhận từ 1 đến 6 narrative scenes trong MVP
**And** mỗi scene có sequence number, title, body/summary và primary evidence
**And** supporting evidence có thể được chọn qua Evidence Picker.

**Given** database đã có physical `scene` biểu diễn khu vực/model 3D
**When** lưu narrative scene
**Then** narrative scene/chapter có identity riêng, không bị đồng nhất với physical 3D scene
**And** có thể tham chiếu optional physical scene/camera/media configuration
**And** story vẫn hợp lệ với image/panorama fallback khi chưa có model 3D.

**Given** Admin sắp xếp lại narrative scenes
**When** lưu thứ tự mới
**Then** sequence 1..N liên tục, không trùng và không vượt giới hạn 6
**And** reorder được ghi atomically
**And** preview phản ánh đúng thứ tự Previous/Next.

**Given** narrative scene thiếu title/body/evidence hoặc tham chiếu record khác corpus context
**When** Admin lưu hoặc submit validation
**Then** lỗi được gắn đúng scene/field
**And** không publish partial story
**And** story hiện hành của public users không bị thay đổi.

**Given** story đã thuộc published release
**When** Admin muốn sửa scene hoặc thứ tự
**Then** phải tạo draft revision mới
**And** published story cũ vẫn bất biến cho citation/audit
**And** review/publish tiếp tục dùng workflow của Epic 2.

### Story 5.2: Quản lý ảnh, panorama và model 3D có provenance

As a knowledge manager,
I want to upload and govern media assets used by scenes,
So that every public image, panorama or 3D model is attributable, deliverable and safe to publish.

**Acceptance Criteria:**

**Given** Admin thêm media asset
**When** nhập metadata
**Then** chọn asset kind, owning scene/site, license, contributor, origin URL và acquisition/upload date
**And** required provenance thiếu làm asset không đủ điều kiện publish
**And** UI không yêu cầu nhập storage key hoặc foreign key thủ công.

**Given** Admin upload ảnh, panorama hoặc 3D model
**When** upload hoàn tất
**Then** object được lưu tại S3 canonical path với checksum, content type và file size metadata
**And** database record chỉ thành công khi object/reference được reconcile
**And** failure không để lại row trỏ tới object không tồn tại hoặc orphan không được theo dõi.

**Given** asset là 3D model
**When** validation chạy
**Then** format/compression/LOD metadata tuân theo contract hỗ trợ như GLB và Draco/Meshopt khi áp dụng
**And** mỗi model production-ready không vượt asset budget 30 MB
**And** invalid/corrupt model không được đánh dấu ready.

**Given** một physical scene có nhiều mức chi tiết
**When** Admin quản lý LOD/proxy assets
**Then** mỗi LOD identity là duy nhất trong scene
**And** proxy/preview được phân biệt với full asset
**And** public API có đủ metadata để chọn asset phù hợp mà không tải tất cả cùng lúc.

**Given** asset đã thuộc published story
**When** file cần thay thế
**Then** tạo immutable asset revision/object mới thay vì overwrite âm thầm
**And** story/release cũ vẫn tham chiếu đúng checksum cũ
**And** thao tác upload/replace/retire được audit.

**Given** browser yêu cầu media
**When** API trả object URL hoặc signed URL
**Then** quyền đọc phù hợp asset policy và thời hạn truy cập
**And** S3 vẫn là canonical store, không critical-path dual-write sang R2/Azure
**And** storage credentials không lộ cho client.

### Story 5.3: Cấu hình góc camera, vị trí 3D và hotspots cho từng scene

As a knowledge manager,
I want each narrative scene to open at the intended visual viewpoint with meaningful hotspots,
So that visitors see the part of the heritage site that supports the story being told.

**Acceptance Criteria:**

**Given** narrative scene tham chiếu physical 3D scene
**When** Admin cấu hình viewpoint
**Then** lưu camera position/orientation, target và scene transform theo contract
**And** reference trỏ tới model/physical scene hợp lệ
**And** invalid hoặc non-finite coordinates bị từ chối.

**Given** scene cần chuyển động camera
**When** Admin cấu hình camera path/keyframes
**Then** keyframes có thứ tự và tham chiếu scene/model hợp lệ
**And** preview có thể replay path trước khi publish
**And** reduced-motion fallback có thể bỏ chuyển động mà vẫn đưa người dùng tới viewpoint chính.

**Given** Admin thêm hotspot
**When** chọn vị trí trên preview/model
**Then** hotspot lưu local coordinates, label và linked published/draft entity phù hợp corpus context
**And** hotspot ngoài bounds hoặc trỏ tới entity không hợp lệ bị cảnh báo/từ chối
**And** Admin không nhập tọa độ/entity UUID thủ công khi UI có thể chọn trực tiếp.

**Given** narrative scene không có hoặc không tải được 3D
**When** cấu hình fallback
**Then** có thể chọn image/panorama và focal information tương ứng
**And** nội dung/evidence của scene không phụ thuộc vào camera path để đọc được
**And** fallback được preview trước publish.

**Given** Admin thay đổi viewpoint, path hoặc hotspots
**When** lưu scene draft
**Then** configuration được validation và ghi atomically
**And** thay đổi được audit
**And** published scene không bị sửa trực tiếp ngoài revision workflow.

### Story 5.4: Kiểm tra narration, tạo audio và transcript

As a knowledge manager,
I want narration to be evidence-checked before audio is generated,
So that visitors never hear unsupported factual claims and can always read an equivalent transcript.

**Acceptance Criteria:**

**Given** Admin soạn narration script cho story/scene
**When** submit script để kiểm tra
**Then** mỗi factual statement phải liên kết tới passage evidence hoặc được đánh dấu rõ là editorial transition
**And** unsupported statement tạo blocking issue
**And** AI suggestion không tự động được chấp nhận hoặc publish.

**Given** narration script còn blocking issue hoặc chưa được human review
**When** yêu cầu tạo audio
**Then** synthesis bị chặn
**And** không tạo public audio từ script chưa duyệt
**And** reason hiển thị đúng statement/evidence cần sửa.

**Given** script đã evidence-check và approve
**When** offline TTS/audio production chạy
**Then** audio được tạo trước khi publish, không synthesize trong request của end user
**And** Vietnamese audio là mandatory cho pilot; ngôn ngữ bổ sung là optional sau mandatory gates
**And** audio asset lưu provenance, voice/language/version và S3 checksum phù hợp.

**Given** audio đã tạo
**When** transcript segments được lưu
**Then** text, sequence, start/end time hợp lệ và nằm trong audio duration
**And** transcript đầy đủ có thể đọc mà không cần phát audio
**And** transcript/citation references thuộc cùng story/release.

**Given** narration hoặc audio cần sửa sau publish
**When** Admin tạo bản mới
**Then** script, audio và transcript được version cùng nhau
**And** published experience cũ vẫn tham chiếu bộ cũ
**And** regeneration phải qua lại evidence/review gates.

### Story 5.5: Trải nghiệm guided story bằng Scene Player

As a visitor,
I want to move through a guided story scene by scene,
So that I can understand a heritage place through an intentional visual and narrative sequence.

**Acceptance Criteria:**

**Given** người dùng chọn `Bắt đầu trải nghiệm` từ Content Landing
**When** Scene Player mở
**Then** pin đúng published story/release và mở Scene 1
**And** hiển thị progress `Scene X of N`, title và scene content phù hợp
**And** không tải draft hoặc story revision khác.

**Given** story có nhiều scenes
**When** người dùng chọn Previous hoặc Next
**Then** chuyển đúng scene theo sequence đã publish
**And** first/last scene có control state rõ ràng
**And** navigation không làm mất story/release context.

**Given** người dùng chọn Replay
**When** scene có camera motion hoặc narration
**Then** scene trở về trạng thái bắt đầu và phát lại phần được phép
**And** replay không tải duplicate asset không cần thiết
**And** reduced-motion preference được tôn trọng.

**Given** scene có 3D, panorama hoặc image fallback
**When** visual canvas render
**Then** dùng 3D khi asset/configuration sẵn sàng, nếu không dùng fallback đã publish
**And** scene text, transcript và source/resources vẫn truy cập được
**And** visual type hiện tại được thể hiện rõ, không giả fallback image là 3D.

**Given** scene có hotspots
**When** người dùng chọn hotspot
**Then** hiển thị label/thông tin liên quan và action phù hợp
**And** keyboard/focus alternative tồn tại
**And** hotspot không điều hướng tới draft/withdrawn content.

**Given** Chat panel từ Epic 4 được mở bên cạnh player
**When** người dùng gửi câu hỏi
**Then** UI hiển thị entity/scene context đang dùng
**And** dùng lại cùng Chat component và grounded backend, không tạo chatbot thứ hai
**And** Chat lỗi không dừng Scene Player và scene change không âm thầm đổi context chưa hiển thị.

### Story 5.6: Tải media hiệu quả và suy giảm an toàn khi có lỗi

As a visitor,
I want the scene experience to remain usable on ordinary devices and unreliable connections,
So that a media failure never removes the story, transcript or ability to continue.

**Acceptance Criteria:**

**Given** người dùng chưa bắt đầu experience hoặc chưa tới scene
**When** Content Landing/Scene Player tải
**Then** full 3D/audio assets không tải trước ngoài preload budget đã định
**And** next-scene prefetch có giới hạn, có thể hủy và không tải toàn bộ story cùng lúc
**And** image/proxy/LOD phù hợp được ưu tiên trước full asset.

**Given** representative production 3D asset trên điều kiện 4G đã ghi nhận
**When** người dùng mở scene
**Then** model mục tiêu tải và render trong ≤3 giây hoặc chuyển sang fallback rõ ràng
**And** mỗi model không vượt 30 MB
**And** performance result được đo trên device/network profile đã công bố.

**Given** audio đã sẵn sàng và người dùng chọn phát
**When** playback bắt đầu
**Then** audio mục tiêu bắt đầu trong ≤1 giây theo điều kiện đo đã ghi nhận
**And** controls có play/pause/progress/mute phù hợp
**And** transcript luôn mở được độc lập với audio.

**Given** model, image, audio hoặc media request trả 404/timeout/error
**When** Scene Player xử lý failure
**Then** chỉ phần asset tương ứng chuyển sang unavailable/fallback state
**And** text, transcript, citations, Chat và Previous/Next vẫn hoạt động
**And** không retry vô hạn hoặc tạo trang trắng.

**Given** người dùng dùng keyboard, screen reader hoặc reduced motion
**When** tương tác Scene Player
**Then** controls có semantic name, focus order và trạng thái được thông báo
**And** camera animation/auto motion có thể giảm hoặc bỏ
**And** thông tin chỉ có trong hình/audio có text alternative phù hợp.

**Given** media tải, fallback hoặc lỗi
**When** telemetry được ghi
**Then** signal chứa story/scene/asset version, duration, outcome và correlation ID phù hợp
**And** không chứa signed URL secret hoặc dữ liệu nhạy cảm
**And** dashboard phân biệt content success với media degradation.

# Epic 6: Khám phá cá nhân hóa có thể giải thích

Người dùng mới nhận cold-start recommendations mà không cần đăng nhập. Khi người dùng tự nguyện bật cá nhân hóa, frontend suy ra hồ sơ sở thích ẩn danh từ tương tác và lưu trên thiết bị; backend chỉ dùng payload hợp lệ để tính gợi ý có reason path, không lưu hồ sơ Public User.

### Story 6.1: Quản lý consent và hồ sơ ẩn danh trên thiết bị

As a public user,
I want control over whether HeritageGraph may use my on-device interactions for personalization,
So that recommendations never require hidden tracking or an account.

**Acceptance Criteria:**

**Given** người dùng chưa đưa ra consent
**When** sử dụng Home, Explore, Map, Content, Chat hoặc Scene Player
**Then** frontend không tạo/cập nhật interest profile hoặc interaction history cho personalization
**And** không gửi anonymous profile tới Recommendation API
**And** recommendation vẫn có thể dùng cold-start mode.

**Given** UI đề nghị bật cá nhân hóa
**When** người dùng xem prompt/settings
**Then** giải thích loại tín hiệu được dùng, dữ liệu nằm trên thiết bị và không đồng bộ tài khoản
**And** lựa chọn bật/từ chối có mức nổi bật công bằng
**And** từ chối không chặn nội dung công cộng.

**Given** người dùng đồng ý
**When** consent được lưu
**Then** local consent/profile record có schema version, timestamp và trạng thái rõ ràng
**And** không chứa tên, email, account ID, raw IP hoặc device fingerprint
**And** chỉ các interaction sau consent được ghi trừ khi policy được người dùng chấp thuận rõ khác đi.

**Given** local profile schema cũ hoặc dữ liệu localStorage bị sửa/hỏng
**When** frontend đọc profile
**Then** validate/migrate theo versioned contract hoặc quay về profile rỗng an toàn
**And** không crash trang
**And** không gửi payload chưa validation tới backend.

**Given** profile/history đạt giới hạn dung lượng hoặc tuổi dữ liệu
**When** ghi tương tác mới
**Then** áp dụng retention/compaction policy xác định
**And** không tăng localStorage không giới hạn
**And** consent state không bị xóa nhầm khi compact profile.

### Story 6.2: Gợi ý cold start cho người dùng mới

As a new or non-consenting user,
I want useful recommendations without a personal profile,
So that I can discover heritage content immediately and privately.

**Acceptance Criteria:**

**Given** request không có consented local profile
**When** Recommendation Service nhận context hợp lệ
**Then** dùng cold-start strategy dựa trên published featured/popular metadata, current region/category/content context phù hợp
**And** không yêu cầu account hoặc synthetic personal profile
**And** chỉ trả candidates thuộc pinned published release.

**Given** cold-start candidates được xếp hạng
**When** tạo result list
**Then** áp dụng diversity policy để tránh mọi kết quả quá giống nhau khi candidate pool cho phép
**And** mỗi result có lý do không cá nhân hóa như nổi bật, cùng khu vực hoặc liên quan nội dung đang xem
**And** không tuyên bố “dựa trên sở thích của bạn”.

**Given** không có đủ candidates trong context hẹp
**When** service mở rộng kết quả
**Then** dùng fallback đã định trong published corpus như bỏ bớt filter hoặc dùng featured content
**And** lý do phù hợp với fallback thực tế
**And** không tạo entity/reason không tồn tại.

**Given** người dùng không consent
**When** xem/click/dismiss cold-start recommendations
**Then** action phục vụ điều hướng hiện tại nhưng không được lưu vào personalization profile/history
**And** backend không persist hành vi Public User.

### Story 6.3: Cập nhật sở thích từ tương tác có consent

As a consenting user,
I want my recommendations to adapt to my interactions,
So that future suggestions become more relevant without creating a server-side identity.

**Acceptance Criteria:**

**Given** personalization consent đang bật
**When** người dùng view, click, dwell, save hoặc dismiss published content
**Then** frontend tạo interaction record tối thiểu theo versioned schema
**And** signal type, target entity/category/region và timestamp hợp lệ được ghi local
**And** không ghi raw content, free-text chat hoặc sensitive fields không cần thiết.

**Given** một interaction hợp lệ
**When** local profile được cập nhật
**Then** dùng deterministic weights/config cho từng signal
**And** save/positive engagement và dismiss có tác động khác nhau theo policy
**And** cùng sequence interactions/config tạo cùng profile result.

**Given** profile có signals theo thời gian
**When** tính sở thích hiện tại
**Then** áp dụng time decay/retention xác định để tín hiệu cũ giảm ảnh hưởng
**And** repeated events được deduplicate/cap để một hành động không tăng trọng số vô hạn
**And** profile giữ trong size limit.

**Given** consent bị tắt trong khi UI đang mở
**When** interaction tiếp theo xảy ra
**Then** frontend dừng cập nhật profile/history và dừng gửi profile
**And** action công cộng vẫn hoạt động
**And** trạng thái không dựa vào reload trang mới có hiệu lực.

### Story 6.4: Tạo và xếp hạng recommendations cá nhân hóa

As a consenting user,
I want recommendations that combine my interests with cultural relationships,
So that I can discover relevant content beyond simple popularity lists.

**Acceptance Criteria:**

**Given** Recommendation API nhận anonymous profile
**When** validate request
**Then** kiểm schema version, allowed fields, value ranges và payload size
**And** từ chối/bỏ profile không hợp lệ theo contract rồi quay về cold start an toàn
**And** không chấp nhận user identity, raw interaction content hoặc executable fields.

**Given** profile và current context hợp lệ
**When** Candidate Generator chạy
**Then** lấy candidates từ versioned graph projection, vector similarity và published metadata
**And** mọi candidate thuộc cùng pinned release
**And** candidate sources hội tụ vào một normalized candidate contract.

**Given** candidate pool đã tạo
**When** Rank & Diversify tính điểm
**Then** score kết hợp relevance/context, graph affinity, profile affinity và diversity components theo cấu hình versioned
**And** dismissed content bị loại/giảm theo policy, content đã xem không lấn át danh sách
**And** tie-breaking xác định để cùng input/config cho kết quả tái lập.

**Given** backend hoàn tất request
**When** trả recommendations
**Then** không persist anonymous profile hoặc interaction history
**And** không ghi toàn bộ profile vào logs/traces
**And** Qwen không được gọi chỉ để xếp hạng recommendation.

**Given** graph, vector hoặc metadata source lỗi
**When** candidate generation suy giảm
**Then** dùng nguồn còn hợp lệ hoặc cold-start fallback theo policy
**And** không trộn corpus versions
**And** response/telemetry thể hiện degraded strategy.

### Story 6.5: Giải thích và đa dạng hóa recommendations

As a user,
I want to know why an item was recommended and receive a varied set of results,
So that suggestions feel understandable rather than repetitive or opaque.

**Acceptance Criteria:**

**Given** recommendation result được chọn
**When** tạo explanation
**Then** response có entity/content, score và reason path hoặc reason code có thể kiểm chứng
**And** graph reason path chỉ dùng node/edge thuộc pinned release
**And** không tạo lý do từ relation không tồn tại.

**Given** reason dựa trên local profile
**When** hiển thị cho người dùng
**Then** diễn đạt ở mức chủ đề/context phù hợp như “vì bạn quan tâm kiến trúc cung đình”
**And** không tiết lộ hoặc suy diễn sensitive trait
**And** không tuyên bố biết danh tính người dùng.

**Given** candidate pool đủ rộng
**When** Rank & Diversify chọn top results
**Then** tránh quá nhiều items cùng entity/category/path gần như trùng nhau
**And** cho phép cross-category discovery theo policy
**And** không hy sinh mọi relevance chỉ để đạt diversity hình thức.

**Given** candidate pool không đủ để đạt diversity target
**When** tạo response
**Then** trả tập hợp nhỏ hơn hoặc ít đa dạng hơn một cách trung thực
**And** không bịa candidate/path để đủ số lượng
**And** telemetry ghi candidate shortage.

**Given** cùng profile, context, release và ranking config
**When** request được chạy lại trong điều kiện deterministic
**Then** score order và reason paths tái lập được
**And** report có ranking/config version để điều tra thay đổi.

### Story 6.6: Hiển thị và tương tác với recommendations

As a user,
I want recommendations integrated into my exploration journey,
So that I can continue to relevant content and influence future suggestions when I choose.

**Acceptance Criteria:**

**Given** Home, Explore hoặc Content Landing có recommendation placement
**When** results tải thành công
**Then** card dùng cùng public card/content navigation contract
**And** hiển thị reason ngắn hoặc control mở explanation
**And** personalized/cold-start mode được diễn đạt phù hợp, không gây hiểu nhầm.

**Given** người dùng chọn recommendation
**When** mở content
**Then** điều hướng tới published Content Landing/experience đúng release context
**And** click/view signal chỉ cập nhật local profile khi consent đang bật
**And** back navigation giữ được vị trí danh sách.

**Given** người dùng chọn Save hoặc Không quan tâm
**When** action được thực hiện
**Then** UI cập nhật rõ trạng thái action
**And** local profile/history được cập nhật deterministic khi consent bật
**And** khi không consent, UI giải thích cần bật cá nhân hóa hoặc chỉ thực hiện hành vi không lưu theo product decision.

**Given** Recommendation Service chậm hoặc lỗi
**When** page render
**Then** nội dung chính Home/Explore/Content vẫn hoạt động
**And** recommendation section hiển thị loading/unavailable hoặc cold-start fallback phù hợp
**And** không tạo trang trắng hoặc giữ skeleton vô hạn.

**Given** người dùng dùng keyboard/screen reader
**When** tương tác cards, reasons, Save hoặc Dismiss
**Then** controls có accessible name/state và focus order hợp lý
**And** dynamic updates được thông báo mà không chiếm focus ngoài ý muốn.

### Story 6.7: Xem, xuất, reset hoặc tắt cá nhân hóa

As a public user,
I want to inspect and control personalization data stored on my device,
So that I can understand, export or remove it without needing an account.

**Acceptance Criteria:**

**Given** người dùng mở Preferences
**When** personalization state được đọc
**Then** hiển thị consent đang bật/tắt, profile schema/version, inferred topics/context và interaction history summary có thể hiểu
**And** không trình bày server có tài khoản/profile khi thực tế không có
**And** corrupted local data hiển thị recovery/reset option an toàn.

**Given** người dùng chọn Export
**When** export được tạo
**Then** file machine-readable JSON chứa consent/profile/history hiện lưu cùng schema version và export timestamp
**And** không thêm device fingerprint, raw IP hoặc dữ liệu không tồn tại trong local store
**And** export không gửi dữ liệu lên backend chỉ để tạo file.

**Given** người dùng chọn Reset và xác nhận
**When** reset hoàn tất
**Then** local interest profile và interaction history bị xóa
**And** recommendation quay về cold-start behavior
**And** UI phản ánh trạng thái mới ngay, không cần reload.

**Given** người dùng tắt personalization
**When** setting được lưu
**Then** frontend dừng đọc/cập nhật/gửi profile cho recommendation
**And** hiển thị rõ dữ liệu local hiện có được giữ hay xóa theo lựa chọn/policy
**And** cung cấp action Reset riêng nếu dữ liệu chưa bị xóa.

**Given** người dùng dùng thiết bị/browser khác
**When** mở HeritageGraph
**Then** không tự đồng bộ profile/history từ thiết bị cũ
**And** không yêu cầu login để phục hồi
**And** behavior bắt đầu từ consent/cold-start state của thiết bị mới.

### Story 6.8: Đánh giá độ chính xác, đa dạng, riêng tư và tốc độ

As a product owner,
I want reproducible evidence that recommendations are useful, diverse, private and fast,
So that personalization can be released without hidden tracking or misleading quality claims.

**Acceptance Criteria:**

**Given** versioned recommendation evaluation sample
**When** đánh giá cold-start và personalized scenarios
**Then** đo precision@5 với reviewer-grounded relevance labels và đạt mục tiêu ≥70% hoặc report gate fail
**And** sample/config/release/profile inputs được version hóa
**And** expected relevance không được lấy trực tiếp từ score implementation.

**Given** result lists từ representative contexts
**When** đánh giá diversity và duplication
**Then** report category/path diversity, repeated/seen/dismissed rates và candidate coverage
**And** quality được báo cùng precision để tránh tối ưu diversity làm mất relevance
**And** candidate shortage được tách khỏi ranking defect.

**Given** reason paths/explanations
**When** validation chạy
**Then** mọi referenced entity/relation/path tồn tại trong pinned release và khớp reason text
**And** fabricated hoặc cross-version reason làm test fail
**And** sensitive-trait inference bị cấm/kiểm tra.

**Given** Recommendation Service chạy trong môi trường mục tiêu
**When** đo request không gồm LLM generation
**Then** p95 ≤2 giây hoặc report gate fail
**And** latency được tách theo candidate sources và ranking
**And** degraded/cold-start fallbacks được đo riêng.

**Given** privacy/contract tests
**When** gửi profile hợp lệ, quá lớn, malformed hoặc chứa identity fields
**Then** backend validate/reject/fallback đúng contract
**And** không có server-side Public User profile/history persistence
**And** logs/traces không lưu toàn bộ profile hoặc forbidden identifiers.

**Given** cùng release, profile, context và ranking config
**When** chạy deterministic replay
**Then** candidate scores/order/reasons tái lập được trong tolerance đã định
**And** report ghi graph/vector/metadata và ranking config versions
**And** regression vượt threshold chặn release/promotion.
