---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
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
- FR14: Graph Service cho phép truy vấn entity, predicate, relation và traversal giới hạn 1–2 hop trên published corpus.
- FR15: Recommendation Service hỗ trợ cold start và hồ sơ sở thích ẩn danh được frontend suy ra từ view, click, dwell, save và dismiss có consent rồi lưu trong `localStorage`.
- FR16: Candidate Generator kết hợp graph projection, pgvector và metadata; Rank & Diversify tránh kết quả quá giống hoặc đã xem.
- FR17: Mỗi gợi ý có score và reason path giải thích được; frontend cập nhật hồ sơ cục bộ từ tương tác mới theo quy tắc xác định và có thể tái lập.
- FR18: Tại Preferences, người dùng xem trạng thái consent, tắt cá nhân hóa, xuất hoặc đặt lại hồ sơ cùng interaction history lưu trên thiết bị.
- FR19: Nội dung chi tiết hỗ trợ story, timeline, entity liên quan, bản đồ, mô hình 3D, audio và transcript.
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
- FR14: Epic 4 — Graph Service và traversal giới hạn.
- FR15: Epic 5 — Cold start và hồ sơ sở thích ẩn danh cục bộ có consent.
- FR16: Epic 5 — Candidate generation và rank/diversify.
- FR17: Epic 5 — Recommendation có score/reason path và cập nhật local profile.
- FR18: Epic 5 — Quản lý consent, xuất và đặt lại dữ liệu cục bộ.
- FR19: Epic 6 — Story, timeline, map, 3D, audio và transcript.
- FR20: Epic 6 — Media provenance và evidence gate cho audio.
- FR21: Epic 6 — Media failure degradation.
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
- FR37: Epic 3 — Home, Explore, Search/Filter và Entity Detail trên published content.

## Epic List

### Epic 1: Admin Knowledge Studio

Quản trị viên đăng nhập và biên soạn trọn một knowledge package — document, passage, entity/alias/place profile, claim, timeline, relation, narrative và evidence — ở trạng thái draft mà không cần thao tác SQL, UUID hoặc foreign key thủ công.

**FRs covered:** FR01, FR22–FR29

### Epic 2: Kiểm định và phát hành corpus đáng tin cậy

Biên tập viên submit draft để Airflow kiểm tra sâu, tạo embedding/index/manifest, xử lý issues, review và publish một corpus release atomically; dashboard cho biết sức khỏe và khả năng phục vụ của từng release.

**FRs covered:** FR30–FR36

### Epic 3: Cổng khám phá và kể chuyện di sản

Người dùng khám phá published heritage content qua một giao diện kể chuyện thống nhất xuyên suốt Home, Explore và Entity Detail: bố cục editorial giàu hình ảnh, card có hierarchy, narrative flow giữa các thực thể và liên kết liền mạch tới Chat, Recommendation, Preferences và Multimedia; đầy đủ trạng thái responsive, loading, empty, error, not-found, clarify và abstained.

**FRs covered:** FR37

### Epic 4: Trợ lý hỏi đáp có căn cứ

Người dùng hỏi bằng tiếng Việt từ portal hoặc trang chat; hệ thống resolve entity, lập query plan, lấy evidence đúng published corpus, dùng Qwen3-4B tổng hợp và chỉ trả answered, clarify hoặc abstained sau grounding validation.

**FRs covered:** FR02–FR14

### Epic 5: Khám phá cá nhân hóa có thể giải thích

Người dùng mới nhận cold-start recommendations; người dùng có consent nhận kết quả dựa trên hồ sơ ẩn danh lưu trong `localStorage`, xem reason path, đồng thời có thể xuất, đặt lại hoặc tắt cá nhân hóa mà không cần đăng nhập. Hệ thống không hỗ trợ đồng bộ hồ sơ giữa các thiết bị.

**FRs covered:** FR15–FR18

### Epic 6: Trải nghiệm di sản 3D và đa phương tiện

Người dùng trải nghiệm story, timeline, map, mô hình 3D, audio và transcript có provenance trên Entity Detail; khi media storage hoặc delivery lỗi, nội dung tri thức vẫn hoạt động và trạng thái suy giảm được hiển thị rõ.

**FRs covered:** FR19–FR21
