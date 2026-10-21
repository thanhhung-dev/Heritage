---
id: SPEC-HeritageGraph
companions:
  - glossary.md
  - success-metrics.md
  - roadmap.md
sources:
  - ../../planning-artifacts/prds/prd-HeritageGraph-2026-09-08/prd.md
  - ../../planning-artifacts/prds/prd-HeritageGraph-2026-09-08/addendum.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# SPEC: HeritageGraph

## Why

Người quan tâm văn hóa Huế – Đà Nẵng phải chọn giữa bài viết tĩnh (không trả lời thắc mắc riêng) và chatbot đại trạ (bia khi thiếu dữ kiện). HeritageGraph là trợ lý tiếng Việt **chạy 100% cục bộ** cho capstone CMU-SE 450 (C1SE.50, 13 tuần còn lại đến 06/12/2026): trả lời kèm trích nguồn bắt buộc, từ chối lịch sự khi thiếu bằng chứng, gợi ý xuyên danh mục biện minh bằng đồ thị tri thức tất định (mọi đỉnh truy về chuỗi nguyên văn — không đỉnh nào do LLM bịa), và đưa người dùng từ *quan tâm* đến *tham dự* lễ hội bằng bối cảnh thực tế. Hai đóng góp học thuật nền tảng đã đo được: đồ thị 510 đỉnh/1135 cạnh (O2) và trích nguồn 0.7037/từ chối 0.9167 (O5) — 9 mục tiêu còn lại là 13 tuần.

## Capabilities

- **CAP-1**
  - **intent:** Người dùng có tài khoản với quyền riêng tư được bảo vệ — đăng ký/đăng nhập argon2id + JWT cookie HttpOnly, ghi hành vi chỉ sau đồng ý có thông báo, xuất dữ liệu máy đọc được và xóa vĩnh viễn hồ sơ + lịch sử tương tác.
  - **success:** Endpoint cá nhân chưa xác thực bị từ chối (test tự động); `POST /api/me/export` trả tệp đầy đủ; `DELETE /api/me/data` xóa sạch hồ sơ lẫn interaction_event (kiểm tra DB); không onboarding bắt buộc — hỏi + nhận gợi ý ngay lần đầu (NFR09).

- **CAP-2**
  - **intent:** Quản trị viên nạp và cai trị nền tri thức — CRUD tài liệu + bản ghi venue/event/artifact/media_asset, trích xuất tất định (không gọi mô hình), đồ thị dựng lại, rà soát có audit_log.
  - **success:** Bản ghi thiếu `source_url`/`source_sentence` bị từ chối **ở mức DB** kèm lỗi mức trường (NFR14, test); mọi tên trích ra là chuỗi con nguyên văn của nguồn (NER micro-F1 ≥0.75 kèm per-type, SM-9); mọi quan hệ đồ thị có chuỗi nguồn.

- **CAP-3**
  - **intent:** Hệ thống truy hồi đúng đoạn gốc bất kể biến thể ngôn ngữ — có dấu, không dấu, tên gọi khác, diễn giải lại — bằng 3 kênh (BM25 từ, BM25 n-gram, vector pgvector 1024) hợp nhất RRF, neo/mở rộng/xếp lại bằng đồ thị.
  - **success:** recall@1 ≥95% in-domain kể cả biến thể (SM-1); bảng tách kênh đo đóng góp từng kênh riêng + tổ hợp (ablation, SM-10); endpoint truy vết phơi hạt giống, hạng từng kênh, các cổng.

- **CAP-4**
  - **intent:** Hệ thống trả lời chỉ từ bối cảnh đã truy hồi, với trích nguồn bắt buộc và cổng từ chối 3 lớp (neo đồ thị, bằng chứng, coverage) — LLM cục bộ Qwen2.5-3B-4bit + LoRA chỉ viết phần kể chuyện.
  - **success:** Mỗi câu khẳng định kèm `[Nguồn: <câu nguyên văn> — <url>]` với url hiển thị frontend; trung thực trích nguồn ≥85%, độ phủ ≥90% (SM-2); từ chối ≥90% câu ngoài phạm vi, 0 câu bịa ngoài phạm vi (SM-3); giả định sai được đính chính ngay câu đầu ≥90% (FR16).

- **CAP-5**
  - **intent:** Hệ thống cá nhân hóa không bao giờ yêu cầu khai sở thích — hồ sơ suy ra từ hành vi (view/dwell/click/save/dismiss, suy giảm nửa chu kỳ 14 ngày) và mỗi gợi ý kèm đường đi đồ thị biện minh (`reason_path`), có xuyên danh mục và đa dạng.
  - **success:** Hai người dùng hồ sơ khác nhau nhận thứ tự gợi ý khác nhau, khác biệt truy nguyên về trọng số hồ sơ (FR13); precision@5 ≥70% đánh giá bởi 2 người + Cohen's κ (SM-6); ≥1 trong 5 gợi ý đầu thuộc danh mục khác hạt giống (≥30% xuyên miền); ≤3/5 cùng danh mục trừ khi ít danh mục; hồ sơ hiển thị từng sở thích kèm hành vi sinh ra nó.

- **CAP-6**
  - **intent:** Khi người dùng chuẩn bị đi dự lễ hội, hệ thống chủ động cấp bối cảnh thực tế theo ý định (6 lớp: research/attend_event/plan_trip/learn/compare/verify, phân loại bằng regex + từ vựng) — lịch (âm lịch quy đổi tay), bản đồ, thời tiết, danh mục chuẩn bị theo luật tường minh, điểm quan sát, chỗ gửi xe.
  - **success:** **0 trường bịa trong thẻ tư vấn** — assert tự động 100%: mọi trường = đúng trường bản ghi nguồn hoặc phản hồi API, mang `provenance` + `fetched_at` (NFR06, NFR13, SM-4); macro-F1 ý định ≥85% trên ≥100 câu gán nhãn tay (SM-7); API ngoài chạy song song, thẻ hoàn thành ≤2s (NFR02); API chết → thẻ ghi "không có dữ liệu dự báo", không đoán; lễ xa >16 ngày → khí hậu trung bình, thẻ ghi rõ "khí hậu, không phải dự báo".

- **CAP-7**
  - **intent:** Người dùng khám phá qua giao diện web — khung chat thẻ, trang chi tiết Tapestry (ảnh lớn, story, dòng thời gian, bản đồ, chip liên kết), trình 3D .glb + audio narration 2 ngôn ngữ.
  - **success:** Trang chi tiết ≤3s (SM-8, NFR03); .glb ≤30MB tải ≤3s trên 4G, audio phát ≤1s (NFR19); mỗi audio có transcript đầy đủ, mỗi câu khẳng định transcript truy về câu nguồn hoặc đánh dấu lời dẫn biên tập — kiểm tra tự động **chặn tổng hợp giọng nói** nếu không đạt (FR30, SM-5); mất R2/Azure → trang vẫn đầy đủ văn bản/transcript/chip, 3D+audio hiện "tạm thời không khả dụng" (NFR20); WCAG 2.1 AA phần áp dụng được (NFR10).

- **CAP-8**
  - **intent:** Quản trị viên thấy sức khỏe hệ thống và kết quả đo lường — dashboard (số tài liệu/danh mục, thống kê đồ thị, trường thiếu nguồn, hàng chờ rà soát, chỉ số mới nhất) và bộ đánh giá chạy được toàn bộ chỉ số.
  - **success:** Mọi chỉ số tính và xuất báo cáo ghi: mô hình, checkpoint adapter, phiên bản prompt, phiên bản kho ngữ liệu, cấu hình (NFR16, FR27); pytest + Playwright + CI chạy xanh; 2 assert tự động (NFR06 + FR30) xanh (gate Sprint 6).

- **CAP-9**
  - **intent:** Mọi hành vi hệ thống kiểm tra được từ ngoài — endpoint truy vết phơi đầy đủ đường quyết định truy hồi, và bộ đánh giá lượng hóa đóng góp của từng thành phần (ablation tách kênh) cùng tính không-suy-giảm.
  - **success:** `GET /api/...` truy vết trả hạt giống, hạng từng kênh, độ gần đồ thị, thành phần cho điểm, kết quả từng cổng (FR24); trích nguồn + từ chối không giảm sau khi lớp tư vấn xuất hiện — giữ ≥0.7037/0.9167, đo lại Sprint 5 (SM-11, O11).

## Constraints

- Mọi phát biểu thực tế (ngày, tọa độ, thời tiết, chỗ gửi xe, thuộc tính cổ vật, gợi ý) **kết xuất từ bản ghi có kiểu mang nguồn gốc** — LLM chỉ viết phần kể chuyện, audio chỉ phát kể chuyện. Ràng buộc cứng từ mentor, không được cấu trúc hóa bằng prompt suông.
- Chạy 100% cục bộ trên một máy: Qwen2.5-3B-4bit + LoRA (MLX), không dịch vụ AI ngoài, không khóa API (NFR18); server demo bind 127.0.0.1, không 0.0.0.0.
- Bản ghi thiếu nguồn **không lưu được** — ràng buộc mức DB, không phải app (NFR14); mọi trường thẻ mang `provenance` + `fetched_at` (NFR13).
- Không bao giờ cắt dù trượt tiến độ: cổng từ chối, trích nguồn bắt buộc, assert không-bịa-trường (NFR06), assert bằng chứng script (FR30), bộ đánh giá. Thứ tự cắt cố định trước: 3D 4→2→1, POI cửa hàng/quà, SUS 8→4, quản trị→CLI, kho 80→65 (giữ tối thiểu 8/danh mục), audio chỉ tiếng Việt.
- Hiệu năng: p95 đầu-cuối ≤8s (đo liên tục từ Sprint 1), gợi ý + thẻ ≤2s, trang chi tiết ≤3s, .glb ≤30MB/≤3s trên 4G, audio phát ≤1s (không tính thời gian tổng hợp — sinh trước).
- Âm lịch quy đổi **soạn tay** ~20 lễ hội 2026–2027, không dùng thư viện (lệch múi giờ có thể lệch 1 ngày). Phân loại ý định bằng regex + từ vựng, không fine-tune.
- Việc rủi ro cao làm trước; không lớp nào xây trên lớp chưa đo. Gate: mọi danh mục ≥8 tài liệu trước khi cá nhân hóa bắt đầu (FR10 phụ thuộc); kiểm độ phủ OSM đầu Tuần 8; chốt danh sách 3D đầu Tuần 6.
- θ (ngưỡng cosine cổng ngữ nghĩa) hiệu chỉnh trên OUT_OF_DOMAIN; NFR04 (recall) và NFR07 (từ chối) báo cáo cùng bảng — đánh đổi không được che giấu.
- Xác thực mọi endpoint đọc/ghi dữ liệu cá nhân (NFR11); xác thực hoàn thành trước khi dữ liệu cá nhân đầu tiên được lưu (NFR12).

## Non-goals

- Không đặt vé/tour/giao dịch; không dữ liệu đám đông; không giao thông thời gian thực.
- Không nhận giọng nói (chỉ gõ văn bản tiếng Việt; audio là narration soạn trước); không dịch đa ngữ giao diện.
- Không mobile native — v1 là web.
- Không chứng nhận lịch sử chính thức — nguyên mẫu học thuật, không nguồn sử liệu.
- Không mở rộng vùng thứ ba (Nam Bộ) — cơ chế độc lập vùng sẵn sàng (bảng đối chiếu), nhưng dữ liệu phải crawl lại + sinh lại eval; ghi tường minh trong báo cáo.
- Không quét 3D thực địa (chỉ nguồn mở); không nhận dạng tự động nội dung ảnh (quản lý qua metadata); không gợi ý lọc cộng tác.
- Không fine-tune cho phân loại ý định.

## Success signal

Cuối Sprint 13 (06/12/2026), một người dùng chưa từng khai báo gì hỏi "Nhã nhạc cung đình Huế có gì đặc biệt?" bằng tiếng Việt không dấu, nhận câu trả lời kèm `[Nguồn: ...]` truy về được, gợi ý "Làng nghề làm nón lá" kèm đường đi đồ thị; hỏi "Chùa Một Cột xây năm nào?" → từ chối lịch sự; hỏi về Lễ tế Xã Tắc → chuỗi thẻ Lịch/Bản đồ/Thời tiết/Chuẩn bị/Điểm quan sát/Chỗ gửi xe 100% truy về bản ghi — toàn bộ chạy trên một máy không internet AI, mọi chỉ số §7 (success-metrics.md) có số trong report tái lập được.

## Assumptions

- Hội đồng coi PRD là SRS chính thức thay vì proposal riêng (giữ nguyên mã FR/NFR để truy vết).
- Mentor chấp nhận cơ chế độc lập vùng + bảng đối chiếu Nam Bộ, không đòi demo thật Nam Bộ.
- Edge TTS đủ chất lượng cho narration 2 ngôn ngữ; nếu không, chọn TTS cục bộ khác cũng ngoại tuyến.
- `<model-viewer>` hoặc Three.js cho 3D — chốt Tuần 10 theo tài sản thực có.
- SUS 6–8 người đủ quy mô cho capstone.
- Repo phát triển chính trên Mac (MLX); máy Windows hiện chỉ soạn docs, mọi lệnh đo/train chạy trên Mac.

## Open Questions

- Baseline base↔LoRA trên cùng 76 mẫu và PARAPHRASE 9/39 đã chốt ngày 08/09/2026; xem `pipelines/evaluation/baseline-summary.md`.
- Mô hình 3D giấy phép mở — chốt đầu Tuần 6; nếu chỉ 2 → F12 hẹp lại (BLOCKER Sprint 4).
- Độ phủ OSM quanh Nam Ô + Bảo tàng Chăm — kiểm đầu Tuần 8; thưa → POI soạn tay (BLOCKER Sprint 5).
- Người đánh giá thứ hai cho precision@5 + nhãn NER vàng (Cohen's κ) — chưa chốt ai (BLOCKER O11).
- Người tham gia nghiên cứu SUS 6–8 — chưa có danh sách.
- θ chưa có số — hiệu chỉnh Tuần 5; đánh đổi NFR04↔NFR07 phải thành bảng.
- Giấy phép ảnh tiêu biểu mỗi thực thể (ảnh 1/entity giữ từ v1.0) — nguồn cần rà khi nhập F03.
