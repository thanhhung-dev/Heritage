---
title: "PRD — HeritageGraph"
project: CulturalMemoryGraph (CMG) / HeritageGraph
status: draft
created: 2026-09-08
updated: 2026-09-08
---

# PRD: HeritageGraph

*A Personalized GraphRAG Assistant for Exploring, Understanding and Planning Local Cultural Experiences — Huế & Đà Nẵng*

## 0. Document Purpose

PRD này là **SRS chính thức** của đồ án capstone CMU-SE 450 (nhóm C1SE.50, 1 người — Dương Thanh Hùng, GVHD ThS. Nguyễn Thị Thanh Tâm, 27/08–06/12/2026). Nó phục vụ: (1) hội đồng — đối chiếu trực tiếp với proposal-vi v2.0 đã duyệt; (2) downstream BMad workflow (architecture, epics/stories, sprint planning) — nguồn chuẩn duy nhất cho phạm vi; (3) chính tác giả — hợp đồng phạm vi 13 tuần còn lại.

Nguồn gốc: PRD này **chuyển thể** từ `docs/proposal-vi.md` v2.0 (được mentor duyệt, chứa O1–O11, F01–F14, FR01–FR30, NFR01–NFR20) và `docs/upgrade-plan.md` (hiện trạng as-built + lộ trình 13 tuần). Nó không thay thế hai tài liệu đó — mọi FR/NFR giữ nguyên mã số để truy vết. Tài liệu kèm: `docs/architecture.md` (kiến trúc as-built + thiết kế mục tiêu), `docs/metrics.md` (định nghĩa chỉ số đo).

**Phương châm xuyên suốt** *(ràng buộc cứng từ mentor):* mọi phát biểu thực tế (ngày, tọa độ, thời tiết, chỗ gửi xe, thuộc tính cổ vật, gợi ý) **kết xuất từ bản ghi có kiểu mang nguồn gốc** — LLM chỉ viết phần kể chuyện; audio chỉ phát kể chuyện. Không bao giờ cắt: cổng từ chối, trích nguồn bắt buộc, khẳng định không-bịa-trường, bộ đánh giá.

## 1. Vision

Người quan tâm văn hóa Huế – Đà Nẵng hôm nay phải chọn giữa hai thứ đều tệ: bài viết tĩnh không trả lời được thắc mắc riêng, hoặc chatbot đại trạ bịa khi thiếu dữ kiện. HeritageGraph là trợ lý tiếng Việt **chạy 100% cục bộ** trả lời câu hỏi văn hóa kèm trích nguồn bắt buộc dạng `[Nguồn: <câu nguyên văn> — <url>]`, từ chối lịch sự khi thiếu bằng chứng, và đo được cả hai hành vi đó.

Điểm khác biệt là **đồ thị tri thức tất định** — mọi đỉnh truy về được chuỗi nguyên văn trong tài liệu nguồn, không đỉnh nào do LLM bịa ra. Đồ thị vừa neo câu hỏi vào miền tri thức (cổng từ chối), vừa mở rộng gợi ý xuyên danh mục (học sinh xem Nhã nhạc được gợi ý Hát tuồng qua cạnh `in_category`, khách du lịch xem Cao lầu được gợi Làng Non Nước). Cá nhân hóa suy ra từ hành vi — **không bao giờ yêu cầu khai sở thích** — mỗi gợi ý kèm đường đi đồ thị biện minh.

Bước cuối: từ *quan tâm* đến *tham dự*. Khi phát hiện người dùng chuẩn bị đi dự lễ hội, hệ thống chủ động cấp bối cảnh thực tế: lịch (kèm quy đổi âm lịch soạn tay), bản đồ, thời tiết, danh mục chuẩn bị sinh bằng luật tường minh, điểm quan sát, chỗ gửi xe — **mỗi trường truy về bản ghi nguồn, không trường nào do LLM sinh**.

**Hiện trạng (đo 05/09/2026):** O2 (đồ thị 510 đỉnh/1135 cạnh) và O5 (trích nguồn 0.7037, từ chối 0.9167) đã xong — hai đóng góp học thuật nền tảng. 9 mục tiêu còn lại là công việc 13 tuần.

## 2. Target User

### 2.1 Jobs To Be Done

- **Học sinh/sinh viên/người trẻ:** "Khi tò mò về một di tích/bộ môn nghệ thuật, tôi muốn hỏi tự do theo cách tôi nghĩ, nhận câu trả lời kèm nguồn tin cậy để trích dẫn, và được gợi ý thứ liên quan mà giáo trình không xếp cạnh nhau."
- **Khách du lịch trong nước & người quan tâm văn hóa:** "Khi dự định tham dự một lễ hội, tôi muốn biết nó diễn ra khi nào (âm lịch quy đổi ra dương lịch), ở đâu (kèm bản đồ), thời tiết thế nào, cần mang gì — để thật sự đi được."
- **Giáo viên:** "Khi soạn bài học, tôi muốn tư liệu có nguồn sẵn dùng — trang chi tiết có trích nguồn, dòng thời gian, audio 2 ngôn ngữ kèm transcript — để đưa vào lớp."
- **Quản trị viên (chính tác giả):** "Khi dữ liệu mới có, tôi muốn nạp, kiểm tra nguồn, rà soát trích xuất, và thấy ngay sức khỏe kho ngữ liệu + đồ thị."
- **Hệ thống (tác nhân nội bộ):** trích xuất tất định (F13), sinh câu trả lời cục bộ (F14).

### 2.2 Non-Users (v1)

- Người cần **đặt vé/tour/giao dịch** — ngoài phạm vi.
- Người dùng **gõ tiếng Anh/nhập giọng nói** — chat chỉ tiếng Việt, chỉ văn bản.
- Nhà nghiên cứu cần **chứng nhận lịch sử chính thức** — sản phẩm là nguyên mẫu học thuật.
- Người dùng **mobile app gốc** — v1 là web.

### 2.3 Key User Journeys

**UJ-1. Minh, sinh viên năm nhất Huế, khám phá theo tò mò riêng.**
- **Persona + context:** 19 tuổi, nghe nhạc cung đình lần đầu ở Festival, muốn hiểu bối cảnh.
- **Entry state:** không đăng nhập bắt buộc (duyệt tự do), web, lần đầu.
- **Path:** hỏi "Nhã nhạc cung đình Huế có gì đặc biệt?" → câu trả lời kèm `[Nguồn: ...]` → nhấp chip "Hát tuồng" trong dải liên quan → trang chi tiết Tapestry (ảnh lớn, story, dòng thời gian, bản đồ) → tiếp tục khám phá.
- **Climax:** gợi ý xuyên danh mục xuất hiện — xem Nhã nhạc (Nghệ thuật) mà hệ thống gợi Làng nghề làm nón lá, **kèm đường đi đồ thị giải thích vì sao**.
- **Resolution:** hồ sơ sở thích ngầm định hình thành (Nghệ thuật +2, Lùng nghề +1); phiên sau gợi ý đã khác.
- **Edge case:** hỏi "Chùa Một Cột xây năm nào?" (ngoài miền — Hà Nội) → hệ thống **từ chối lịch sự**, không bịa.

**UJ-2. Lan, 34 tuổi, kế hoạch đi Lễ tế Xã Tắc từ TP.HCM.**
- **Persona + context:** đi Huế lần đầu với gia đình, không biết lễ âm lịch rơi vào ngày nào.
- **Entry state:** web, tìm "Lễ tế Xã Tắc".
- **Path:** trang chi tiết lễ hội → **thẻ Lịch** (âm lịch quy đổi tay, nguồn) → **thẻ Bản đồ** (tọa độ) → **thẻ Thời tiết** (Open-Meteo) → **thẻ Chuẩn bị** ("có phần lễ → trang phục lịch sự", luật tường minh từ dự báo) → **thẻ Điểm quan sát** + **thẻ Chỗ gửi xe** (Overpass, cached).
- **Climax:** một chuỗi thẻ trả lời "tôi cần làm gì để thật sự đi dự" mà không cần hỏi riêng từng thứ.
- **Resolution:** đi dự được; nếu API thời tiết chết → thẻ ghi **"không có dữ liệu dự báo"**, không đoán.
- **Edge case:** hỏi "Lễ tế Xã Tắc ở Đà Nẵng đúng không?" (giả định sai) → **đính chính ngay câu đầu**.

**UJ-3. Cô Thảo, giáo viên lịch sử, soạn bài về cổ vật cung đình.**
- **Entry state:** web, duyệt danh mục "Cổ vật".
- **Path:** tìm "Bảo tàng Cổ vật Cung đình Huế" → trang chi tiết → tab cổ vật (niên đại, chất liệu, **bảo tàng + phòng trưng bày**) → nghe audio narration Việt/Anh kèm transcript → tải transcript làm tư liệu.
- **Climax:** mọi dữ kiện truy về nguồn → dám trích vào bài giảng.
- **Resolution:** dùng `/explore/[node]` để học sinh tự khám phá có kiểm soát.

**UJ-4. Hùng (tác giả), quản trị nội dung.**
- **Path:** đăng nhập (argon2id) → thêm 8 tài liệu Lễ hội mới (F02) → hệ thống trích xuất tất định + **đồ thị dựng lại** → rà soát đỉnh mới, sửa, xác nhận (F04, ghi audit_log) → dashboard: "Lễ hội 2 → 10 tài liệu; 0 trường thiếu nguồn" (FR26) → chạy bộ đánh giá (F06) → report ghi checkpoint + phiên bản prompt + phiên bản kho (FR27).

**UJ-5. Người dùng yêu cầu quyền riêng tư.**
- **Path:** đăng nhập → trang tài khoản → thấy **hồ sơ sở thích đã suy ra, từng sở thích kèm hành vi sinh ra nó** (view ×3, dwell ×1) → tắt 1 sở thích sai → nhấp **Xuất dữ liệu** (file máy đọc được) → nhấp **Xóa vĩnh viễn** → cả hồ sơ lẫn lịch sử interaction_event biến mất.

## 3. Glossary

- **Kho ngữ liệu (corpus)** — tập tài liệu văn bản đã chuẩn hóa + tách đoạn, mỗi đoạn kèm định vị nguồn (tên bài, URL, vị trí ký tự). Mục tiêu ≥80 tài liệu, ≥8/danh mục.
- **Danh mục** — 1 trong 6: Di tích lịch sử, Ẩm thực, Danh thắng, Nghệ thuật, Lễ hội, Làng nghề (+ cổ vật quản lý qua bản ghi).
- **Đồ thị tri thức (KG)** — networkx dựng tất định từ kho ngữ liệu + danh sách địa điểm; đỉnh: entity/year/doc/category/region (+ event/venue/artifact khi có bản ghi); cạnh có kiểu có trọng số: `mentions, year, related, in_ward, in_region, in_category, is_about`. **Mọi đỉnh truy về chuỗi nguyên văn.**
- **Truy hồi Hybrid RAG + GraphRAG** — 3 kênh (BM25 từ, BM25 n-gram không dấu, vector pgvector dim 1024) hợp nhất bằng RRF, neo/mở rộng/xếp lại bằng lan truyền đồ thị.
- **Cổng từ chối (refusal gate)** — 3 cổng trong `rag.py`: neo đồ thị, bằng chứng, coverage. Khi chặn → context rỗng → model từ chối theo mẫu đã train.
- **Bản ghi có cấu trúc** — `venue` (lat/lon/ward/district), `event` + `event_segment` (phần lễ/phần hội, loại lịch), `artifact` (museum/period/material/room), `poi`, `media_asset`. **Mọi trường bắt buộc `source_url` + `source_sentence` (NFR14, ràng buộc ở mức DB).**
- **Hồ sơ sở thích ngầm định** — suy ra từ interaction_event (view +1, dwell>20s +2, click +2, save +3, dismiss −2), **suy giảm nửa chu kỳ 14 ngày**, không bao giờ khai.
- **Gợi ý biện minh** — mỗi gợi ý kèm `reason_path` (đường đi đồ thị sinh ra nó), ví dụ `Hát tuồng → [in_category] Nghệ thuật → Nhã nhạc cung đình Huế`.
- **Xuyên miền (cross-domain)** — gợi ý thuộc danh mục khác hạt giống; mục tiêu ≥30% trong top-5 (FR10).
- **Ý định (intent)** — 1 trong 6 lớp: `research | attend_event | plan_trip | learn | compare | verify`. Phân loại bằng regex + từ vựng, **không tinh chỉnh mô hình**.
- **Thẻ tư vấn có kiểu** — khối bối cảnh kết xuất từ bản ghi/API ngoài theo ý định: Schedule, VenueMap, Weather, PrepChecklist, Viewpoint, Parking, Artifact/Museum/SamePeriod/RelatedCraft, Comparison, Correction. **Không trường nào do LLM sinh (NFR06).**
- **Tài sản đa phương tiện** — mô hình 3D .glb (Cloudflare R2, nén Draco/Meshopt ≤30 MB), audio 2 ngôn ngữ (Azure Blob), sinh ngoại tuyến sau khi qua kiểm tra bằng chứng script.
- **T (θ)** — ngưỡng cosine của cổng ngữ nghĩa khi kênh vector tham gia; hiệu chỉnh trên OUT_OF_DOMAIN, báo cáo cùng NFR07.

## 4. Features

### 4.1 Nền tảng: tài khoản, riêng tư, lưu trữ (F01, F07)

Mọi endpoint đọc/ghi dữ liệu cá nhân phải xác thực (NFR11). Xác thực hoàn thành **trước** khi dữ liệu cá nhân đầu tiên được lưu (NFR12 nghĩa vụ). Ghi nhận hành vi chỉ sau khi có đồng ý có thông báo.

**Functional Requirements:**

#### FR01: Đăng ký, xác thực, quản lý tài khoản
Người dùng có thể đăng ký, đăng nhập, quản lý phiên. **Consequences (testable):**
- Mật khẩu chỉ lưu dạng băm argon2id
- Phiên phát hành qua cookie HttpOnly (JWT, SameSite=Lax)
- Endpoint được bảo vệ từ chối yêu cầu chưa xác thực
- Máy chủ demo bind 127.0.0.1, không 0.0.0.0

#### FR25: Hồ sơ + dữ liệu cá nhân trong trang tài khoản
Hồ sơ hiển thị kèm hành vi sinh ra từng sở thích, bỏ/tắt được; **Consequences:** xuất tệp máy đọc được (`POST /api/me/export`); xóa vĩnh viễn (`DELETE /api/me/data`) — xóa cả hồ sơ lẫn interaction_event. **Không thể bị cắt** (NFR12).

**Feature-specific NFRs:** NFR11, NFR12 (xem §5).

### 4.2 Nền tri thức: kho ngữ liệu, bản ghi, trích xuất (F02, F03, F13)

Quản trị CRUD tài liệu; bản ghi venue/event/artifact **chỉ lưu khi mọi trường sự kiện có URL nguồn + câu nguồn** (từ chối ở mức trường). Trích xuất F13 **tất định** (không gọi mô hình), chạy khi tài liệu nạp.

**Functional Requirements:**

#### FR02: CRUD tài liệu kho ngữ liệu
Tài liệu chuẩn hóa, tách đoạn kèm định vị nguồn; đồ thị dựng lại với đỉnh mới liên kết về nguồn.

#### FR03: CRUD bản ghi có cấu trúc
**Consequences:** bản ghi thiếu `source_url`/`source_sentence` bị từ chối **ở mức DB** (NFR14) kèm lỗi mức trường. Gồm venue (tọa độ), event (loại lịch, các phần lễ/hội), artifact (niên đại, chất liệu, bảo tàng, phòng), media_asset (giấy phép, người đóng góp, URL nguồn gốc — FR29).

#### FR04: Trích xuất thực thể/quan hệ/hành chính/năm
Đầu ra khớp lược đồ 4 loại, mọi tên trích ra là **chuỗi con nguyên văn** của nguồn.

#### FR05: Dựng + cập nhật đồ thị
Đỉnh/cạnh tạo, gán kiểu, gán trọng số, liên kết về nguồn; **không quan hệ nào tạo mà thiếu chuỗi nguồn**.

#### FR06: Rà soát kết quả trích xuất
Thay đổi ghi vào audit_log kèm giá trị trước/sau.

### 4.3 Truy hồi Hybrid RAG + GraphRAG (F08 — phần truy hồi, F13)

Ba kênh: BM25 từ (có dấu), BM25 n-gram (không dấu, sai chính tả), **vector pgvector** (diễn giải lại — kênh mới Sprint 3). Hợp nhất RRF theo thứ hạng; đồ thị neo + bơm ứng viên + xếp lại.

**Functional Requirements:**

#### FR12: Truy hồi đúng đoạn bất kể biến thể ngôn ngữ
**Consequences:** tài liệu đúng xếp hạng nhất kể cả viết có dấu/không dấu/tên gọi khác/diễn giải lại (recall@1 ≥95%, NFR04); đóng góp từng kênh đo riêng dạng **bảng tách kênh**; endpoint truy vết (FR24) phơi hạt giống, hạng từng kênh, các cổng.

*Ghi chú kỹ thuật (từ upgrade-plan §2.4):* kênh vector chỉ có tác dụng nếu sửa `retriever.py:372` (câu diễn giải không bị chặn trước khi vector nói) và `rag.py:95` (coverage thuần IDF không triệt tiêu kênh vector — chấp nhận `coverage ≥ MIN **hoặc** cosine ≥ θ`).

### 4.4 Trả lời có căn cứ (F08/F09, F14)

Sinh câu trả lời bằng Qwen2.5-3B-4bit + LoRA cục bộ (MLX), chỉ từ bối cảnh đã truy hồi. Cổng từ chối 3 lớp. Đây là đóng góp học thuật đã đo được (0.7037/0.9167) — **không suy giảm khi các lớp mới thêm vào** (đo lại ở Sprint 5, O11).

**Functional Requirements:**

#### FR14: Chat chỉ văn bản, trả lời chỉ từ bối cảnh
**Consequences:** giao diện chỉ nhận văn bản; không sinh câu trả lời khẳng định nào mà không có câu nguồn trích từ tài liệu đã truy hồi.

#### FR15: Trích nguồn hoặc phát biểu thiếu bằng chứng
Mỗi câu trả lời khẳng định kèm `[Nguồn: <câu nguyên văn> — <url>]`; **`url` phải hiển thị ở frontend** (lỗi FR15 cũ: type Source thiếu url — đã sửa trong Tuần 2 docs).

#### FR16: Đính chính giả định sai
Giả định trái nguồn → đính chính **ngay câu đầu** (≥90% câu trái giả định — SM).

### 4.5 Cá nhân hóa & gợi ý biện minh (F08, F11 — phần gợi ý)

Hồ sơ ngầm định có suy giảm; gợi ý = `α·GraphAffinity + β·ProfileAffinity + γ·CrossDomainBonus − δ·Seen` (MMR chống 5 cái lăng liên tiếp). **Cơ chế độc lập vùng** — đáp ứng ghi chú của mentor về ví dụ Nam Bộ bằng bảng đối chiếu cấu trúc (cải lương ↔ Nhã nhạc/Hát tuồng; áo bà ba ↔ bản ghi làng nghề; Nhà cổ Huỳnh Thủy Lê ↔ di tích cùng phường), giữ nguyên cặp địa bàn.

**Functional Requirements:**

#### FR07: Suy ra hồ sơ mà không yêu cầu khai
**Consequences:** nền tảng dùng đầy đủ trước khi có hồ sơ; sau vài tìm/xem đầu tiên hồ sơ đã có sở thích có trọng số.

#### FR08: Ghi tương tác ngầm định, xem/sửa được
Sự kiện view/dwell/click/save/dismiss ghi kèm mốc thời gian + đỉnh đích; trọng số **suy giảm theo thời gian**; người dùng thấy từng sở thích kèm hành vi sinh ra nó.

#### FR09: Gợi ý kèm đường đi đồ thị
Mỗi mục kèm `reason_path` đã sinh ra nó; API `GET /api/recommend?seed=<node>&k=5` → `[{node, label, category, score, reason_path}]`.

#### FR10: Gợi ý xuyên danh mục
**Consequences:** ≥1 trong 5 gợi ý đầu thuộc danh mục khác (khởi động chỉ khi đồ thị nối được — **gate Sprint 2: mọi danh mục ≥8 tài liệu**).

#### FR11: Đa dạng
5 mục đầu ≤3 mục cùng danh mục, trừ khi số danh mục tiếp cận được ít hơn.

#### FR13: Xếp hạng lại theo hồ sơ
Hai người dùng hồ sơ khác nhau nhận thứ tự khác nhau; khác biệt truy nguyên về trọng số hồ sơ.

### 4.6 Tư vấn chủ động (F10)

Phân loại ý định 6 lớp (regex + từ vựng, không fine-tune); sổ đăng ký intent → card_generator; API ngoài (Open-Meteo, Overpass) gọi **song song** với bước sinh (`asyncio.gather`) để ẩn độ trễ; suy giảm tường minh khi API chết.

**Functional Requirements:**

#### FR17: Phân loại ý định
Truy vấn gán 1 trong 6 lớp; gán ghi lại, kiểm tra được; macro-F1 ≥85% trên ≥100 câu gán nhãn tay.

#### FR18: Thẻ khớp sổ đăng ký
**Consequences:** **mọi trường thẻ = đúng trường bản ghi nguồn hoặc phản hồi API, không có trường nào do sinh ra** — assert tự động 100% (NFR06); thẻ mang `provenance` (`corpus|db|graph|external:open-meteo|external:osm`) + `fetched_at` (NFR13).

#### FR19: Lịch sự kiện
Tên, loại lịch, ngày (âm lịch quy đổi **soạn tay**, không thư viện — ràng buộc cứng), địa điểm kèm tọa độ, đơn vị tổ chức, phần lễ + phần hội.

#### FR20: Thời tiết + danh mục chuẩn bị
Dự báo từ Open-Meteo theo tọa độ; checklist sinh bằng **~15 luật tường minh trong `prep_rules.yaml`** trên dự báo, không sinh văn bản. Lễ xa hơn 16 ngày → khí hậu trung bình cùng kỳ (archive-api), **thẻ ghi rõ "khí hậu, không phải dự báo"**.

#### FR21: POI gần địa điểm
Bãi xe (`amenity=parking`), điểm quan sát (`tourism=viewpoint`), cửa hàng nghề/quà; Overpass + cache vào bảng poi; nguồn + thời điểm lấy; **kiểm độ phủ OSM đầu Tuần 8** (Nam Ô, Bảo tàng Chăm) — thưa → fallback POI soạn tay.

#### FR22: Địa điểm & lịch mở cửa
Thẻ kèm tên địa điểm, địa chỉ, giờ mở, giá vé từ bản ghi F03; cổ vật thêm bảo tàng + phòng trưng bày.

### 4.7 Giao diện & đa phương tiện (F11, F12)

Khung chat thẻ, trang Tapestry, dòng thời gian, bản đồ Leaflet, trình 3D + audio 2 ngôn ngữ.

**Functional Requirements:**

#### FR23: Trang chi tiết Tapestry
Ảnh lớn trái, danh sách story phải; kể chuyện, audio, chip liên kết, dòng thời gian, thực thể liên quan, dải nội dung liên quan.

#### FR24: Endpoint truy vết
Vết phơi: hạt giống, hạng từng kênh, độ gần đồ thị, thành phần cho điểm, kết quả từng cổng từ chối.

#### FR28: 3D + audio
.glb từ R2 qua Three.js; xoay, phóng, chuyển story, chuyển ngữ; **mỗi audio có transcript đầy đủ**.

#### FR29: Nguồn gốc tài sản
Bản ghi media_asset lưu khóa kho, người đóng góp, ngày, giấy phép, URL nguồn gốc; thiếu → từ chối tại biên endpoint.

#### FR30: Script audio có bằng chứng
**Mỗi câu khẳng định transcript truy về được câu nguồn** hoặc đánh dấu lời dẫn dắt biên tập; kiểm tra tự động **chặn tổng hợp giọng nói** nếu không đạt.

### 4.8 Quản trị & đánh giá (F04–F06, FR26–FR27)

#### FR26: Dashboard sức khỏe
Số tài liệu/danh mục, thống kê đồ thị, trường thiếu nguồn, hàng chờ rà soát, chỉ số mới nhất.

#### FR27: Toàn bộ bộ đánh giá chạy được
Mọi chỉ số §7 tính và xuất báo cáo ghi: **mô hình, checkpoint bộ điều hợp, phiên bản prompt, phiên bản kho ngữ liệu, cấu hình** (NFR16 — eval model đã đáp ứng trong trường `meta`; các bộ đo mới phải giữ cùng hợp đồng).

## 5. Non-Functional Requirements (NFR01–NFR20)

| Mã | Nhóm | Yêu cầu |
|---|---|---|
| NFR01 | Hiệu năng | p95 đầu-cuối **≤8 giây** (câu hỏi tiêu chuẩn, môi trường demo), đo liên tục từ Sprint 1 |
| NFR02 | Hiệu năng | Gợi ý + thẻ trong **2 giây** (không tính sinh mô hình); API ngoài chạy song song |
| NFR03 | Hiệu năng | Trang chi tiết **≤3 giây** (đệm đồ thị, ảnh thu nhỏ) |
| NFR04 | Độ chính xác | recall@1 **≥95%** kể cả không dấu/tên khác/diễn giải; recall riêng tập diễn giải báo cáo tách |
| NFR05 | Độ tin cậy | Trung thực trích nguồn **≥85%**; độ phủ trích nguồn **≥90%** |
| NFR06 | An toàn | **0 trường bịa trong thẻ tư vấn** — assert tự động |
| NFR07 | Độ tin cậy | Từ chối **≥90%**; trả lời bịa ngoài phạm vi = lỗi; báo cáo cùng NFR04 |
| NFR08 | Giải thích được | Mọi gợi ý phơi đường đi qua tooltip; mọi truy hồi kiểm tra qua endpoint |
| NFR09 | Khả dụng | Lần đầu hỏi + nhận gợi ý **ngay lập tức** — không onboarding, không bảng khai |
| NFR10 | Tiếp cận | WCAG 2.1 AA phần áp dụng được: alt-text, tương phản, bàn phím, transcript cho audio, mô tả 3D |
| NFR11 | Bảo mật | Xác thực mọi endpoint cá nhân; kiểm tra đầu vào; không đường ghi không xác thực; không mở mạng công khai |
| NFR12 | Riêng tư | Đồng ý trước khi ghi; chỉ lưu tối thiểu; xuất + xóa (không thể cắt) |
| NFR13 | Nguồn gốc | Mọi phát biểu truy về nguồn: câu kho ngữ liệu, trường bản ghi, hoặc API có tên + mốc thời gian |
| NFR14 | Toàn vẹn | Bản ghi thiếu nguồn **không lưu được** — ràng buộc mức **DB**, không phải app |
| NFR15 | Bảo trì | Nạp/graph/truy hồi/sinh/gợi ý/tư vấn/UI = mô-đun giao diện tách biệt |
| NFR16 | Tái lập | Model, checkpoint adapter, phiên bản prompt, phiên bản kho, cấu hình ghi trong **mọi report** |
| NFR17 | Mở rộng | Thêm vùng/danh mục/bản ghi **không sửa mã**; thẻ mới chỉ cần đăng ký bộ sinh |
| NFR18 | Khả chuyển | **Một máy, không dịch vụ AI ngoài, không khóa API** |
| NFR19 | Đa phương tiện | .glb tải ≤3 giây trên 4G, ≤30 MB (Draco/Meshopt); audio phát ≤1 giây; không tính thời gian tổng hợp (sinh trước) |
| NFR20 | Ngoại tuyến | Mất R2/Azure → trang chi tiết vẫn đầy đủ văn bản/transcript/chip; 3D+audio hiện "tạm thời không khả dụng", không trang trắng |

## 6. Non-Goals (Explicit)

- **Không** nhận dạng video/OCR quy mô lớn, dịch đa ngữ giao diện, đặt vé/tour, dữ liệu đám đông, giao thông thời gian thực, chứng nhận lịch sử, gợi ý lọc cộng tác, mobile native
- **Không** nhận giọng nói — chỉ gõ văn bản; audio là narration soạn trước
- **Không** số hóa 3D bằng quét thực địa — 3D chỉ từ nguồn mở
- **Không** nhận dạng tự động nội dung ảnh — ảnh quản lý qua metadata
- **Không** mở rộng vùng thứ ba (Nam Bộ) — cơ chế sẵn sàng, dữ liệu thì phải crawl lại + sinh lại eval (vài tuần); ghi tường minh ở báo cáo (Mục 15.4)
- **Không** dùng thư viện âm lịch — quy đổi soạn tay ~20 lễ hội 2026–2027; thư viện lệch múi giờ có thể lệch 1 ngày
- **Không** fine-tune cho phân loại ý định — regex + từ vựng (luật >90% đo được, kiểm toán được)

## 7. Success Metrics

**Primary (đối chiếu Mục 15.3 proposal):**
- **SM-1** recall@1 ≥95% (in-domain, gồm không dấu/tên khác/diễn giải) — validates FR12, NFR04
- **SM-2** Độ trung thực trích nguồn ≥85%, độ phủ ≥90% — validates FR15, NFR05
- **SM-3** Độ chính xác từ chối ≥90% — validates FR14/NFR07
- **SM-4** **0 trường bịa trong thẻ** (assert tự động 100%) — validates FR18, NFR06
- **SM-5** Script audio 100% có bằng chứng — validates FR30
- **SM-6** Gợi ý: precision@5 ≥70% (2 người đánh giá + Cohen's κ), nDCG@5, xuyên miền ≥30% top-5, entropy danh mục — validates FR09–FR11
- **SM-7** Ý định macro-F1 ≥85% trên ≥100 câu nhãn — validates FR17
- **SM-8** p95 ≤8 giây; trang chi tiết ≤3 giây — validates NFR01, NFR03
- **SM-9** NER micro-F1 ≥0.75 kèm per-type — validates FR04
- **SM-10** Ablation tách kênh: từng kênh riêng + tổ hợp, có/không xếp hạng lại đồ thị — **đóng góp học thuật #1: lượng hóa giá trị đồ thị**
- **SM-11** Không-suy-giảm: trích nguồn + từ chối không giảm sau khi lớp tư vấn xuất hiện — validates O11
- **SM-12** SUS trên 6–8 người (thấp hơn chỉ khi cắt theo §8)

**Counter-metrics (không tối ưu):**
- **SM-C1**: Tỷ lệ từ chối — không tối ưu tăng một mình: từ chối mọi câu đạt 100% nhưng phá NFR09/FR07 (refusal-ok bắt buộc phải trả lời). Đo cùng recall trong một bảng.
- **SM-C2**: Tỷ lệ xuyên miền — không đẩy bằng cách gợi ý xa chủ đề: precision@5 là khớp chế chế; bonus chỉ tính khi vẫn liên quan đồ thị.
- **SM-C3**: p95 — không đạt bằng cách giảm MAX_TOKENS xuống mức câu trả lời cụt: độ phủ trích nguồn phải ≥90% song song.

## 8. Roadmap 13 tuần (05/09 → 06/12/2026)

Hai quy tắc: **việc rủi ro cao làm trước**; **không lớp nào xây trên lớp chưa đo**.

| Tuần | Sprint | Nội dung chính | Xong | Gate vào sprint sau |
|---|---|---|---|---|
| 2 | Trả nợ đo lường | Sửa rò rỉ kg.py (Đàn Nam Giao, 1193 ký tự); base chạy lại 76 mẫu; checkpoint vào report (NFR16); sửa số liệu 4 tệp; suite PARAPHRASE + baseline | — | eval exit 0; hai report so sánh được; baseline PARAPHRASE có số |
| 3 | S1 — Nền tảng | Postgres 16 + pgvector + Alembic + docker-compose; 15 bảng (app_user argon2id, user_interest, interaction_event, recommendation_log, venue, event, event_segment, artifact, poi, media_asset, story, passage_embedding vector(1024), audit_log); auth JWT cookie; middleware tương tác có đồng ý; `/api/me/export` + `/api/me/data`; schema v2 `/api/chat` (`{answer, sources, blocks, intent, recommendations}`); Antd; **đo p95 ngay** | O10 (mã) | p95 đầu-cuối có số |
| 4 | S2 — Dữ liệu miền | Crawl ~35 tài liệu (Nghệ thuật +6, Lễ hội +8, Làng nghề +8); 50 venue (Wikidata P625 → Nominatim → kiểm mắt); 20 event + phần lễ/hội; 35 artifact (chammuseum.vn, danh mục Bảo vật quốc gia); dựng lại đồ thị; sinh lại tập vàng; chạy lại eval | **O1, O3** | **Mọi danh mục ≥8 tài liệu — không đạt thì Sprint 4 (cá nhân hóa) không bắt đầu vì FR10 không thể đạt** |
| 5 | S3 — Truy hồi ba kênh | Nhúng mlx-embeddings (không torch); RRF 3 kênh; sửa retriever.py:372 + rag.py:95; hiệu chỉnh θ trên OUT_OF_DOMAIN; **bảng tách kênh**; endpoint truy vết | **O4** | Bảng tách kênh có số; NFR04+NFR07 chốt cùng nhau |
| 6–7 | S4 — Cá nhân hóa | **Việc đầu Tuần 6: chốt danh sách mô hình 3D** (mở → 4, chỉ 2 → biết ngay). Rồi: hồ sơ + suy giảm; recommend.py; /api/recommend + reason_path; recommendation_log; trang hồ sơ; dải liên quan | **O6** | Danh sách 3D chốt; xuyên miền đo được |
| 8–9 | S5 — Tư vấn chủ động | **Việc đầu Tuần 8: kiểm độ phủ OSM** (Nam Ô, Bảo tàng Chăm). Rồi: ý định 6 lớp + 100 câu nhãn; sổ intent→card; Open-Meteo; Overpass + cache; prep_rules.yaml; asyncio.gather; **đo lại trích nguồn + từ chối**. Kèm quản trị (CRUD, audit, dashboard) | **O7, O9** | Không-suy-giảm được đo (giữ 0.7037/0.9167) |
| 10 | S6 — Giao diện + đa phương tiện | Sổ bộ kết xuất thẻ; trang Tapestry; timeline; Leaflet; nén 3D; **kiểm bằng chứng script → chặn tổng hợp**; Edge TTS 2 ngôn ngữ; R2/Azure; Three.js; rà WCAG | **O8** | 2 assert tự động chạy xanh |
| 11 | S7 — Hai hành trình + đệm | Hành trình nghiên cứu (cổ vật → bảo tàng → cùng thời kỳ → làng nghề) + hành trình tham dự (lễ hội → lịch → địa điểm → thời tiết → chuẩn bị → quan sát → gửi xe); **đệm trượt tiến độ** | — | — |
| 12–13 | Kiểm thử & đo | pytest + Playwright + CI; assert NFR06 + FR30; toàn bộ chỉ số §7; precision@5 + κ; SUS 6–8 người; streaming nếu p95 quá | **O11** | Mọi chỉ số có số |
| 14–15 | Kết thúc | Tài liệu kiến trúc/API/lược đồ; rà soát riêng tư + đạo đức; video/slide/hướng dẫn; báo cáo cuối | O10 (rà soát) | — |

**Timeline 15 tuần đầy đủ** (khởi động T1–2: phân tích, SRS, wireframe, phương pháp đánh giá — đã qua; sprint mapping như bảng trên).

**Thứ tự cắt khi trượt (quyết trước — không quyết trong hoảng loạn):**
1. Số mô hình 3D: 4 → 2 → 1 (giữ audio cho story còn lại; chỉ 2 → F12 phủ 2 địa điểm, nêu tường minh Mục 15.4)
2. POI cửa hàng/quà (giữ bãi xe + điểm quan sát)
3. Nghiên cứu người dùng: 8 → 4 người
4. Giao diện quản trị → CLI + trang thống kê chỉ đọc
5. Kho 80 → 65 tài liệu, **giữ nguyên tối thiểu 8/danh mục**
6. Audio chỉ tiếng Việt (Anh → hướng phát triển)

**Không bao giờ cắt:** cổng từ chối, trích nguồn bắt buộc, assert không-bịa-trường (NFR06), assert bằng chứng script (FR30), bộ đánh giá.

## 9. Open Questions

Đã giải quyết 08/09/2026: baseline base↔LoRA trên cùng 76 mẫu, PARAPHRASE
baseline 9/39 và NER LoRA 0.7861. Xem `pipelines/evaluation/baseline-summary.md`.

1. **[BLOCKER cho Sprint 4] Mô hình 3D giấy phép mở** — chốt đầu Tuần 6; nếu chỉ 2 → F12 hẹp lại
2. **[BLOCKER cho Sprint 5] Độ phủ OSM** quanh Nam Ô + Bảo tàng Chăm — kiểm đầu Tuần 8; thưa → POI soạn tay
3. **[BLOCKER cho O11] Người đánh giá thứ hai** — precision@5 + nhãn NER vàng cần 2 người (Cohen's κ); chưa chốt ai
4. **Người tham gia nghiên cứu SUS 6–8** — chưa có danh sách
5. **θ cổng ngữ nghĩa** — chưa có số; hiệu chỉnh Tuần 5, đánh đổi NFR04↔NFR07 phải thành bảng
6. **Giấy phép ảnh tiêu biểu mỗi thực thể** — ảnh 1/entity giữ lại từ v1.0, nguồn cần rà khi nhập F03

## 10. Assumptions Index

- §0: PRD chuyển thể từ proposal-vi v2.0 + upgrade-plan; giữ nguyên mã FR/NFR — *[ASSUMPTION: hội đồng coi PRD này là SRS chính thức thay vì proposal riêng]*
- §4.5: bảng đối chiếu Nam Bộ của upgrade-plan §6 được coi là câu trả lời thỏa cho ghi chú mentor — *[ASSUMPTION: mentor chấp nhận cơ chế độc lập vùng + bảng đối chiếu, không đòi demo thật Nam Bộ]*
- §4.6: audio Edge TTS ngoại tuyến 2 ngôn ngữ — *[ASSUMPTION: Edge TTS đủ chất lượng cho narration; nếu không thì chọn phương án TTS cục bộ khác cũng ngoại tuyến]*
- §4.7: `<model-viewer>` hoặc Three.js cho 3D — *[ASSUMPTION: chọn lúc Tuần 10 theo tài sản thực có]*
- §7: ngưỡng SUS 6–8 người giữ nguyên của proposal — *[ASSUMPTION: quy mô đủ cho capstone, không cần nâng]*
- §8: repo phát triển chính trên Mac (MLX) — *[ASSUMPTION: máy Windows hiện tại chỉ soạn docs, mọi lệnh đo/train chạy trên Mac]*
