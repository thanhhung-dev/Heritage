# Kế hoạch hoàn thiện dự án theo `proposal-vi.md`

Tài liệu này trả lời đúng ba câu hỏi: **thiếu gì**, **phải viết mã nào**, **làm theo thứ tự nào**. Nguồn chuẩn duy nhất cho phạm vi là `docs/proposal-vi.md` (11 mục tiêu O1–O11, 14 tính năng F01–F14, 30 yêu cầu chức năng FR01–FR30, 20 yêu cầu phi chức năng NFR01–NFR20).

Đọc kèm: `docs/architecture.md` (kiến trúc as-built — **đang lạc hậu, xem §0.3**), `docs/metrics.md` (định nghĩa chỉ số đã đo).

---

## §0. Hiện trạng đã đo

### 0.1. Số liệu đo trực tiếp

Đo bằng `load_docs()` + `build_graph()` ngày 05/09/2026, không phải số trong README:

```
45 tài liệu dùng được / 349 đoạn / 304.224 ký tự   (47 tệp corpus, bỏ 2)
Bỏ: 'Bánh xèo' (trùng nội dung 'Bánh khoái'), 'Đàn Nam Giao' (205 ký tự, trang định hướng)
Vùng:      Huế 30, Đà Nẵng 15
Danh mục:  Di tích lịch sử 22, Ẩm thực 9, Danh thắng 6, Nghệ thuật 4, Lễ hội 2, Làng nghề 2
Đồ thị:    510 đỉnh / 1135 cạnh / 1 thành phần liên thông / 0 tài liệu cô lập
           entity 235, year 222, doc 45, category 6, region 2
           mentions 242, year 443, related 123, in_ward 98, in_region 92, in_category 92, is_about 45
Truy hồi:  trong phạm vi 68/70, paraphrase 9/39, bằng chứng 34/34, phường/xã 18/20
           ngoài phạm vi 31/38
Sinh văn bản: citation_faithful 0.7037, refusal_accuracy 0.9167 (pipelines/evaluation/report_lora.json, 76 mẫu)
```

### 0.2. Việc phải làm trước khi code bất cứ thứ gì

**Đã hoàn thành 08/09/2026:** retrieval được chạy lại trên toàn bộ suite; kết quả hiện tại là trong phạm vi 68/70, paraphrase 9/39, bằng chứng 34/34, phường/xã 18/20 và ngoài phạm vi 31/38.

**Baseline đã được chốt.** `report_base.json` và `report_lora.json` cùng đo 76 mẫu / corpus 45 bài bằng cùng prompt và greedy decoding. NER micro-F1 0.1043 → 0.7861; citation faithful 0.0370 → 0.7037; coverage 0.0370 → 0.7407; refusal 0.3750 → 0.9167.

**NFR16 đã được đáp ứng cho eval model.** Mỗi report ghi model, checkpoint, cấu hình sinh và SHA-256 của adapter, gold, prompt, corpus, scorer trong trường `meta`. Xem `pipelines/evaluation/baseline-summary.md`.

### 0.3. Tài liệu đang mô tả sai hiện trạng

| Tệp | Ghi gì | Thực tế |
| --- | --- | --- |
| `architecture.md:36,95-115,300-321` | PostgreSQL 16 + pgvector, 15 bảng, `embedding vector(1024)`, docker-compose | **Không tồn tại**. Không tệp `.sql`, không `docker-compose*`, không driver DB trong venv |
| `architecture.md:55,67-68` | 23 tài liệu / 215 đoạn / 331 đỉnh / 563 cạnh | 45 / 349 / 510 / 1135 |
| `README.md` | 23 tài liệu / 215 đoạn | Như trên |
| `apps/frontend/app/page.tsx:48` | "Qwen2.5-7B" | Qwen2.5-**3B**-Instruct-4bit |
| `demo-guide.md:19` | recall@1 22/22 | 30/30 |

Cả `architecture.md` và `README.md` đều tự tuyên bố là "số liệu đo được", nên sai số này là lỗi đáng bị hỏi. Sửa trong Tuần 2.

### 0.4. Mã hiện có — giữ nguyên, không sửa

Đây là phần đã đo được và là đóng góp của dự án:

| Thành phần | Vì sao giữ |
| --- | --- |
| `apps/backend/core/retriever.py` — BM25 từ + BM25 n-gram + RRF + xếp hạng lại bằng đồ thị | recall@1 30/30 kể cả câu không dấu và tên gọi khác |
| `apps/backend/core/kg.py` — dựng đồ thị tất định, `expand_docs()`, `find_seeds()` | 0,23 giây; `expand_docs()` chính là hàm bộ gợi ý sẽ dùng lại |
| `apps/backend/core/rag.py:89-104` — các cổng từ chối | `refusal_accuracy 0.9167`. **Không bao giờ cắt** |
| `apps/backend/core/prompt.py` — SYSTEM | Nguồn duy nhất của văn phong + định dạng trích nguồn, dùng chung train/serve/eval |
| `apps/backend/core/corpus.py` — tách đoạn | Nguồn duy nhất, dùng chung train và serve |
| `apps/backend/core/nerlabel.py` | Có bộ chặn tên ghép, dòng họ, assertion lúc import |
| `models/lora-serve/` checkpoint `0000200` | Đã chọn theo val loss 0.414 thay vì 0.473 ở bước 720 |

### 0.5. Mã hiện có — phải sửa

| Chỗ | Vấn đề | Yêu cầu liên quan |
| --- | --- | --- |
| `apps/backend/core/config.py:44` | `BACKEND_HOST = "0.0.0.0"` mở giao diện mạng công khai | NFR11 |
| `apps/backend/app.py` | `/api/chat` không xác thực, CORS mở | NFR11 |
| `apps/backend/core/rag.py:95` | Cổng `MIN_COVERAGE` chỉ đo từ vựng → sẽ triệt tiêu kênh vector | Mục 12.3 Bước 7 |
| `apps/backend/core/retriever.py:372` | `if not lexical and not named: return empty` → câu diễn giải lại chết trước khi kênh vector nói gì | NFR04 |
| `apps/backend/api/chat.py:20-22` | `ChatResponse` chỉ có `{answer, sources}` | FR18, FR09 |
| `apps/frontend/app/page.tsx:24` | Hardcode `http://localhost:8000` thay vì `NEXT_PUBLIC_API_URL` | — |
| `apps/frontend/app/page.tsx` type `Source` | Khai `{text, score?, entity?}` nhưng backend trả thêm `doc`, `url`, `heading`, `chunk_id` → `url` bị bỏ im lặng, tức trích nguồn không hiển thị được nguồn | FR15 |
| `apps/backend/tests/` | Rỗng. Không có framework kiểm thử, không CI | FR27, NFR06 |

### 0.6. Đối chiếu mục tiêu — đã xong bao nhiêu

| Mục tiêu | Nội dung | Trạng thái | Còn thiếu |
| --- | --- | --- | --- |
| O1 | Kho ngữ liệu ≥80 tài liệu, ≥8 mỗi danh mục | **Một phần** — 45 tài liệu, 3 danh mục dưới ngưỡng | +35 tài liệu (§1.1) |
| O2 | Đồ thị tri thức có nguồn gốc | **Xong** — 510 đỉnh, 1135 cạnh, mọi đỉnh có nguồn | Thêm đỉnh sự kiện/địa điểm/cổ vật sau khi có bản ghi |
| O3 | Bản ghi có cấu trúc kèm nguồn | **Chưa có gì** | 50 địa điểm, 20 sự kiện, 35 cổ vật (§1.2–1.4) |
| O4 | Truy hồi ba kênh + đồ thị | **Hai phần ba** — thiếu kênh vector | pgvector + nhúng + hiệu chỉnh cổng (§2.4) |
| O5 | Trả lời có căn cứ | **Xong** — 0.7037 trích nguồn, 0.9167 từ chối | Sửa rò rỉ §0.2 |
| O6 | Cá nhân hóa | **Chưa có gì** | Toàn bộ lớp: DB, hồ sơ, bộ gợi ý (§2.2, §2.5) |
| O7 | Tư vấn chủ động | **Chưa có gì** | Ý định 6 lớp, sổ đăng ký thẻ, API ngoài (§2.6, §2.7) |
| O8 | Giao diện thẻ + đa phương tiện | **Gần như chưa** — 1 trang 88 dòng | Toàn bộ (§2.9, §2.10) |
| O9 | Biên tập và quản trị | **Chưa có gì** | CRUD, kiểm tra nguồn, sổ kiểm toán (§2.8) |
| O10 | Riêng tư | **Chưa có gì** | Đồng ý, xuất, xóa (§2.3) |
| O11 | Đánh giá | **Một phần** — 6 suite truy hồi + 4 chỉ số sinh | Diễn giải lại, tách kênh, ý định, gợi ý, thẻ, độ trễ (§4) |

Hai mục đã xong (O2, O5) là hai mục làm nên đóng góp học thuật. Chín mục còn lại là công việc của 13 tuần tới.

---

## §1. Dữ liệu đang thiếu

Mỗi mục ghi rõ: hiện có gì, cần gì, **lấy ở đâu bên ngoài**, và mục tiêu nào chết nếu không có.

### 1.1. Thiếu #1 — Cân bằng danh mục kho ngữ liệu

**Chặn:** O1, O6. **Hiện có:** Nghệ thuật 4, Lễ hội 2, Làng nghề 2 tài liệu.

O1 đòi ≥8 tài liệu mỗi danh mục, tổng ~80. Ba danh mục đang dưới ngưỡng, và đây là **chặn nghiêm trọng nhất** cho O6: FR10 đòi ≥1 trong 5 gợi ý đầu thuộc danh mục khác, nhưng với 4 tài liệu Nghệ thuật và 2 Làng nghề, bộ gợi ý chỉ có thể quay vòng trong Di tích (22 tài liệu). Cạnh `related` chỉ nối được thứ đã có mặt trong đồ thị. Đây là chặn **dữ liệu**, không phải chặn thuật toán.

**Cần:** thêm ~35 tài liệu — Nghệ thuật +6, Lễ hội +8, Làng nghề +8, còn lại rải đều.

| Nguồn | Nội dung | Cách lấy |
| --- | --- | --- |
| vi.wikipedia.org | Nghệ thuật, làng nghề, lễ hội, món ăn | `pipelines/ingestion/crawl_wiki.py` đã chạy 47/47 thành công, chỉ cần thêm tên vào danh sách địa điểm |
| Cục Di sản văn hóa (dsvh.gov.vn) | Danh mục di sản phi vật thể quốc gia | Bộ lọc theo tỉnh → tên chính xác của lễ hội và nghề |
| Cổng TTĐT TP Huế / TP Đà Nẵng | Danh mục lễ hội, làng nghề được công nhận | Trang danh mục → lấy tên → tra Wikipedia; không có bài thì soạn tay kèm nguồn |
| Trung tâm Bảo tồn Di tích Cố đô Huế | Nhã nhạc, tuồng, lễ hội cung đình | Trang giới thiệu từng di tích |
| UNESCO ich.unesco.org | Nhã nhạc (2003), hồ sơ di sản phi vật thể | Hồ sơ trích dẫn được |

**Tên cụ thể để crawl** (kiểm tra tồn tại bài trước):

- Nghệ thuật: Ca Huế, Hát bài chòi, Hò khoan, Múa Chăm, Rối cạn, Tuồng Huế
- Làng nghề: Làng đá Non Nước, Đúc đồng Phường Đúc, Nón lá Huế, Hoa giấy Thanh Tiên, Tranh làng Sình, Gốm Thanh Hà, Dệt Zèng A Lưới, Mộc Kim Bồng
- Lễ hội: Lễ hội Điện Huệ Nam, Lễ tế Xã Tắc, Lễ hội Quán Thế Âm, Lễ hội Đình làng Hải Châu, Lễ hội Làng Túy Loan, Đua thuyền Sông Hàn, Lễ hội Vía Bà, Hội đèn lồng
- Ẩm thực: Bánh ép, Chè hẻm Huế, Bún chả cá, Bánh tráng cuốn thịt heo, Ốc hút, Bánh canh Nam Phổ

**Điểm quan trọng:** thêm tài liệu **không cần train lại mô hình**. LoRA dạy văn phong, định dạng trích nguồn, hành vi từ chối và NER — không dạy dữ kiện. Dữ kiện đến từ truy hồi. Nên mở rộng kho ngữ liệu là ~1 ngày crawl và rà soát, không phải 2,5 giờ train.

### 1.2. Thiếu #2 — Toạ độ địa lý

**Chặn:** O3, O7 (toàn bộ), FR19, FR20, FR21, FR22. **Hiện có:** không có `lat`/`lon` ở bất kỳ đâu trong repo — đã kiểm `corpus/locations_index.json` và `corpus/resolve_map.json`.

Thẻ thời tiết, thẻ bãi xe, thẻ điểm quan sát, khung bản đồ — cả bốn đều cần một cặp toạ độ. Không có toạ độ thì O7 không tồn tại được, kể cả khi mã đã viết xong.

**Cần:** ≥50 bản ghi `venue` với `lat`, `lon`, `ward`, `district`, kèm nguồn.

| Nguồn | Dùng cho | Ghi chú |
| --- | --- | --- |
| Wikidata P625 | Toạ độ cho di tích có bài Wikipedia | Chính xác nhất. Đã có `pageid` trong `resolve_map.json` → tra được QID |
| Nominatim [14] | Mã hoá địa lý tên di tích → toạ độ | Miễn phí, không khoá. Giới hạn 1 req/s → chạy 1 lần rồi cache. Bắt buộc gửi User-Agent |
| Infobox Wikipedia | Nhiều bài di tích Huế có sẵn toạ độ | Đang bị `clean_wiki_text()` bỏ đi; parse riêng được |
| Google Maps (xem thủ công) | Kiểm chéo 50 điểm | ~1 giờ. Chỉ đọc toạ độ, không dùng API |

**Thứ tự:** Wikidata trước (chính xác nhất, có `pageid` sẵn) → Nominatim cho phần thiếu → mắt người kiểm 50 điểm trên bản đồ. Ghi nguồn toạ độ vào trường `source_url` của từng bản ghi.

### 1.3. Thiếu #3 — Bản ghi sự kiện có cấu trúc

**Chặn:** O3, FR19. **Hiện có:** danh mục Lễ hội đúng 2 tài liệu, toàn văn xuôi. Không bảng ngày, không lịch âm, không đơn vị tổ chức, không phần lễ/phần hội.

FR19 đòi trả về chính xác: tên, loại lịch và ngày, địa điểm kèm toạ độ, đơn vị tổ chức, và các phần lễ và hội. **Không một trường nào trong số đó tồn tại dưới dạng dữ liệu hiện nay.**

**Cần:** ≥20 bản ghi `event` + `event_segment`, mỗi trường kèm `source_url` + `source_sentence`.

| Nguồn | Trường lấy được |
| --- | --- |
| Cục Di sản văn hóa — danh mục di sản phi vật thể quốc gia | Tên chính thức, địa phương, năm công nhận, mô tả nghi lễ |
| Cổng TTĐT TP Đà Nẵng / TP Huế, mục Văn hoá – Lễ hội | Thời gian âm lịch, đơn vị tổ chức, địa điểm |
| Sở Du lịch Đà Nẵng / Huế — lịch sự kiện năm | Ngày dương lịch cụ thể của năm, ban tổ chức |
| Trung tâm Bảo tồn Di tích Cố đô Huế | Lễ hội cung đình, chi tiết nghi thức |
| Báo Đà Nẵng, Báo Thừa Thiên Huế | Phần lễ / phần hội, hoạt động cụ thể |
| UBND phường/xã | Lễ hội cấp làng như Cầu ngư Nam Ô, Túy Loan |

**Cảnh báo về lịch âm** (đã ghi thành ràng buộc ở proposal Mục 8.1): đừng dùng thư viện. `lunardate` và tương tự theo lịch Trung Quốc, lệch múi giờ UTC+7/+8 nên đôi khi lệch 1 ngày — đúng loại lỗi hội đồng sẽ chỉ ra. Soạn tay bảng quy đổi cho ~20 lễ hội trong 2026–2027 (30 phút, đúng 100%), ghi thư viện vào hướng phát triển tương lai.

### 1.4. Thiếu #4 — Bản ghi cổ vật

**Chặn:** O3, FR22, và Tình huống A ở Mục 12.5. **Hiện có:** chữ "cổ vật" xuất hiện trong đúng 3 tệp — `Bảo tàng Cổ vật Cung đình Huế.txt` (14 lần), `Bảo tàng Điêu khắc Chăm Đà Nẵng.txt` (4 lần), `Chùa Thiên Mụ.txt` (1 lần). Toàn văn xuôi, không mã hiện vật, không niên đại, không chất liệu, không phòng trưng bày.

**Cần:** ≥35 bản ghi `artifact` với `name`, `museum`, `period`, `material`, `room`, `source_url`, `source_sentence`.

| Nguồn | Nội dung |
| --- | --- |
| chammuseum.vn | Danh sách bảo vật quốc gia, tên hiện vật, niên đại, chất liệu, phòng trưng bày. Nguồn tốt nhất cho phần Chăm |
| baotangcovatcungdinh.vn / hueworldheritage.org.vn | Hiện vật cung đình Huế: ngai vàng, kim phẩm, đồ sứ ký kiểu |
| Danh mục Bảo vật quốc gia (quyết định Thủ tướng, đăng trên Cục Di sản) | Danh sách chính thức + mô tả. Nguồn trích dẫn mạnh nhất cho báo cáo |
| Wikipedia "Bảo vật quốc gia (Việt Nam)" | Bảng tổng hợp để đối chiếu |
| Nhãn hiện vật chụp tại bảo tàng | Chính xác nhất cho `room`; đồng thời có ảnh dùng được |

Lưu ý thay đổi so với bản kế hoạch trước: proposal đã **bỏ sơ đồ bảo tàng có điểm nóng** khỏi phạm vi (Mục 7.1, bảng tính năng bị bỏ), nên `artifact` không còn cần `floorplan_x/y`. Vị trí cổ vật được nêu bằng tên bảo tàng và phòng trưng bày, hiển thị qua FR22. Đây là ~0,5 ngày công được tiết kiệm.

### 1.5. Thiếu #5 — Điểm quan tâm

**Chặn:** FR21. **Hiện có:** không có gì.

| Nguồn | Truy vấn |
| --- | --- |
| Overpass API [13] | `amenity=parking`, `tourism=viewpoint`, `shop=gift`, `shop=souvenir` trong bán kính quanh toạ độ địa điểm |
| Soạn tay khi OSM thiếu | Rất có thể phải làm — xem cảnh báo |

**Cảnh báo:** độ phủ OSM ở Việt Nam không đều — đã ghi thành ràng buộc ở proposal Mục 8.1. **Việc đầu tiên của Tuần 8 là kiểm tra thật** độ phủ `amenity=parking` quanh Nam Ô và Bảo tàng Chăm. Nếu thưa thì fallback bản ghi `poi` soạn tay kèm nguồn — đừng phát hiện điều này ở Tuần 10.

### 1.6. Thiếu #6 — Thời tiết

**Chặn:** FR20. **Hiện có:** không có.

Open-Meteo [12] `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&hourly=precipitation_probability,temperature_2m`. Miễn phí, **không cần khoá**, có `precipitation_probability` theo giờ. Dự báo chỉ tới ~16 ngày, nên lễ hội xa hơn thì dùng `archive-api.open-meteo.com` lấy khí hậu trung bình cùng kỳ các năm trước và **ghi rõ trên thẻ đó là số liệu khí hậu, không phải dự báo** (đã ghi ở Mục 15.4).

Luật "mang gì" viết thành ~15 luật trong YAML, không dùng mô hình: `precip>40% → áo mưa`; `temp>33 → nước, nón`; `có phần lễ → trang phục lịch sự`; `đua thuyền → chọn chỗ cao`; `lễ hội đêm → đèn pin, đi sớm`. FR20 đòi đúng điều này: "sinh bằng luật tường minh trên dự báo, không bằng sinh văn bản".

### 1.7. Thiếu #7 — Người dùng, hồ sơ sở thích, lịch sử tương tác

**Chặn:** O6, O10, FR01, FR07, FR08, FR25. **Hiện có:** **không có cơ sở dữ liệu nào.** Không Postgres, không SQLite, không vector DB. Không model user, không login, không session. Toàn bộ trạng thái là tệp trên đĩa + một `@lru_cache` (`apps/backend/core/retriever.py:449`).

**Kèm theo là lỗ bảo mật.** `apps/backend/core/config.py:44` bind `0.0.0.0:8000`, `/api/chat` hoàn toàn không xác thực. Hiện tại vô hại vì chưa có dữ liệu cá nhân. Khi bắt đầu lưu hành vi người dùng thì thành vấn đề thật, và NFR11 đòi "không có đường ghi nào không xác thực". **Xác thực phải xong TRƯỚC khi lưu dữ liệu cá nhân đầu tiên**, không phải sau.

### 1.8. Thiếu #8 — Tài sản đa phương tiện

**Chặn:** O8, F12, FR28, FR29, FR30. **Hiện có:** không có gì. Không mô hình 3D, không audio, không bảng tài sản, không tài khoản R2 hay Azure.

**Cần:** 2–4 mô hình `.glb` đã nén dưới 30 MB (NFR19), và audio narration hai ngôn ngữ cho các story tương ứng.

| Nguồn | Nội dung | Ghi chú |
| --- | --- | --- |
| Sketchfab, bộ lọc giấy phép CC | Mô hình di sản Việt Nam | Phải kiểm giấy phép cho phép ghi công và dùng phi thương mại |
| Open Heritage 3D, CyArk | Dữ liệu quét di sản | Độ phủ Việt Nam mỏng, kiểm trước |
| Poly Haven, các dự án số hóa đại học | Mô hình kiến trúc dùng lại được | — |
| Tự dựng từ ảnh (photogrammetry) | Khi không tìm được nguồn | **Ngoài phạm vi** theo Mục 6.4 — không làm |

**Cảnh báo về nguồn cung** (đã ghi thành ràng buộc ở Mục 8.1): mô hình 3D di sản Việt Nam dưới giấy phép mở là rất ít. **Việc đầu tiên của Tuần 6 là tìm thật và chốt danh sách** — nếu chỉ tìm được 2 mô hình thì F12 phủ 2 địa điểm, và điều đó được nêu tường minh ở Mục 15.4 thay vì để hội đồng phát hiện. Mục 8.2 đã ghi giả định này: địa điểm không có mô hình vẫn hiển thị đầy đủ mà không có phần 3D.

**Audio:** Edge TTS [25] chạy ngoại tuyến, không khoá, có giọng tiếng Việt. Sinh trước khi soạn nội dung chứ không sinh lúc chạy (Mục 10, "Audio sinh trước") — nên độ trễ tổng hợp không nằm trong ngân sách NFR19.

### 1.9. Bảng tổng hợp

| # | Thiếu | Chặn | Nguồn ngoài | Công |
| --- | --- | --- | --- | --- |
| 1 | ~35 tài liệu cân bằng danh mục | O1, O6 | Wikipedia, Cục Di sản, cổng TTĐT | 1 ngày |
| 2 | ≥50 toạ độ địa điểm | O3, O7 | Wikidata P625, Nominatim, kiểm mắt | 0,5 ngày |
| 3 | ≥20 bản ghi sự kiện + phần lễ/hội | O3, FR19 | Cục Di sản, Sở Du lịch, báo địa phương | 1,5 ngày |
| 4 | ≥35 bản ghi cổ vật | O3, FR22 | chammuseum.vn, danh mục Bảo vật quốc gia | 1 ngày |
| 5 | Bãi xe / điểm quan sát / cửa hàng | FR21 | Overpass OSM + soạn tay khi thiếu | 0,5 ngày |
| 6 | Thời tiết | FR20 | Open-Meteo (không khoá) | Chỉ mã |
| 7 | Người dùng + hồ sơ + lịch sử | O6, O10 | Không cần nguồn ngoài — cần Postgres | Xem §2.2 |
| 8 | 2–4 mô hình 3D + audio hai ngôn ngữ | O8, F12 | Sketchfab CC, Open Heritage 3D, Edge TTS | 1,5 ngày |

Tổng nhập liệu: khoảng 7,5 ngày. Đó là lý do Tuần 4 được dành trọn cho dữ liệu — nếu coi đây là việc làm kèm thì nó sẽ trượt và kéo theo cả bốn lớp phía trên.

**Quy tắc không nhượng bộ (NFR14):** mọi trường sự kiện của mọi bản ghi bắt buộc có `source_url` + `source_sentence`, áp ở mức ràng buộc cơ sở dữ liệu chứ không ở tầng ứng dụng. Bản ghi thiếu nguồn bị từ chối ở mức trường. Bỏ quy tắc này là mất chính cái kỷ luật trích nguồn đang là xương sống của dự án — và mất luôn khả năng nói "0 trường bịa" trước hội đồng.

---

## §2. Thay đổi mã nguồn

### 2.1. Nguyên tắc chi phối

Trước mọi chi tiết kỹ thuật, hai nguyên tắc của proposal Mục 4.6 quyết định toàn bộ thiết kế phần dưới:

> **Mô hình ngôn ngữ chỉ viết phần kể chuyện di sản. Mọi phát biểu thực tế hoặc có cấu trúc được kết xuất từ một bản ghi có kiểu mang theo nguồn gốc của chính nó, và không bao giờ đi qua bước sinh văn bản.**

> **Audio narration chỉ phát phần kể chuyện. Mọi phát biểu thực tế trong script phải truy về được một câu nguồn trong kho ngữ liệu, kiểm tra tự động trước khi tổng hợp giọng nói.**

Lý do không phải khẩu hiệu. Thành tựu duy nhất bảo vệ được của dự án hiện nay là `refusal_accuracy 0.9167` và `citation_faithful_rate 0.7037`. Nếu để mô hình 3B tự nói về thời tiết và bãi xe, bạn tái tạo hiện tượng bịa đặt đúng ở chỗ vừa diệt xong, và mất luôn luận điểm chính. Nguyên tắc này cũng nhất quán với `apps/backend/core/kg.py:1-21` (không dùng mô hình lúc dựng đồ thị vì mô hình bịa thực thể) — sự nhất quán đó là điểm cộng khi bảo vệ.

### 2.2. Thêm mới — Cơ sở dữ liệu (Tuần 3)

PostgreSQL 16 + pgvector + SQLAlchemy + Alembic + `infra/docker-compose.yml`, đúng như Mục 10 đã chốt.

```
app_user(id, email, password_hash /* argon2id */, created_at, consent_at)
user_interest(user_id, node_id, weight, source_kind /* view|dwell|click|save */, updated_at)
interaction_event(id, user_id, kind /* view|dwell|click|save|dismiss */,
                  target_node_id, dwell_ms, ts)
recommendation_log(id, user_id, seed_node, item_node, reason_path,
                   rank, shown_at, clicked_at)

venue(id, doc_node, lat, lon, ward, district, address, opening_hours, ticket_price,
      source_url, source_sentence)
event(id, name, doc_node, calendar /* lunar|solar */, start_date, end_date,
      organizer, venue_id, source_url, source_sentence)
event_segment(id, event_id, phase /* lễ|hội */, name, description, ord,
              source_url, source_sentence)
artifact(id, name, museum_doc, period, material, room,
         source_url, source_sentence)
poi(id, kind /* parking|viewpoint|shop|food */, name, lat, lon,
    venue_id, source /* osm|manual */, fetched_at)

media_asset(id, kind /* model3d|audio */, object_key, story_id, language,
            transcript, license, contributor, origin_url, uploaded_at)
story(id, doc_node, title, ord, narrative, source_url)

passage_embedding(chunk_id, embedding vector(1024))

audit_log(id, user_id, action, target, before, after, ts)
```

Hai ràng buộc mức cơ sở dữ liệu, không dựa vào tầng ứng dụng để nhớ:

- `venue`, `event`, `event_segment`, `artifact`: `NOT NULL` trên `source_url` và `source_sentence` (NFR14)
- `media_asset`: `NOT NULL` trên `license`, `contributor`, `origin_url`, `uploaded_at` (FR29)

`passage_embedding` khoá theo `chunk_id` của `retriever.py:233` (`<tên bài>#<i>`) để chỉ mục vector không bao giờ lệch khỏi kho ngữ liệu đang chạy.

### 2.3. Thêm mới — Xác thực và riêng tư (Tuần 3, TRƯỚC dữ liệu cá nhân)

- `apps/backend/api/auth.py`: `POST /api/auth/register`, `/login`, `/logout`, `GET /api/auth/me`
- argon2id [19] qua `argon2-cffi`; JWT trong cookie HttpOnly, SameSite=Lax
- Dependency `current_user` cho mọi endpoint đọc hoặc ghi dữ liệu cá nhân
- Sửa `apps/backend/core/config.py:44`: `0.0.0.0` → `127.0.0.1` cho cấu hình demo (NFR11)
- `POST /api/me/export` và `DELETE /api/me/data` (FR25) — **làm luôn Tuần 3**, đừng để Tuần 14
- Màn hình đồng ý trước khi ghi `interaction_event` đầu tiên (NFR12)

FR25 và NFR12 là nghĩa vụ về riêng tư, không phải tính năng — nên chúng nằm ở Tuần 3 cùng với thứ tạo ra nghĩa vụ đó, không nằm ở cuối.

### 2.4. Thêm mới — Kênh truy hồi ngữ nghĩa (Tuần 5)

Đây là phần còn thiếu của O4, và là chỗ dễ làm sai nhất trong toàn bộ kế hoạch.

**Bước 1 — Có bằng chứng trước khi viết mã.** `pipelines/evaluation/eval_retrieval.py` hiện có 6 suite (`IN_DOMAIN`, `OUT_OF_DOMAIN`, `EVIDENCE`, `SUBJECT`, `SCOPE`, `WARD`) và **không có suite diễn giải lại**. Nhưng NFR04 đòi recall@1 ≥95% "kể cả truy vấn diễn giải lại". Nghĩa là yêu cầu khó nhất của NFR04 chưa từng được kiểm chứng.

Thêm suite `PARAPHRASE`: câu hỏi không chia sẻ từ khoá nào với kho ngữ liệu — `"vua Khải Định được chôn ở chỗ nào"` thay vì `"lăng Khải Định ở đâu"`; `"món mì nào của Hội An"` thay vì `"Cao lầu"`. Chạy offline, không cần mô hình, ~1 giờ. **Đo baseline hai kênh trên suite này trước.** Con số đó là thứ biện minh cho toàn bộ Sprint 3 — và nếu nó cao bất ngờ thì bạn đã tiết kiệm được một sprint.

**Bước 2 — Nhúng.** Môi trường hiện tại là `mlx` / `mlx-lm`, **không có torch**. `sentence-transformers` sẽ kéo torch (~2,5 GB). Cân nhắc `mlx-embeddings` để giữ nhất quán với stack MLX. Model tiếng Việt (`bge-m3`, `multilingual-e5`, các model Việt chuyên biệt) thì **đo trên suite `PARAPHRASE` của chính bạn rồi chọn**, đừng chọn theo bảng xếp hạng chung.

**Bước 3 — Hợp nhất.** Điểm cộng của thiết kế hiện tại: `_rrf()` (`retriever.py:214-220`) hợp nhất theo **thứ hạng** chứ không theo độ lớn điểm, nên không cần chuẩn hoá gì. Thêm kênh thứ ba đúng nghĩa là thêm một `dict[int, float]` vào `_rrf(...)` ở `retriever.py:362`.

**Bước 4 — Hai chỗ phải sửa, nếu không kênh vector vô dụng.** Đây là điểm quan trọng nhất của mục này:

| Chỗ | Vấn đề | Sửa thành |
| --- | --- | --- |
| `retriever.py:372` | `if not lexical and not named: return empty` — câu diễn giải lại thuần chết trước khi kênh vector nói gì | Thêm điều kiện `and not dense` |
| `rag.py:95` | `if best_coverage < MIN_COVERAGE: return ("", [])`. `_coverage()` (`retriever.py:259-270`) thuần IDF từ vựng, nên đoạn tìm được vì *giống nghĩa khác từ* bị loại | `coverage >= MIN_COVERAGE **hoặc** cosine >= θ` |

**Bước 5 — Hiệu chỉnh θ, và báo cáo đánh đổi.** Cosine không bao giờ tiến về 0, kể cả với đoạn không liên quan. Nên θ thấp sẽ nhận cả câu ngoài phạm vi và **kéo tụt NFR07** (từ chối ≥90%). Hiệu chỉnh θ trên suite `OUT_OF_DOMAIN` trước khi chốt, và báo cáo NFR04 cùng NFR07 trong một bảng để đánh đổi hiện ra thành số. Proposal Mục 12.3 Bước 7 đã ghi rõ yêu cầu này.

**Bước 6 — Bảng đo tách kênh (FR12).** Đo từng kênh riêng và các tổ hợp, có và không có xếp hạng lại bằng đồ thị. Đây là đóng góp học thuật thứ nhất ở Mục 15.1 — nó lượng hoá phần đóng góp của cấu trúc đồ thị thay vì giả định.

Để kênh vector sau một cờ cấu hình để bật/tắt được: bạn cần bảng trước–sau, không phải một trạng thái.

### 2.5. Thêm mới — Bộ gợi ý (Tuần 6–7)

`apps/backend/core/recommend.py`. Đây là đóng góp học thuật thứ hai.

```python
score(d) = α · GraphAffinity(seed, d)          # expand_docs() — đã có sẵn
         + β · ProfileAffinity(interests, d)   # cùng hàm, hạt giống = hồ sơ
         + γ · CrossDomainBonus(seed, d)       # +thưởng nếu KHÁC danh mục NHƯNG có đường đi thật
         − δ · Seen(d)                          # từ interaction_event
→ MMR [10] để tránh 5 cái lăng liên tiếp
```

Ba điểm thiết kế:

**Mỗi gợi ý mang theo đường đi sinh ra nó (FR09).** `reason_path` kiểu `Hát tuồng → [in_category] Nghệ thuật → [in_category] Nhã nhạc cung đình Huế`. Đây là điểm khác biệt so với sản phẩm thị trường: lọc cộng tác là hộp đen. Trong bối cảnh di sản và giáo dục, không giải thích được là **lỗi**, không phải khiếm khuyết hình thức. Đó là câu trả lời mạnh cho "khác gì thị trường", chứ không phải bản thân chữ "cá nhân hóa".

**`CrossDomainBonus` là định nghĩa máy móc của FR10.** Thưởng cho ứng viên đến được bằng đường đi thật *nhưng thuộc danh mục khác*, và nó cho ra một chỉ số đo được: **tỷ lệ xuyên miền ≥30%** trong top-5.

**Khởi động nguội không có bảng khai sở thích (FR07, NFR09).** Proposal đã chốt: không onboarding. Số hạng hạt giống `α` hoạt động từ tương tác đầu tiên nên phiên đầu đã hữu dụng; `β = 0` khi chưa có hồ sơ và tăng dần khi bằng chứng tích lũy. Trọng số ngầm định: view +1, dwell>20s +2, click thẻ +2, save +3, dismiss −2, suy giảm nửa chu kỳ 14 ngày. FR08 đòi mỗi mục sở thích hiển thị được **hành vi đã sinh ra nó**, nên `user_interest.source_kind` phải lưu loại tương tác chứ không chỉ trọng số.

API: `GET /api/recommend?seed=<node>&k=5` → `[{node, label, category, score, reason_path}]`

### 2.6. Thêm mới — Nhận diện ý định (Tuần 8)

Mở rộng `query_intent()` (`apps/backend/core/retriever.py:113`, hiện trả `{location, time, verify, ward}`) thành 6 lớp của Mục 12.3 Bước 2: `research | attend_event | plan_trip | learn | compare | verify`.

**Dùng biểu thức chính quy và từ vựng, KHÔNG tinh chỉnh mô hình.** Sáu lớp, tiếng Việt, luật đạt >90% và kiểm toán được — quan trọng hơn là giải thích được ở hội đồng. Tinh chỉnh cho việc này là thêm một biến số không đo được vào một dự án đã đủ biến số. Mục 10 đã ghi lựa chọn này.

Đo bằng ≥100 câu gán nhãn tay, báo cáo macro-F1 + ma trận nhầm lẫn (FR17).

### 2.7. Thêm mới — Lớp tư vấn (Tuần 8–9)

`apps/backend/core/advisor.py` — sổ đăng ký `intent → [card_generator]`:

| Ý định | Thẻ kết xuất |
| --- | --- |
| `research` | `ArtifactCard`, `MuseumCard`, `SamePeriodCard`, `RelatedCraftCard` |
| `attend_event` | `ScheduleCard`, `VenueMapCard`, `WeatherCard`, `PrepChecklistCard`, `ViewpointCard`, `ParkingCard` |
| `plan_trip` | `VenueMapCard`, `NearbyCard`, `FoodCard`, `WeatherCard` |
| `learn` | `NarrationBlock` + `RelatedCard` |
| `compare` | `ComparisonTableCard` |
| `verify` | `CorrectionBlock` (đã có sẵn qua tinh chỉnh) |

Bộ điều hợp ngoài: `apps/backend/adapters/weather.py` (Open-Meteo), `apps/backend/adapters/osm.py` (Overpass + Nominatim, cache vào bảng `poi`), `apps/backend/core/prep_rules.yaml` (~15 luật).

**Kỹ thuật ẩn độ trễ (NFR02).** `asyncio.gather` gọi API ngoài **song song** với `generate_response()`. Mô hình 3B sinh 768 token mất vài giây; API thời tiết mất ~300 ms. Chồng lên nhau thì độ trễ ngoài biến mất hoàn toàn khỏi p95.

**Suy giảm mềm (FR21).** API chết → thẻ ghi "không có dữ liệu dự báo", **không bao giờ đoán**. Đây là một ca kiểm thử, không phải một nhánh xử lý lỗi.

Mỗi thẻ mang `provenance`: `corpus | db | graph | external:open-meteo | external:osm` + `fetched_at` (NFR13).

### 2.8. Thêm mới — Biên tập và quản trị (Tuần 9)

O9 hiện chưa có gì. Cần `apps/backend/api/admin.py` với: CRUD tài liệu (F02) kích hoạt dựng lại đồ thị; CRUD bản ghi có cấu trúc và tài sản đa phương tiện (F03) với kiểm tra nguồn từ chối ở mức trường; giao diện rà soát kết quả trích xuất (F04) ghi `audit_log` kèm giá trị trước và sau; bảng điều khiển sức khỏe (F05, FR26) hiển thị số tài liệu theo danh mục, thống kê đồ thị, số trường thiếu nguồn, hàng chờ rà soát.

Đây là mục dễ bị cắt nhất khi trượt tiến độ — xem §5.

### 2.9. Sửa — Response schema `/api/chat` (Tuần 3)

`apps/backend/api/chat.py:20-22` hiện là `{answer, sources}`. Thành:

```python
class ChatResponse(BaseModel):
    answer: str                     # giữ nguyên — không phá frontend cũ
    sources: list[dict] = []        # giữ nguyên
    blocks: list[Block] = []        # MỚI: các thẻ có kiểu (FR18)
    intent: str | None = None       # MỚI (FR17)
    recommendations: list[Rec] = [] # MỚI (FR09)
```

Cộng thêm chứ không thay thế → frontend hiện tại vẫn chạy trong khi bạn xây cái mới.

### 2.10. Frontend (Tuần 10)

Hiện trạng: `apps/frontend/app/page.tsx` **88 dòng là toàn bộ ứng dụng**. `components/`, `lib/`, `public/` rỗng hoàn toàn. Không state library, không HTTP client.

Ba lỗi lệch phải sửa ngay Tuần 2:
- `page.tsx:48` quảng cáo "Qwen2.5-7B" — thực tế là **3B**
- `page.tsx:24` hardcode `http://localhost:8000` thay vì `NEXT_PUBLIC_API_URL` đã khai trong `.env.local.example`
- Type `Source` khai `{text, score?, entity?}` nhưng backend trả thêm `doc`, `url`, `heading`, `chunk_id` → **`url` đang bị bỏ im lặng**, tức trích nguồn hiển thị mà không có nguồn. Đây là lỗi FR15, không phải lỗi kiểu dữ liệu.

Cần thêm: Antd (Mục 10 đã chốt); `components/blocks/` với sổ đăng ký `type → component`; trang `/explore/[node]` có dải "liên quan" kèm lý do; Leaflet cho bản đồ; trang chi tiết kiểu Tapestry (FR23); `aria-live` trên khung hội thoại (hiện không có gì cho khả năng tiếp cận, NFR10).

### 2.11. Thêm mới — Đa phương tiện (Tuần 10)

`apps/backend/core/media.py` + `apps/backend/api/media.py`:

- Nạp mô hình 3D: kiểm giấy phép và URL nguồn, nén Draco/Meshopt xuống <30 MB (NFR19), tải lên R2, ghi `media_asset`
- **Kiểm tra bằng chứng cho script (FR30):** đối chiếu từng câu khẳng định của script với kho ngữ liệu; câu không truy được về nguồn và không được đánh dấu là lời dẫn dắt biên tập thì **chặn việc tổng hợp**. Đây là cơ chế biến nguyên tắc thứ hai ở §2.1 thành thứ kiểm chứng được.
- Tổng hợp giọng nói ngoại tuyến hai ngôn ngữ, lưu kèm transcript lên Azure Blob
- Frontend: `<model-viewer>` hoặc Three.js, audio player kèm transcript hiển thị được (NFR10), trạng thái "tài sản tạm thời không khả dụng" khi kho không truy cập được (NFR20)

### 2.12. Kiểm thử (Tuần 12–13)

Hiện tại: `apps/backend/tests/` **rỗng**, không framework, không CI, không `.github/`. Cần pytest + Playwright + GitHub Actions.

Hai ca kiểm thử quan trọng nhất của cả dự án:

```python
def test_no_fabricated_card_fields():
    """NFR06: mọi trường của mọi thẻ phải khớp bản ghi nguồn hoặc phản hồi API."""
    for card in all_generated_cards(TEST_QUERIES):
        for field, value in card.data.items():
            assert value == source_record_of(card)[field], \
                f"Trường bịa: {card.type}.{field}"


def test_audio_script_has_evidence():
    """FR30: mọi câu khẳng định trong transcript phải truy về được kho ngữ liệu."""
    for asset in all_audio_assets():
        for sent in assertive_sentences(asset.transcript):
            assert corpus_sentence_for(sent) or sent.is_editorial, \
                f"Câu audio không có nguồn: {asset.id} :: {sent}"
```

Đây là thứ biến hai nguyên tắc kiến trúc thành bằng chứng. Không có chúng thì "0 trường bịa" chỉ là một lời tuyên bố.

---

## §3. Lộ trình 13 tuần

Hôm nay 05/09/2026, hạn 06/12/2026. Ánh xạ sang bảng sprint của proposal Mục 11.3.

Hai quy tắc trình tự của Mục 11.2 chi phối thứ tự dưới đây: **việc rủi ro cao làm trước**, và **không lớp nào được xây trên một lớp chưa đo**.

### Tuần 2 (tuần này, 4 ngày) — Trả nợ đo lường

**Đây là bước quan trọng nhất. Đừng code tính năng mới trước bước này.**

1. **Sửa lỗi rò rỉ.** `pipelines/evaluation/eval_retrieval.py` exit 1: câu "Đàn Nam Giao thờ ai?" rò rỉ 1193 ký tự. Nguyên nhân: đồ thị giữ đỉnh entity cho tài liệu đã bị `corpus.py` loại. Sửa `kg.py` để bỏ đỉnh của tài liệu không dùng được.
2. **Chạy lại mô hình gốc** trên cùng 76 mẫu `pipelines/evaluation/gold.jsonl`, để phép so sánh base↔LoRA có kiểm soát.
3. **Ghi checkpoint bộ điều hợp vào `report_*.json`** (`pipelines/training/score_gold.py`) — NFR16.
4. **Sửa số liệu lạc hậu**: `README.md`, `docs/architecture.md` (23/215 → 45/349; 331/563 → 510/1135), `docs/demo-guide.md:19` (22/22 → 30/30), `apps/frontend/app/page.tsx:48` (7B → 3B).
5. **Sửa `architecture.md`** cho khớp hiện trạng: đánh dấu rõ phần Postgres/pgvector là **thiết kế mục tiêu**, không phải as-built. Nếu hội đồng đọc rồi xin xem schema thì hiện không có gì để mở.
6. **Thêm suite `PARAPHRASE`** vào `pipelines/evaluation/eval_retrieval.py` và đo baseline. Đây là bằng chứng biện minh cho Sprint 3 (§2.4 Bước 1).

### Tuần 3 — Sprint 1: Nền tảng

Postgres + pgvector + docker-compose + Alembic; models SQLAlchemy; auth argon2id + JWT cookie; middleware ghi `interaction_event` có đồng ý; `/api/me/export` + `/api/me/data`; response schema v2; Antd. **Đo p95 độ trễ ngay tuần này** — NFR01 ≤8 giây với 3B cục bộ và `MAX_TOKENS=768` là sát, đừng để Tuần 12 mới biết.

### Tuần 4 — Sprint 2: Dữ liệu miền

Toàn bộ §1. Crawl ~35 tài liệu; nhập 50 địa điểm + toạ độ, 20 sự kiện + phần, 35 cổ vật; dựng lại đồ thị; sinh lại tập vàng; chạy lại eval truy hồi.

**Cổng vào Tuần 5:** mọi danh mục ≥8 tài liệu. Nếu chưa đạt thì Sprint 4 (cá nhân hóa) không được bắt đầu — vì FR10 sẽ không thể đạt và bạn sẽ phát hiện điều đó ở Tuần 12.

→ Xong **O1, O3**

### Tuần 5 — Sprint 3: Truy hồi ba kênh

Toàn bộ §2.4: nhúng đoạn vào pgvector; hợp nhất ba kênh; sửa `retriever.py:372` và `rag.py:95`; hiệu chỉnh θ trên `OUT_OF_DOMAIN`; bảng đo tách kênh; endpoint truy vết đầy đủ (FR24).

→ Xong **O4**

### Tuần 6–7 — Sprint 4: Cá nhân hóa

**Việc đầu tiên Tuần 6: tìm và chốt danh sách mô hình 3D** (§1.8) — nếu chỉ có 2 mô hình thì biết ngay từ giờ chứ không phải Tuần 10.

Rồi: hồ sơ ngầm định + suy giảm; `recommend.py`; `/api/recommend` trả `reason_path`; `recommendation_log`; giao diện hồ sơ trong F07; trang chi tiết có dải liên quan.

→ Xong **O6**

### Tuần 8–9 — Sprint 5: Tư vấn chủ động

**Việc đầu tiên Tuần 8: kiểm tra độ phủ OSM** quanh Nam Ô và Bảo tàng Chăm (§1.5) — nếu thưa thì fallback POI soạn tay ngay.

Rồi: bộ phân loại ý định + 100 câu gán nhãn; sổ đăng ký thẻ; Open-Meteo; Overpass + cache; `prep_rules.yaml`; `asyncio.gather`. Cuối Sprint: **đo lại độ trung thực trích nguồn và độ chính xác từ chối** để chứng minh tuyên bố không-suy-giảm của O11. Kèm §2.8 (quản trị).

→ Xong **O7, O9**

### Tuần 10 — Sprint 6: Giao diện và đa phương tiện

Sổ đăng ký bộ kết xuất thẻ; trang Tapestry; dòng thời gian; Leaflet; §2.11 (nén 3D, kiểm tra bằng chứng script, tổng hợp audio, tải lên R2/Azure, trình xem Three.js); rà soát khả năng tiếp cận.

→ Xong **O8**

### Tuần 11 — Sprint 7: Hai hành trình + đệm

Hành trình nghiên cứu (cổ vật → bảo tàng → cùng thời kỳ → làng nghề) và hành trình tham dự (lễ hội → lịch → địa điểm → thời tiết → chuẩn bị → điểm quan sát → bãi xe), đúng Mục 12.5. Hấp thụ trượt tiến độ.

### Tuần 12–13 — Kiểm thử và đo

pytest + Playwright + CI; hai ca kiểm thử ở §2.12; toàn bộ chỉ số Mục 15.3; **precision@5 với 2 người đánh giá + Cohen's κ**; nghiên cứu người dùng 6–8 người (SUS); streaming nếu p95 không đạt.

→ Xong **O11**

### Tuần 14–15 — Kết thúc

Tài liệu kiến trúc, API, lược đồ; rà soát riêng tư và đạo đức; video, slide, hướng dẫn sử dụng; báo cáo cuối.

→ Xong **O10** (phần rà soát; mã đã xong từ Tuần 3)

---

## §4. Đo lường

Giữ 4 chỉ số cũ (`docs/metrics.md`), thêm những chỉ số Mục 15.3 đòi mà hiện chưa có:

| Chỉ số | Cách đo | Hiện trạng |
| --- | --- | --- |
| recall@1 / recall@3 in-domain | Các suite trong phạm vi | **Đã đo** 68/70 |
| recall trên suite diễn giải lại | Suite `PARAPHRASE`, 39 câu | **Đã đo** 9/39 — nút thắt chính |
| Đo tách kênh | Từng kênh riêng và tổ hợp, có/không đồ thị | **Chưa có** — Tuần 5 |
| Từ chối ngoài phạm vi | Suite `OUT_OF_DOMAIN` | **Đã đo** 31/38 |
| Bằng chứng trong đoạn | Suite `EVIDENCE` | **Đã đo** 34/34 |
| NER micro-F1 | `pipelines/evaluation/gold.jsonl`, có rà soát người | **Đã đo** base 0.1043 / LoRA 0.7861 |
| Trích nguồn: trung thực và độ phủ | 76 mẫu | **Đã đo** 0.7037 / 0.7407 |
| Độ chính xác từ chối | 24 mẫu từ chối | **Đã đo** 0.9167 |
| Đính chính giả định sai | Tập câu trái tiền đề | **Chưa tách riêng** — Tuần 12 |
| Ý định macro-F1 | 100 câu gán nhãn + ma trận nhầm lẫn | **Chưa có** — Tuần 8 |
| Gợi ý P@5 / nDCG@5 | 25 hạt giống × 5 gợi ý, **2 người đánh giá, báo cáo Cohen's κ** | **Chưa có** — Tuần 12 |
| Tỷ lệ xuyên miền | % top-5 khác danh mục hạt giống, mục tiêu ≥30% | **Chưa có** — Tuần 7 |
| Độ đa dạng trong danh sách | Entropy danh mục trong top-5 | **Chưa có** — Tuần 7 |
| Điểm kích hoạt cá nhân hóa | Số tương tác sau đó hồ sơ làm đổi thứ hạng | **Chưa có** — Tuần 7 |
| Độ đúng trường của thẻ | Assert tự động, mục tiêu **100%** | **Chưa có** — Tuần 8 |
| Bằng chứng script audio | Assert tự động, mục tiêu **100%** | **Chưa có** — Tuần 10 |
| Không suy giảm độ tin cậy | Đo trước–sau khi lớp tư vấn xuất hiện | **Chưa có** — Tuần 9 |
| p95 độ trễ đầu-cuối | Đo từ Tuần 3 | **Chưa có** — Tuần 3 |
| SUS | 6–8 người, ghi rõ là định tính | **Chưa có** — Tuần 12 |

Một mục tiêu không đạt nhưng **đã đo và giải thích được** là kết quả capstone chấp nhận được. Một mục tiêu **không đo** thì không.

Ba chỉ số cần người đánh giá thứ hai (Mục 11.4): nhãn vàng thực thể, độ liên quan của gợi ý. Một điểm độ liên quan do chính người viết bộ gợi ý tự cho không phải bằng chứng.

---

## §5. Rủi ro và thứ tự cắt

Rủi ro lớn nhất **không phải kỹ thuật, là phạm vi**. Proposal có 11 mục tiêu, 14 tính năng, 30 yêu cầu chức năng, 18 sản phẩm giao — với một người trong 13 tuần còn lại, trong đó 9/11 mục tiêu chưa bắt đầu.

**Thứ tự cắt khi trượt tiến độ** (quyết trước để không phải phán đoán dưới áp lực, đúng Mục 14.1):

1. Số mô hình 3D: 4 → 2 → 1 địa điểm, giữ audio narration cho các story còn lại
2. POI cửa hàng và quà → giữ bãi xe và điểm quan sát
3. Nghiên cứu người dùng 8 → 4 người
4. Giao diện quản trị (§2.8) → thay bằng CLI + một trang thống kê chỉ đọc
5. Kho ngữ liệu 80 → 65 tài liệu, **giữ nguyên mức tối thiểu 8 mỗi danh mục**
6. Audio chỉ tiếng Việt, ghi tiếng Anh vào hướng phát triển tương lai

**Không bao giờ cắt, ở bất kỳ mức áp lực nào:** các cổng từ chối, trích nguồn bắt buộc, assert không-bịa-trường (NFR06), assert bằng chứng script audio (FR30), và bộ đánh giá. Đó là đóng góp của dự án; thiếu chúng thì đây chỉ là một bản demo không kiểm chứng được.

**Ba rủi ro chưa được nêu ở proposal Mục 8.1 và cần đưa vào Mục 14 khi soạn:**

| Rủi ro | Loại | Giảm thiểu |
| --- | --- | --- |
| Ngưỡng cổng ngữ nghĩa kéo tụt độ chính xác từ chối | AI | Hiệu chỉnh θ trên `OUT_OF_DOMAIN` trước khi chốt; báo cáo NFR04 và NFR07 cùng nhau; giữ cờ bật/tắt kênh vector |
| Kênh vector không cải thiện gì vì recall@1 đã 30/30 | Đánh giá | Đo suite `PARAPHRASE` **trước** khi viết mã; nếu baseline đã cao thì ghi vào báo cáo như một kết quả và tiết kiệm một sprint |
| Không tìm được mô hình 3D di sản Việt Nam có giấy phép mở | Dữ liệu | Chốt danh sách ở Tuần 6, không Tuần 10; F12 phủ đúng số địa điểm tìm được và điều đó được nêu ở Mục 15.4 |

---

## §6. Về ví dụ cải lương

**Cải lương không thuộc kho ngữ liệu.** Cải lương và đàn ca tài tử là Nam Bộ; Nhà cổ Huỳnh Thủy Lê ở Đồng Tháp. Kho ngữ liệu hiện tại là Huế 30 + Đà Nẵng 15.

**Cơ chế thì chuyển được, dữ liệu thì không.** Không có gì trong `recommend.py` phụ thuộc vào vùng — nó lan truyền trên `in_category`, `mentions`, `in_ward`, `year`, `related`. Mở sang Nam Bộ = crawl lại, gán lại danh mục, sinh lại tập vàng, chạy lại toàn bộ eval — vài tuần, mà **không thêm một cơ chế mới nào**. Proposal Mục 16 đã ghi chính xác điều này.

**Đề xuất:** giữ một cặp địa bàn (đúng Mục 6.3), demo *cơ chế* bằng ví dụ Huế, và đưa bảng đối chiếu chứng minh ví dụ của cô chạy được về mặt cấu trúc:

| Vai trò trong ví dụ | Tương đương trong kho ngữ liệu |
| --- | --- |
| Cải lương (loại hình diễn xướng làm điểm vào) | Nhã nhạc cung đình Huế, Hát tuồng |
| Đàn ca tài tử (âm nhạc gắn liền) | Tài liệu diễn xướng cùng danh mục Nghệ thuật |
| Áo bà ba (trang phục / văn hoá vật chất) | Bản ghi làng nghề (nón lá, dệt Zèng) + cổ vật |
| Nhà cổ Huỳnh Thủy Lê (di tích để thăm) | Di tích cùng đơn vị hành chính, qua cạnh `in_ward` |
| Điểm diễn cải lương gần đó | Bản ghi `venue` + `event` có phần hội gồm loại hình đó |

Điểm quan trọng khi trình bày: cô yêu cầu **cơ chế** — đầu vào → suy luận sở thích → gợi ý xuyên miền — và cơ chế đó được hiện thực đầy đủ. Việc kho ngữ liệu là Huế thay vì Nam Bộ là một hạn chế về phạm vi dữ liệu, được nêu tường minh ở Mục 15.4 thay vì để hội đồng tự phát hiện. Và Mục 12.5 cố tình chọn **cổ vật** và **lễ hội** làm hai hành trình demo chính thay vì di tích, đúng như cô nói: văn hoá thì nhiều thứ, không chỉ diễn xướng.
