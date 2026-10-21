# Addendum — PRD HeritageGraph

*Nội dung thuộc downstream documents (architecture, epics) hoặc earned a place nhưng không fits PRD chính.*

## 1. Chi tiết kỹ thuật trích xuất từ upgrade-plan (nguồn cho architecture + stories)

### 1.1. Schema DB Sprint 1 (Tuần 3) — 15 bảng
`app_user` (argon2id), `user_interest` (source_kind: view|dwell|click|save), `interaction_event`, `recommendation_log` (reason_path), `venue`, `event` (calendar: lunar|solar), `event_segment` (phase: lễ|hội), `artifact`, `poi` (source: osm|manual), `media_asset` (license, contributor, origin_url, uploaded_at), `story`, `passage_embedding` (vector(1024), khóa chunk_id `<tên bài>#<i>` theo retriever.py:233), `audit_log`. Ràng buộc NOT NULL nguồn ở mức DB (NFR14).

### 1.2. Hai chỗ bắt buộc sửa cho kênh vector (Sprint 3)
- `retriever.py:372`: `if not lexical and not named: return empty` → thêm `and not dense` — nếu không, câu diễn giải chết trước khi vector nói gì
- `rag.py:95`: `MIN_COVERAGE` thuần IDF từ vựng → `coverage >= MIN_COVERAGE **hoặc** cosine >= θ`

### 1.3. Công thức gợi ý (recommend.py, Sprint 4)
```
score(d) = α·GraphAffinity(seed,d) + β·ProfileAffinity(interests,d)
         + γ·CrossDomainBonus(seed,d) − δ·Seen(d)   → MMR chống 5 cái lăng liên tiếp
```
Trọng số ngầm định: view +1, dwell>20s +2, click thẻ +2, save +3, dismiss −2, suy giảm nửa chu kỳ 14 ngày. β=0 khi chưa có hồ sơ.

### 1.4. Sổ ý định → thẻ (Sprint 5)
`research` → Artifact/Museum/SamePeriod/RelatedCraft; `attend_event` → Schedule/VenueMap/Weather/PrepChecklist/Viewpoint/Parking; `plan_trip` → VenueMap/Nearby/Food/Weather; `learn` → NarrationBlock+Related; `compare` → ComparisonTable; `verify` → CorrectionBlock. Mở rộng query_intent() (retriever.py:113) từ 4 → 6 lớp.

### 1.5. Mã giữ nguyên (không sửa — upgrade-plan §0.4)
retriever.py (BM25×2 + RRF + graph), kg.py (0.23s, expand_docs, find_seeds), rag.py:89-104 (cổng), prompt.py SYSTEM, corpus.py, nerlabel.py, checkpoint LoRA 0000200 (val loss 0.414).

### 1.6. Mã phải sửa (§0.5)
config.py:44 (0.0.0.0→127.0.0.1), app.py (auth + CORS), api/chat.py:20-22 (schema v2), page.tsx (NEXT_PUBLIC_API_URL — đã sửa Tuần 2 docs), type Source (thêm doc/url/heading/chunk_id), apps/backend/tests/ (rỗng — cần pytest + Playwright + CI).

## 2. Chi tiết nguồn dữ liệu Sprint 2 (Tuần 4) — cho stories nhập liệu

### 2.1. Tên crawl cụ thể (đã có trong upgrade-plan §1.1)
- Nghệ thuật: Ca Huế, Hát bài chòi, Hò khoan, Múa Chăm, Rối cạn, Tuồng Huế
- Làng nghề: Làng đá Non Nước, Đúc đồng Phường Đúc, Nón lá Huế, Hoa giấy Thanh Tiên, Tranh làng Sình, Gốm Thanh Hà, Dệt Zèng A Lưới, Mộc Kim Bồng
- Lễ hội: Điện Huệ Nam, Tế Xã Tắc, Quán Thế Âm, Đình làng Hải Châu, Làng Túy Loan, Đua thuyền Sông Hàn, Vía Bà, Hội đèn lồng
- Ẩm thực: Bánh ép, Chè hẻm Huế, Bún chả cá, Bánh tráng cuốn thịt heo, Ốc hút, Bánh canh Nam Phổ

### 2.2. Nguồn toạ độ/bản ghi
Wikidata P625 (tra qua pageid trong resolve_map.json) → Nominatim (1 req/s, User-Agent bắt buộc, cache) → kiểm mắt 50 điểm. Sự kiện: Cục Di sản (dsvh.gov.vn), cổng TTĐT, Sở Du lịch, báo địa phương. Cổ vật: chammuseum.vn, baotangcovatcungdinh.vn, danh mục Bảo vật quốc gia.

### 2.3. Bảng đối chiếu Nam Bộ (trả lời ghi chú mentor, demo bằng Huế)
Cải lương (điểm vào) ↔ Nhã nhạc/Hát tuồng; đàn ca tài tử ↔ tài liệu cùng danh mục Nghệ thuật; áo bà ba ↔ bản ghi làng nghề (nón lá, dệt Zèng) + cổ vật; Nhà cổ Huỳnh Thủy Lê ↔ di tích cùng phường qua in_ward; điểm diễn ↔ venue + event có phần hội.

## 3. 20 rủi ro chính (từ proposal Mục 14) — cho risk register epics

Phạm vi vượt 15 tuần (Cao — thứ tự cắt cố định trước, Sprint 7 đệm) • Cân bằng danh mục (Cao — gate Sprint 2) • Bản ghi thủ công (Cao — giới hạn số lượng, 1 sprint riêng) • Thẻ hồi sinh bịa (Cao — kết xuất từ bản ghi, assert) • Gợi ý khó đo (Cao — 2 người + κ) • Kênh vector yếu tên riêng hiếm (TB — 3 kênh + trace) • POI thưa (TB — kiểm Tuần 8) • API chết lúc demo (TB — đệm + suy giảm tường minh là test case) • Âm lịch lệch (TB — bảng tay) • p95 vượt (Cao — đo từ Sprint 1, song song API, streaming dự phòng) • Dữ liệu cá nhân thành nghĩa vụ (Cao — đồng ý trước, xuất/xóa Sprint 1) • Endpoint không xác thực (Cao — Sprint 1) • Trích tên sai (Cao — vựng đóng, chuỗi con nguyên văn) • Tên hành chính trùng (TB — alias + test riêng) • Quan hệ thiếu bằng chứng (Cao — chỉ quan hệ cấu trúc) • Nội dung nhạy cảm (Cao — nguồn mọi trường + cố vấn) • Nhầm thành nguồn sử liệu (TB — provenance hiển thị) • LTV ốm (Cao — Sprint 7 đệm) • θ kéo tụt từ chối (mới — báo cáo NFR04+NFR07 cùng bảng) • Baseline PARAPHRASE cao bất ngờ (mới — ghi là kết quả + tiết kiệm sprint).

## 4. Ví dụ minh họa user journey chi tiết (Mục 12.5 proposal)
Hai hành trình demo cố tình chọn **cổ vật** và **lễ hội** (không phải di tích) — "văn hóa thì nhiều thứ, không chỉ diễn xướng". Hành trình nghiên cứu: cổ vật → bảo tàng → cổ vật cùng thời kỳ → làng nghề. Hành trình tham dự: lễ hội → lịch → địa điểm → thời tiết → chuẩn bị → điểm quan sát → chỗ gửi xe.
