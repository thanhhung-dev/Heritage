---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
inputDocuments:
  - prds/prd-HeritageGraph-2026-09-08/prd.md
  - prds/prd-HeritageGraph-2026-09-08/addendum.md
  - ../../docs/architecture.md
  - ../../docs/specs/spec-heritagegraph-v2/SPEC.md
  - ../../docs/specs/spec-heritagegraph-v2/companions (features.md, fr-catalog.md, metrics-targets.md, architecture-principles.md, schedule.md)
---

# HeritageGraph - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for HeritageGraph, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

> **Ghi chú phạm vi:** PRD `prd-HeritageGraph-2026-09-08` là SRS chính thức (chuyển thể từ proposal-vi v2.0 + upgrade-plan, giữ nguyên mã FR/NFR để truy vết). Nó **mở rộng** so với spec `spec-heritagegraph-v2` (chuyển thể từ đề cương): thêm kênh vector pgvector (FR12), trang chi tiết nội dung (PRD gọi là "Tapestry") + 3D + audio (FR23, FR28–FR30), hạ tầng Antd. Khi xung đột, PRD thắng.
>
> **Quy ước triển khai (theo chỉ thị của PO):** Xây **mới toanh từ đầu** — không dựa vào hiện trạng repo, không giả định mã nguồn đã có. Mọi thành phần (retriever, kg, rag, llm, corpus, frontend) đều là công việc cần làm mới. Thiết kế mục tiêu trong `docs/architecture.md` được dùng như đặc tả xây dựng.

## Requirements Inventory

### Functional Requirements

- FR01: Đăng ký, xác thực, quản lý tài khoản — mật khẩu chỉ lưu băm argon2id; phiên qua cookie HttpOnly (JWT, SameSite=Lax); endpoint được bảo vệ từ chối yêu cầu chưa xác thực; máy chủ demo bind 127.0.0.1
- FR02: CRUD tài liệu kho ngữ liệu — chuẩn hóa, tách đoạn kèm định vị nguồn; đồ thị dựng lại với đỉnh mới liên kết về nguồn
- FR03: CRUD bản ghi có cấu trúc — venue (tọa độ), event (loại lịch, phần lễ/hội), artifact (niên đại, chất liệu, bảo tàng, phòng), media_asset (giấy phép, người đóng góp, URL gốc); thiếu `source_url`/`source_sentence` bị từ chối **ở mức DB** kèm lỗi mức trường
- FR04: Trích xuất thực thể/quan hệ/hành chính/năm — tất định, khớp lược đồ 4 loại, mọi tên là chuỗi con nguyên văn của nguồn
- FR05: Dựng + cập nhật đồ thị — đỉnh/cạnh tạo, gán kiểu, gán trọng số, liên kết về nguồn; không quan hệ nào tạo mà thiếu chuỗi nguồn
- FR06: Rà soát kết quả trích xuất — thay đổi ghi audit_log kèm giá trị trước/sau
- FR07: Suy ra hồ sơ sở thích mà không yêu cầu khai — nền tảng dùng đầy đủ trước khi có hồ sơ; sau vài tìm/xem đầu tiên hồ sơ đã có sở thích có trọng số
- FR08: Ghi tương tác ngầm định, xem/sửa được — view/dwell/click/save/dismiss kèm mốc thời gian + đỉnh đích; trọng số suy giảm theo thời gian; người dùng thấy từng sở thích kèm hành vi sinh ra nó
- FR09: Gợi ý kèm đường đi đồ thị — mỗi mục kèm `reason_path`; `GET /api/recommend?seed=<node>&k=5` → `[{node, label, category, score, reason_path}]`
- FR10: Gợi ý xuyên danh mục — ≥1 trong 5 gợi ý đầu thuộc danh mục khác; gate Sprint 2: mọi danh mục ≥8 tài liệu
- FR11: Đa dạng — 5 mục đầu ≤3 mục cùng danh mục, trừ khi số danh mục tiếp cận được ít hơn
- FR12: Truy hồi đúng đoạn bất kể biến thể ngôn ngữ — 3 kênh (BM25 từ, BM25 n-gram không dấu, vector pgvector dim 1024) hợp nhất RRF; recall@1 ≥95%; bảng tách kênh; endpoint truy vết phơi hạt giống, hạng từng kênh, các cổng
- FR13: Xếp hạng lại theo hồ sơ — hai người dùng hồ sơ khác nhau nhận thứ tự khác nhau; khác biệt truy nguyên về trọng số hồ sơ
- FR14: Chat chỉ văn bản, trả lời chỉ từ bối cảnh đã truy hồi
- FR15: Trích nguồn hoặc phát biểu thiếu bằng chứng — mỗi câu khẳng định kèm `[Nguồn: <câu nguyên văn> — <url>]`; url phải hiển thị ở frontend
- FR16: Đính chính giả định sai — giả định trái nguồn → đính chính ngay câu đầu (≥90%)
- FR17: Phân loại ý định — 6 lớp (research/attend_event/plan_trip/learn/compare/verify); regex + từ vựng, không fine-tune; macro-F1 ≥85% trên ≥100 câu gán nhãn tay
- FR18: Thẻ khớp sổ đăng ký — mọi trường thẻ = đúng trường bản ghi nguồn hoặc phản hồi API, không trường nào do sinh ra; assert tự động 100%; thẻ mang provenance + fetched_at
- FR19: Lịch sự kiện — tên, loại lịch, ngày (âm lịch quy đổi soạn tay, không thư viện), địa điểm kèm tọa độ, đơn vị tổ chức, phần lễ + phần hội
- FR20: Thời tiết + danh mục chuẩn bị — Open-Meteo theo tọa độ; checklist sinh bằng ~15 luật tường minh trong `prep_rules.yaml`; lễ xa hơn 16 ngày → khí hậu trung bình cùng kỳ, thẻ ghi rõ "khí hậu, không phải dự báo"
- FR21: POI gần địa điểm — bãi xe, điểm quan sát, cửa hàng nghề/quà; Overpass + cache vào bảng poi; kiểm độ phủ OSM đầu Tuần 8; thưa → fallback POI soạn tay
- FR22: Địa điểm & lịch mở cửa — tên, địa chỉ, giờ mở, giá vé từ bản ghi F03; cổ vật thêm bảo tàng + phòng trưng bày
- FR23: Trang chi tiết nội dung (PRD gọi là "Tapestry") — ảnh lớn trái, danh sách story phải; kể chuyện, audio, chip liên kết, dòng thời gian, thực thể liên quan, dải nội dung liên quan
- FR24: Endpoint truy vết — phơi hạt giống, hạng từng kênh, độ gần đồ thị, thành phần cho điểm, kết quả từng cổng từ chối
- FR25: Hồ sơ + dữ liệu cá nhân trong trang tài khoản — hồ sơ kèm hành vi sinh ra từng sở thích, bỏ/tắt được; xuất tệp máy đọc được; xóa vĩnh viễn cả hồ sơ lẫn interaction_event. Không thể bị cắt
- FR26: Dashboard sức khỏe — số tài liệu/danh mục, thống kê đồ thị, trường thiếu nguồn, hàng chờ rà soát, chỉ số mới nhất
- FR27: Toàn bộ bộ đánh giá chạy được — mọi chỉ số tính và xuất báo cáo ghi: mô hình, checkpoint bộ điều hợp, phiên bản prompt, phiên bản kho ngữ liệu, cấu hình
- FR28: 3D + audio — .glb từ R2 qua Three.js; xoay, phóng, chuyển story, chuyển ngữ; mỗi audio có transcript đầy đủ
- FR29: Nguồn gốc tài sản — media_asset lưu khóa kho, người đóng góp, ngày, giấy phép, URL nguồn gốc; thiếu → từ chối tại biên endpoint
- FR30: Script audio có bằng chứng — mỗi câu khẳng định transcript truy về được câu nguồn hoặc đánh dấu lời dẫn dắt biên tập; kiểm tra tự động chặn tổng hợp giọng nói nếu không đạt

### NonFunctional Requirements

- NFR01: p95 đầu-cuối ≤8 giây (câu hỏi tiêu chuẩn, môi trường demo), đo liên tục từ Sprint 1
- NFR02: Gợi ý + thẻ trong 2 giây (không tính sinh mô hình); API ngoài chạy song song
- NFR03: Trang chi tiết ≤3 giây (đệm đồ thị, ảnh thu nhỏ)
- NFR04: recall@1 ≥95% kể cả không dấu/tên khác/diễn giải; recall riêng tập diễn giải báo cáo tách
- NFR05: Trung thực trích nguồn ≥85%; độ phủ trích nguồn ≥90%
- NFR06: 0 trường bịa trong thẻ tư vấn — assert tự động
- NFR07: Từ chối ≥90%; trả lời bịa ngoài phạm vi = lỗi; báo cáo cùng NFR04
- NFR08: Mọi gợi ý phơi đường đi qua tooltip; mọi truy hồi kiểm tra qua endpoint
- NFR09: Lần đầu hỏi + nhận gợi ý ngay lập tức — không onboarding, không bảng khai
- NFR10: WCAG 2.1 AA phần áp dụng được: alt-text, tương phản, bàn phím, transcript cho audio, mô tả 3D
- NFR11: Xác thực mọi endpoint cá nhân; kiểm tra đầu vào; không đường ghi không xác thực; không mở mạng công khai
- NFR12: Đồng ý trước khi ghi; chỉ lưu tối thiểu; xuất + xóa (không thể cắt)
- NFR13: Mọi phát biểu truy về nguồn: câu kho ngữ liệu, trường bản ghi, hoặc API có tên + mốc thời gian
- NFR14: Bản ghi thiếu nguồn không lưu được — ràng buộc mức DB, không phải app
- NFR15: Nạp/graph/truy hồi/sinh/gợi ý/tư vấn/UI = mô-đun giao diện tách biệt
- NFR16: Model, checkpoint adapter, phiên bản prompt, phiên bản kho, cấu hình ghi trong mọi report
- NFR17: Thêm vùng/danh mục/bản ghi không sửa mã; thẻ mới chỉ cần đăng ký bộ sinh
- NFR18: Một máy, không dịch vụ AI ngoài, không khóa API
- NFR19: .glb tải ≤3 giây trên 4G, ≤30 MB (Draco/Meshopt); audio phát ≤1 giây; không tính thời gian tổng hợp (sinh trước)
- NFR20: Mất R2/Azure → trang chi tiết vẫn đầy đủ văn bản/transcript/chip; 3D+audio hiện "tạm thời không khả dụng", không trang trắng

### Additional Requirements

*Nguồn: docs/architecture.md (thiết kế mục tiêu) + addendum §1 (chi tiết kỹ thuật). Triển khai greenfield — mọi thứ xây mới.*

- **Thiết kế mục tiêu làm đặc tả xây dựng:** toàn bộ lớp PostgreSQL (schema, docker-compose, seed_postgres, PostgresRepository, bảng 3D Story/Scene, app_user, audit_log, chat_session/chat_message/chat_feedback) là **việc cần xây mới**. Kiến trúc mục tiêu: graph dựng deterministic từ corpus + locations_index, retrieval trong RAM, PG persist cho `/api/graph`
- **Mã nguồn cần xây mới (xây từ đầu):** `retriever.py` (BM25 từ + BM25 n-gram + RRF + graph rerank/pump), `kg.py` (dựng đồ thị deterministic, find_seeds, expand_docs), `rag.py` (3 cổng từ chối: neo graph, bằng chứng, coverage), `prompt.py` SYSTEM, `corpus.py` (chunker chung cho train + serve), `nerlabel.py`, `llm.py` (Qwen+LoRA generate), `config.py` (bind 127.0.0.1), `app.py` (auth + CORS), `api/chat.py` (schema v2 `{answer, sources, blocks, intent, recommendations}`), frontend Next.js + Antd X (`page.tsx` NEXT_PUBLIC_API_URL, type `Source` có doc/url/heading/chunk_id), `apps/backend/tests/` (pytest + Playwright + CI)
- **Infra Sprint 1:** Postgres 16 + pgvector 0.8.6 + Alembic + docker-compose (pgvector/pgvector:pg16); 15 bảng: app_user (argon2id), user_interest, interaction_event, recommendation_log, venue, event (calendar: lunar|solar), event_segment (phase: lễ|hội), artifact, poi (source: osm|manual), media_asset, story, passage_embedding (vector(1024), khóa chunk_id `<tên bài>#<i>`), audit_log; ràng buộc NOT NULL nguồn ở mức DB
- **Quy ước DB:** id TEXT `<PREFIX>-<NNNNNN>` sequence cấp, không max+1; mọi CHECK ngữ nghĩa ở DB không phải app; TIMESTAMPTZ; PG password từ .env không commit
- **Phân tách đường truy vấn:** /api/chat giữ index trong RAM (p95 <50ms, không RTT mạng); /api/graph đọc PG (persist giữa restart); mất PG → 503 với message hướng dẫn, không silent degradation
- **Kênh vector Sprint 3 — thiết kế từ đầu cho 3 kênh:** BM25 từ + BM25 n-gram (4-gram trên text bỏ dấu) + vector pgvector dim 1024, hợp nhất RRF (k=60); điều kiện tham gia kênh vector: `coverage >= MIN_COVERAGE` **hoặc** `cosine >= θ` (không để coverage thuần IDF triệt tiêu kênh vector); θ hiệu chỉnh trên OUT_OF_DOMAIN, đánh đổi NFR04↔NFR07 báo cáo cùng bảng; nhúng bằng mlx-embeddings (không torch)
- **Công thức gợi ý Sprint 4:** `score(d) = α·GraphAffinity + β·ProfileAffinity + γ·CrossDomainBonus − δ·Seen` → MMR; trọng số ngầm định: view +1, dwell>20s +2, click +2, save +3, dismiss −2, suy giảm nửa chu kỳ 14 ngày; β=0 khi chưa có hồ sơ
- **Sổ ý định → thẻ Sprint 5:** research → Artifact/Museum/SamePeriod/RelatedCraft; attend_event → Schedule/VenueMap/Weather/PrepChecklist/Viewpoint/Parking; plan_trip → VenueMap/Nearby/Food/Weather; learn → NarrationBlock+Related; compare → ComparisonTable; verify → CorrectionBlock; 6 lớp ý định (research | attend_event | plan_trip | learn | compare | verify)
- **API ngoài song song:** asyncio.gather chồng lên bước sinh để ẩn độ trễ; suy giảm tường minh khi API chết (ca kiểm thử)
- **Embedding model:** Qwen/Qwen2.5-Embedding local, dim 1024, không tinh chỉnh v1
- **Bảng đối chiếu Nam Bộ** (trả lời ghi chú mentor): cải lương ↔ Nhã nhạc/Hát tuồng; đàn ca tài tử ↔ tài liệu cùng danh mục; áo bà ba ↔ bản ghi làng nghề + cổ vật; Nhà cổ Huỳnh Thủy Lê ↔ di tích cùng phường qua in_ward — demo bằng Huế, cơ chế độc lập vùng
- **Nguồn dữ liệu Sprint 2:** Wikidata P625 → Nominatim (1 req/s, User-Agent, cache) → kiểm mắt 50 điểm; sự kiện: Cục Di sản (dsvh.gov.vn), cổng TTĐT, Sở Du lịch; cổ vật: chammuseum.vn, baotangcovatcungdinh.vn, danh mục Bảo vật quốc gia

### UX Design Requirements

Tài liệu UX spine riêng (DESIGN.md/EXPERIENCE.md) chưa tạo. Thay vào đó, **Epic 2 nhánh B là epic thiết kế chính thức**: design tokens, component specs, layout specs và cấu hình Antd X cho form user + chatbot được deliverable tại đó. Các yêu cầu UI/UX còn lại nằm trong FR23 (trang chi tiết), FR28 (3D + audio), NFR09 (không onboarding), NFR10 (WCAG 2.1 AA) — Epic 8 mở đầu bằng 1 story thiết kế riêng cho trang chi tiết, còn lại đưa vào stories như acceptance criteria.

### NFR cắt ngang (cross-cutting)

Các NFR sau áp dụng cho **mọi epic**, không thuộc về một epic nào — phải được tuân thủ khi viết story và kiểm tra ở Epic 10:

- **NFR15 (Bảo trì — modularity):** nạp/graph/truy hồi/sinh/gợi ý/tư vấn/UI = mô-đun giao diện tách biệt. Mỗi epic phải giữ ranh giới mô-đun này.
- **NFR17 (Mở rộng):** thêm vùng/danh mục/bản ghi **không sửa mã**; thẻ tư vấn mới chỉ cần đăng ký bộ sinh (sổ registry của Epic 7).
- **NFR18 (Khả chuyển):** một máy, không dịch vụ AI ngoài, không khóa API. Mọi tích hợp ngoài (Open-Meteo, Overpass) phải có suy giảm tường minh.

### FR Coverage Map

- FR01: Epic 2 nhánh B (thiết kế form UI) + Epic 3 (xây logic auth argon2id, JWT cookie, endpoint bảo vệ)
- FR02: Epic 1 (thu thập dataset ban đầu) + Epic 4 (hệ thống CRUD bền vững)
- FR03: Epic 1 (thu thập venue/event/artifact) + Epic 4 (ràng buộc nguồn mức DB)
- FR04: Epic 1 (trích xuất + đồ thị lần đầu) + Epic 4 (pipeline trích xuất khi nạp mới)
- FR05: Epic 1 (dựng đồ thị) + Epic 4 (cập nhật đồ thị khi CRUD)
- FR06: Epic 4 (rà soát trích xuất, audit_log trước/sau)
- FR07: Epic 6 (suy ra hồ sơ, không yêu cầu khai)
- FR08: Epic 6 (tương tác ngầm định, suy giảm, xem/sửa)
- FR09: Epic 6 (gợi ý kèm reason_path, /api/recommend)
- FR10: Epic 6 (xuyên danh mục ≥1/5, gate Epic 1 xong)
- FR11: Epic 6 (đa dạng ≤3 cùng danh mục)
- FR12: Epic 5 (query planner + operators, recall@1 ≥95%; vector có điều kiện theo spike)
- FR13: Epic 6 (xếp hạng lại theo hồ sơ)
- FR14: Epic 2 nhánh A (model) + Epic 2 nhánh B (thiết kế chat UI) + Epic 5 (chat chỉ văn bản, trả lời từ context)
- FR15: Epic 5 (trích nguồn `[Nguồn: ... — url]`, frontend hiển thị url)
- FR16: Epic 5 (đính chính giả định sai câu đầu)
- FR17: Epic 7 (phân loại ý định 6 lớp, macro-F1 ≥85%)
- FR18: Epic 7 (thẻ khớp sổ đăng ký, assert 0 bịa, provenance)
- FR19: Epic 7 (thẻ Lịch sự kiện, âm lịch soạn tay)
- FR20: Epic 7 (Open-Meteo + prep_rules.yaml ~15 luật)
- FR21: Epic 7 (POI Overpass + cache, fallback soạn tay)
- FR22: Epic 7 (địa điểm, giờ mở, giá vé, bảo tàng + phòng)
- FR23: Epic 8 (trang chi tiết: ảnh, story, timeline, map)
- FR24: Epic 5 (endpoint truy vết: hạt giống, hạng kênh, cổng)
- FR25: Epic 2 nhánh B (thiết kế trang tài khoản) + Epic 3 (xuất/xóa dữ liệu, không thể cắt)
- FR26: Epic 9 (dashboard sức khỏe — việc mới)
- FR27: Epic 9 (bộ đánh giá + report NFR16 — phần lớn [ADOPTED], đo liên tục từ Epic 4)
- FR28: Epic 8 (3D .glb + audio 2 ngôn ngữ)
- FR29: Epic 8 (media_asset: giấy phép, đóng góp, URL gốc)
- FR30: Epic 8 (script audio có bằng chứng, chặn tổng hợp)

## Epic List

### Epic 1: Khởi động — Thu thập dữ liệu

Epic khởi động dành cho team 5 người. Thu thập toàn bộ dữ liệu nền (không bao gồm thiết kế — thiết kế chuyển sang Epic 2):

- **Crawl 45 bài Wikipedia Huế/Đà Nẵng** + ~35 tài liệu mới (Nghệ thuật +6, Lễ hội +8, Làng nghề +8, Ẩm thực +6)
- **Thu thập bản ghi:** 50 venue (Wikidata P625 → Nominatim → kiểm mắt), 20 event + phần lễ/hội, 35 artifact
- **Dựng đồ thị deterministic** (entity/year/doc/category/region + venue/event/artifact), tách đoạn + sinh tập train/valid
- **Giao dataset dạng file** (corpus text, records JSON/CSV, graph artifacts) — **chưa nạp DB; Epic 4 mới nạp vào PostgreSQL**

**FRs covered:** FR02, FR03, FR04, FR05 | **NFRs:** NFR14
**Deliverable:** dataset corpus + records data (JSON/CSV) + graph artifacts + train/valid data — **chưa phải DB rows**.

### Epic 2: Huấn luyện model & Thiết kế giao diện

Epic song song 2 nhánh, bố trí theo thế mạnh team — **chỉ PO (hungheo) train model**, các thành viên khác làm giao diện + test:

- **Nhánh A — Huấn luyện model (PO, solo):** migrate sang **Qwen3-4B + LoRA** (`models/peft-adapter/` có sẵn, eval_loss 0.3495) — **LoRA chỉ dạy cách trả lời** (văn phong, citation, refusal), không tham gia retrieval; sinh dữ liệu train (bootstrap), huấn luyện, đánh giá gold set (NER micro-F1, citation faithful, refusal), chốt checkpoint.
- **Nhánh B — Thiết kế giao diện & cấu hình component (4 thành viên):** design tokens (màu, typography, spacing), form đăng ký/đăng nhập, trang tài khoản, khung chat Antd X (Bubble/Sources/Suggestion/Chips), TopBar, Landing, trạng thái loading/error/empty/refusal, tooltip reason_path, chuẩn WCAG 2.1 AA; thành viên thực hiện test giao diện.

**FRs covered (nhánh A — model):** FR14 (phần model) | **(nhánh B — UI):** FR01, FR14, FR25
**NFRs:** NFR09, NFR10
**Phụ thuộc:** Epic 1 (train data + corpus). Train có thể bắt đầu trên corpus v1 trong khi dữ liệu v2 vẫn crawl.
**Deliverable nhánh A:** model LoRA ở `models/lora-serve/` + báo cáo eval gold set. **Deliverable nhánh B:** design tokens, component specs, layout specs, cấu hình Antd X sẵn dùng.

### Epic 3: Tài khoản & Quyền riêng tư

Người dùng đăng ký/đăng nhập an toàn (argon2id, JWT cookie HttpOnly, bind 127.0.0.1), đồng ý có thông báo trước khi ghi tương tác; trang tài khoản hiển thị hồ sơ sở thích kèm hành vi sinh ra nó, xuất tệp máy đọc được (`POST /api/me/export`) và xóa vĩnh viễn (`DELETE /api/me/data`). Xây form theo design Epic 2.

**FRs covered:** FR01, FR25 | **NFRs:** NFR11, NFR12
**Phụ thuộc:** Epic 2 nhánh B (design form/trang tài khoản).
**Song song:** Epic 3 và **Epic 4 độc lập với nhau** (3 phụ thuộc 2B, 4 phụ thuộc 1) — **chạy song song sau Epic 1/2** để giảm áp lực bottleneck Epic 4.
**Ranh giới với Epic 6:** Epic 3 xây **trang tài khoản + xuất/xóa dữ liệu** (FR25); hồ sơ sở thích được **tính toán bởi Epic 6** (FR07/FR08) qua API — Epic 3 chỉ hiển thị + bật/tắt/đóng góp ý, không tự triển khai công thức suy luận.

### Epic 4: Hệ thống CRUD & Rà soát quản trị

Xây hệ thống CRUD bền vững (endpoint + DB) quản lý kho ngữ liệu và bản ghi đã thu thập ở Epic 1: thêm/sửa/xóa tài liệu tự động dựng lại đồ thị; bản ghi thiếu `source_url`/`source_sentence` bị từ chối **ở mức DB** kèm lỗi mức trường; trích xuất chạy lại khi nạp tài liệu mới; rà soát đỉnh/cạnh mới ghi audit_log kèm giá trị trước/sau.

**FRs covered (phần hệ thống):** FR02, FR03, FR04, FR05, FR06 | **NFRs:** NFR14
**Phụ thuộc:** Epic 1 (dataset + graph artifacts để nạp vào DB).
**Bottleneck:** 5 epic phụ thuộc Epic 4 (5, 6, 7, 8, 9) — **chạy song song với Epic 3** (hai epic độc lập) để giảm áp lực lịch trình.

### Epic 5: Query planner & Trả lời có căn cứ

Theo kiến trúc chatbot (`docs/chatbot.md`): intent router **8 lớp** (overview/field/timeline/relationship/section/comparison/open_text/out_of_scope) → **query planner chọn operator** (exact claim / timeline / graph 1–2 hop / section narrative / text hybrid) → **Evidence Context Builder** chọn 3–8 evidence + cấp citation ID → Qwen3-4B sinh → **grounding gate** (pre-gen + post-gen). Response đúng 1 trạng thái: `answered` / `clarify` / `abstained`. Endpoint truy vết phơi plan, operator chạy, hạng Text operator.

**FRs covered:** FR12, FR14, FR15, FR16, FR24 | **NFRs:** NFR04, NFR05, NFR07
**Phụ thuộc:** Epic 1 (corpus + đồ thị) + Epic 2 nhánh A (Qwen3-4B + LoRA) + Epic 2 nhánh B (chat UI design).
**Story riêng — "Spike kênh dense vector":** chatbot.md đặt vector **có điều kiện** ("chỉ nếu eval chứng minh có lợi"). Spike đo dense top-3 ≥70% trên PARAPHRASE — đạt mới xây kênh + hiệu chỉnh θ; không đạt thì giữ 2 kênh BM25 (bảng tách kênh SM-10 vẫn xuất cho 2 kênh).

### Epic 6: Cá nhân hóa & Gợi ý biện minh

Hồ sơ sở thích suy ra từ tương tác (view +1, dwell>20s +2, click +2, save +3, dismiss −2, suy giảm nửa chu kỳ 14 ngày); gợi ý `α·GraphAffinity + β·ProfileAffinity + γ·CrossDomainBonus − δ·Seen` + MMR; API `GET /api/recommend?seed=<node>&k=5` trả reason_path; ≥1/5 gợi ý xuyên danh mục; không onboarding.

**FRs covered:** FR07, FR08, FR09, FR10, FR11, FR13 | **NFRs:** NFR08, NFR09
**Phụ thuộc:** Epic 1 (gate: mọi danh mục ≥8 tài liệu) **+ Epic 3** (bảng interaction_event + consent middleware đã ghi sự kiện). Cả hai phải xong trước khi Epic 6 bắt đầu.
**Ranh giới với Epic 3:** Epic 6 triển khai **công thức suy luận + API hồ sơ**; Epic 3 là consumer (trang tài khoản hiển thị, bật/tắt).

### Epic 7: Tư vấn chủ động theo ý định

Phân loại ý định 6 lớp (regex + từ vựng); sổ đăng ký intent → card; thẻ Lịch (âm lịch soạn tay), Bản đồ, Thời tiết (Open-Meteo) + Chuẩn bị (~15 luật prep_rules.yaml), Điểm quan sát + Chỗ gửi xe (Overpass + cache), Địa điểm/Artifact; API ngoài chạy song song asyncio.gather; **0 trường bịa — assert tự động 100%**.

**FRs covered:** FR17, FR18, FR19, FR20, FR21, FR22 | **NFRs:** NFR06, NFR13
**Phụ thuộc:** Epic 4 (bản ghi venue/event/artifact từ DB) + Epic 5 (retripipelines/evaluation/định tuyến ý định).

### Epic 8: Trang chi tiết nội dung & 3D/Audio

Trang chi tiết `/explore/[node]` — nơi đọc/nghe/xem/xoay 3D một chủ đề văn hóa, mọi dữ kiện truy về nguồn: ảnh lớn + danh sách story, chip liên kết, dòng thời gian, bản đồ Leaflet, thực thể liên quan; 3D .glb (Three.js, Draco/Meshopt ≤30 MB) + audio VI/EN kèm transcript; media_asset có giấy phép/đóng góp/URL gốc; script audio qua kiểm tra bằng chứng trước khi tổng hợp giọng nói; fallback ngoại tuyến không trang trắng (NFR20: mất R2/Azure → vẫn đầy đủ text/transcript, 3D+audio chỉ báo "tạm thời không khả dụng").

**FRs covered:** FR23, FR28, FR29, FR30 | **NFRs:** NFR10, NFR19, NFR20
**Phụ thuộc:** Epic 4 (bản ghi media_asset/artifact/venue từ DB).
**Ghi chú:** Epic 2 nhánh B chỉ thiết kế form + chatbot — **story đầu của Epic 8 phải là story thiết kế** (layout trang chi tiết: ảnh lớn + story panel, timeline, map, 3D viewer, audio) trước khi build.

### Epic 9: Quản trị & Đánh giá đo lường (admin)

Dashboard sức khỏe: số tài liệu/danh mục, thống kê đồ thị, trường thiếu nguồn, hàng chờ rà soát, chỉ số mới nhất; toàn bộ bộ đánh giá chạy được và xuất report ghi mô hình, checkpoint adapter, phiên bản prompt, phiên bản kho ngữ liệu, cấu hình. **Đẩy xuống sát cuối theo thứ tự cắt phạm vi PRD** (cut #4: giao diện quản trị → CLI + trang thống kê chỉ đọc).

**FRs covered:** FR26, FR27 | **NFRs:** NFR16
**Phụ thuộc:** Epic 4 (DB có dữ liệu + hàng chờ rà soát) + Epic 5 (retrieval đo được).
**Phân chia công việc trong epic:**
- **FR27 (bộ đánh giá + report NFR16) — phần lớn [ADOPTED]:** code pipelines/evaluation/ đã tồn tại (`eval_retrieval.py` 215 cases, `eval_attribution.py`, `score_gold.py` metadata SHA-256). Việc của epic này = wrap + đảm bảo report có đủ trường NFR16. **Phải được dùng đo liên tục từ Epic 4 trở đi** (đo p95 ngay từ Sprint 1 — NFR01), không chờ đến Epic 9 mới chạy.
- **FR26 (dashboard sức khỏe) — việc mới:** UI dashboard đọc DB + eval artifacts.
**Ghi chú:** Nếu trượt tiến độ, nội dung admin bị cắt đầu tiên — downgrade thành CLI + trang thống kê chỉ đọc; FR27 (bộ đánh giá) vẫn giữ vì nó là mandatory cut.

### Epic 10: Kiểm thử, đo lường cuối & Đóng gói

unittest (backend, có sẵn) + Playwright (E2E) + CI; assert NFR06 + FR30 tự động; đo toàn bộ SM-1…SM-12 (recall@1, trích nguồn, từ chối, precision@5 + Cohen's κ, macro-F1, p95, SUS 6–8 người); báo cáo cuối + video hướng dẫn.

**NFRs covered:** NFR01, NFR02, NFR03 + toàn bộ SM
**Phụ thuộc:** Tất cả epic trước phải xong (đo lường trên sản phẩm cuối). Kiểm tra cả NFR cắt ngang (NFR15, NFR17, NFR18).
