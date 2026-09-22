# Roadmap nâng cấp MVP HeritageGraph

Tài liệu này trả lời bốn câu hỏi thực thi:

1. Khi nào cần thêm dữ liệu?
2. Khi nào cần nâng lên Hybrid RAG ba kênh?
3. Khi nào nên huấn luyện lại LoRA?
4. Khi nào mới nên xây hệ thống gợi ý?

Nguồn phạm vi chính thức là PRD `docs/planning-artifacts/prds/prd-HeritageGraph-2026-09-08/prd.md`.
Roadmap này chỉ làm rõ thứ tự triển khai và các cổng kiểm tra, không thêm phạm vi mới.

> **Trạng thái 08/09/2026:** Giai đoạn 0 đã hoàn thành. Base và LoRA đã chạy lại
> trên cùng 76 mẫu với fingerprint đầy đủ; xem `pipelines/evaluation/baseline-summary.md`. Bước
> đang chờ thực hiện là Giai đoạn 1 — spike embedding trên 349 chunks.

## 1. Hiện trạng

HeritageGraph đã có:

- BM25 theo từ cho truy vấn có dấu.
- BM25 n-gram cho truy vấn không dấu và sai chính tả.
- RRF để hợp nhất hai kênh lexical.
- Đồ thị tri thức để neo, mở rộng và xếp hạng lại.
- Qwen2.5-3B-Instruct-4bit + LoRA để sinh câu trả lời, trích nguồn và từ chối.
- 45 tài liệu, 349 chunks, 6 danh mục.

Kết quả retrieval gần nhất:

| Nhóm | Kết quả | Nhận xét |
|---|---:|---|
| Truy vấn trong phạm vi | 68/70 | Đã tốt, không phải nút thắt chính |
| Paraphrase | 9/39 | Nút thắt lớn nhất; lexical không hiểu đủ quan hệ đồng nghĩa |
| Bằng chứng | 34/34 | Phải giữ nguyên |
| Phường/xã | 18/20 | Đã khá tốt |
| Từ chối ngoài phạm vi | 31/38 | Chưa đạt mục tiêu ≥90% |

Kho dữ liệu vẫn mất cân bằng:

| Danh mục | Số tài liệu hiện tại | Tối thiểu trước gợi ý |
|---|---:|---:|
| Di tích lịch sử | 22 | 8 |
| Ẩm thực | 9 | 8 |
| Danh thắng | 6 | 8 |
| Nghệ thuật | 4 | 8 |
| Lễ hội | 2 | 8 |
| Làng nghề | 2 | 8 |

## 2. Thứ tự đúng

```text
Đo baseline đáng tin
        ↓
Thử nghiệm embedding trên corpus hiện tại
        ↓
Mở rộng và cân bằng dữ liệu
        ↓
Xây Hybrid RAG ba kênh trên dữ liệu đã ổn định
        ↓
Hiệu chỉnh cổng semantic và chốt retrieval
        ↓
Đánh giá lại lỗi sinh của LLM
        ↓
Chỉ train LoRA nếu lỗi còn thuộc tầng sinh
        ↓
Xây gợi ý dựa trên graph + hồ sơ
        ↓
Xây thẻ tư vấn và hai hành trình demo
```

Không nên đảo thứ tự này. Đặc biệt, không hiệu chỉnh ngưỡng semantic trên 45 tài
liệu rồi thêm hàng chục tài liệu mà không đo lại; phân phối cosine và đối thủ xếp
hạng sẽ thay đổi khi corpus thay đổi.

## 3. Giai đoạn 0 — Chốt baseline trước khi nâng cấp

### Làm ngay

- Chạy retrieval attribution và lưu report hiện tại.
- Chạy base model và LoRA trên cùng một `pipelines/evaluation/gold.jsonl` 76 mẫu.
- Mọi report phải ghi model, checkpoint adapter, prompt version, corpus version,
  cấu hình retrieval và Git revision.
- Tách riêng các chỉ số:
  - recall in-domain;
  - recall paraphrase;
  - từ chối ngoài phạm vi;
  - citation faithful;
  - citation coverage;
  - đính chính giả định sai.

### Cổng hoàn thành

- Hai report base và LoRA dùng cùng tập dữ liệu.
- Có thể chạy lại và cho cùng kết quả.
- Không còn số liệu “baseline chưa đo” trong tài liệu.

### Chưa làm ở giai đoạn này

- Chưa train LoRA mới.
- Chưa thêm nhiều alias để chữa từng câu paraphrase.
- Chưa xây recommendation.

## 4. Giai đoạn 1 — Thử nghiệm kênh semantic trên 45 tài liệu

Đây là một **spike đo lường**, chưa phải tích hợp production hoàn chỉnh.

### Mục tiêu

Chọn embedding model bằng dữ liệu thật của dự án, không chọn theo leaderboard.

### Thực hiện

1. Thử 2–3 embedding model local, ưu tiên model multilingual/Vietnamese chạy
   được trên Apple Silicon.
2. Embed 349 chunks và tìm kiếm cosine trong bộ nhớ; chưa cần pgvector ở bước thử.
3. Đo riêng dense retrieval trên 39 câu PARAPHRASE.
4. So sánh top-1, top-3, thời gian embed và thời gian truy vấn.
5. Chọn một model và cố định dimension trước khi tạo schema `passage_embedding`.

### Cổng quyết định

Chỉ tiếp tục xây kênh vector nếu dense retrieval tạo cải thiện rõ ràng trên
PARAPHRASE. Mốc khuyến nghị cho spike:

- dense top-3 tìm thấy đúng bài ở ít nhất 70% PARAPHRASE; và
- tổ hợp thử BM25 + n-gram + dense tốt hơn baseline 9/39; và
- không dùng câu hỏi eval để thêm dữ liệu train hoặc alias thủ công.

Nếu không đạt, đổi embedding model hoặc kiểm tra chất lượng chunks trước; không
đổ thêm trọng số vào reranker để che việc ứng viên đúng không vào pool.

## 5. Giai đoạn 2 — Mở rộng và cân bằng dữ liệu

Đây là lúc **nâng dữ liệu chính thức**, trước khi chốt Hybrid RAG và trước khi làm
gợi ý.

### Dữ liệu văn bản

- Nâng corpus từ 45 lên tối thiểu 65 tài liệu; mục tiêu đầy đủ là khoảng 80.
- Bắt buộc mỗi danh mục có ít nhất 8 tài liệu.
- Ưu tiên: Lễ hội → Làng nghề → Nghệ thuật → Danh thắng.
- Mỗi tài liệu phải có URL nguồn, vùng, danh mục và alias đã rà soát.
- Không thêm tài liệu chỉ để làm đúng một câu eval cụ thể.

### Dữ liệu có cấu trúc cho MVP đầy đủ

- Tối thiểu 50 venue có tọa độ và nguồn.
- Tối thiểu 20 event có ngày, loại lịch, phần lễ/hội và nguồn.
- Tối thiểu 35 artifact có niên đại, chất liệu, bảo tàng/phòng và nguồn.
- `source_url` và `source_sentence` là bắt buộc ở mức database.

### Sau mỗi batch 5–10 tài liệu

1. Dựng lại graph.
2. Kiểm tra tài liệu cô lập và alias trùng.
3. Chạy lại toàn bộ retrieval eval.
4. Bổ sung câu hỏi vàng cho nội dung mới.
5. Ghi corpus version vào report.

### Cổng hoàn thành

- Mọi danh mục có ít nhất 8 tài liệu.
- Graph có 0 tài liệu cô lập.
- Bộ eval đã được cập nhật cho corpus mới.
- Không làm giảm nhóm gọi đúng tên, evidence và quan hệ hành chính.

### Lưu ý về LLM

Không train lại LoRA chỉ vì thêm kiến thức. Dữ kiện mới đi vào corpus và RAG;
LoRA chỉ dạy cách trả lời, trích nguồn, từ chối và đính chính.

## 6. Giai đoạn 3 — Xây Hybrid RAG ba kênh chính thức

Sau khi corpus đã đạt cổng dữ liệu, tích hợp production:

1. BM25 word.
2. BM25 n-gram.
3. Dense vector từ embedding model đã chọn.
4. Hợp nhất bằng RRF.
5. Graph mở rộng ứng viên và rerank.
6. Chọn chunk trong bài thắng.

Luồng mong muốn:

```text
query
 ├─ BM25 word ─────┐
 ├─ BM25 n-gram ───┼─ RRF ─ graph rerank ─ document rank ─ chunk rank
 └─ dense vector ──┘
```

### Hai thay đổi cổng bắt buộc

- Không trả rỗng khi lexical rỗng nhưng dense vẫn có ứng viên.
- Một hit được qua cổng khi:

```text
lexical_coverage >= MIN_COVERAGE
OR
dense_cosine >= theta
```

Không bỏ cổng từ chối. `theta` phải được hiệu chỉnh trên cả PARAPHRASE và
OUT_OF_DOMAIN.

### Bảng ablation bắt buộc

| Cấu hình | In-domain @1 | Paraphrase @1/@3 | OOD refusal | p95 retrieval |
|---|---:|---:|---:|---:|
| Word | | | | |
| N-gram | | | | |
| Dense | | | | |
| Word + n-gram | | | | |
| Ba kênh | | | | |
| Ba kênh + graph | | | | |

### Cổng hoàn thành

- Mục tiêu cuối: recall@1 in-domain ≥95%, bao gồm biến thể ngôn ngữ.
- Paraphrase được báo cáo riêng; với 39 ca, mục tiêu 95% tương đương ít nhất
  38/39 ca đúng.
- OOD refusal ≥90%, tương đương ít nhất 35/38 ca đúng.
- Evidence không giảm khỏi 34/34.
- Có cờ tắt kênh dense để tái lập ablation.
- Endpoint trace cho biết hạng của từng kênh, điểm graph và cổng nào đã chặn.

Không tiếp tục tăng recall bằng cách hạ `theta` nếu OOD refusal tụt dưới 90%.

## 7. Giai đoạn 4 — Khi nào train LoRA vòng tiếp theo?

Chỉ đánh giá việc train lại sau khi retrieval giai đoạn 3 đã ổn định. Công thức
phân trách nhiệm:

```text
Sai bài hoặc thiếu chunk đúng       → sửa retripipelines/evaluation/data
Context đúng nhưng câu trả lời sai  → sửa prompt/pipelines/training/LLM
Context đúng nhưng thiếu citation   → thêm mẫu LoRA về citation
Context thiếu dữ kiện               → thêm dữ liệu, không train LoRA
```

### Chỉ train lại khi

- Context đúng đã được đưa cho model.
- Citation faithful vẫn dưới 85%, hoặc citation coverage dưới 90%.
- Model vẫn bịa thêm chi tiết ngoài context.
- Model không đính chính giả định sai ở câu đầu.
- Các lỗi này xuất hiện trên validation documents không nằm trong train.

### Dữ liệu LoRA vòng 2 nên có

- Context đủ → trả lời ngắn, mọi khẳng định có citation nguyên văn.
- Context một phần → chỉ trả lời phần có bằng chứng.
- Context sai bài hoặc rỗng → từ chối.
- Câu hỏi có tiền đề sai → đính chính ngay câu đầu.
- Hard negative có từ khóa giống nhưng khác thực thể/vùng.

Giữ Qwen 3B và LoRA rank 16 trước. Checkpoint hiện tại đã cho thấy overfit sau
khoảng bước 250, vì vậy ưu tiên dữ liệu lỗi chất lượng cao và early stopping hơn
là tăng rank hoặc chuyển ngay sang model 7B.

### Cổng hoàn thành

- Citation faithful ≥85%.
- Citation coverage ≥90%.
- Refusal accuracy của model ≥90%.
- Không làm giảm retrieval hoặc tăng p95 vượt 8 giây.

## 8. Giai đoạn 5 — Khi nào bắt đầu sinh gợi ý?

Chỉ bắt đầu recommendation khi **cả ba điều kiện** sau đạt:

1. Mỗi danh mục có ít nhất 8 tài liệu.
2. Graph đã dựng lại và 0 tài liệu cô lập.
3. Có database cho user, interaction events và recommendation logs.

Lý do: recommendation không thể tạo gợi ý xuyên danh mục tốt nếu Lễ hội và Làng
nghề chỉ có 2 tài liệu. Tăng trọng số không thể bù cho ứng viên không tồn tại.

### Thứ tự xây recommendation

1. **Graph-only baseline:** gợi ý theo khoảng cách graph, chưa cá nhân hóa.
2. Mỗi kết quả bắt buộc có `reason_path`.
3. Thêm profile affinity từ `view`, `dwell`, `click`, `save`, `dismiss`.
4. Thêm suy giảm theo thời gian.
5. Thêm cross-domain bonus.
6. Dùng MMR hoặc luật đa dạng để top-5 không chứa quá 3 mục cùng danh mục.
7. Ghi recommendation log để đo precision@5 và nDCG@5.

### Cổng hoàn thành

- 100% gợi ý có `reason_path` hợp lệ.
- Ít nhất 1/5 gợi ý đầu khác danh mục khi graph có đường liên quan.
- Hai hồ sơ khác nhau tạo thứ tự khác nhau và giải thích được bằng trọng số.
- Precision@5 ≥70% với hai người đánh giá.

LLM không sinh danh sách gợi ý và không tự viết lý do. Lý do phải được kết xuất từ
đường đi graph thật.

## 9. Giai đoạn 6 — Thẻ tư vấn và hành trình demo

Chỉ làm sau recommendation và dữ liệu có cấu trúc:

- Intent classifier 6 lớp bằng regex + từ vựng, không fine-tune.
- Event → lịch, venue, thời tiết, chuẩn bị, điểm quan sát, bãi xe.
- Artifact → bảo tàng, phòng, hiện vật cùng thời kỳ, làng nghề liên quan.
- Mọi field lấy từ database hoặc API có provenance; không đi qua LLM.
- API chết phải trả trạng thái “không có dữ liệu”, không đoán.

Ưu tiên hoàn thiện hai hành trình:

1. Cổ vật → bảo tàng → cùng thời kỳ → làng nghề.
2. Lễ hội → lịch → địa điểm → thời tiết → chuẩn bị → quan sát → gửi xe.

3D, audio hai ngôn ngữ và giao diện quản trị đầy đủ chỉ làm sau khi hai hành trình
văn bản hoạt động và các chỉ số an toàn đã đạt.

## 10. Lịch đề xuất dễ theo dõi

| Thứ tự | Công việc | Thời lượng gợi ý | Điều kiện để sang bước sau |
|---:|---|---:|---|
| 0 | Chốt baseline retrieval + base/LoRA | 1–2 ngày | Report so sánh được |
| 1 | Spike 2–3 embedding models | 1–2 ngày | Dense top-3 paraphrase ≥70% |
| 2 | PostgreSQL/pgvector + schema nguồn | 2–4 ngày | Migration và constraint chạy xanh |
| 3 | Cân bằng corpus + structured data | 5–8 ngày | ≥8 tài liệu/danh mục |
| 4 | Hybrid RAG ba kênh + calibration | 3–5 ngày | NFR04/NFR07 đạt hoặc có bảng đánh đổi |
| 5 | LoRA vòng 2 nếu cần | 2–3 ngày | Citation/refusal đạt mục tiêu |
| 6 | Graph recommendation baseline | 2–3 ngày | 100% có reason_path |
| 7 | Cá nhân hóa + đa dạng | 3–5 ngày | P@5 và xuyên miền đo được |
| 8 | Intent + thẻ tư vấn | 4–6 ngày | 0 field bịa, fallback chạy xanh |
| 9 | Hai hành trình demo | 2–4 ngày | E2E hoàn chỉnh |

Thời lượng là ước lượng cho một người và cần điều chỉnh sau mỗi gate. Nếu một gate
không đạt, quay lại đúng tầng gây lỗi; không tiếp tục xây tầng phía trên.

## 11. Quy tắc quyết định nhanh

| Quan sát | Việc cần làm |
|---|---|
| Gold document không vào top-50 | Cải thiện candidate generation/dense retrieval |
| Gold document có trong pool nhưng không top-1 | Rerank/RRF/graph weights |
| Đúng bài nhưng sai chunk | Chunking hoặc chunk rerank |
| Đúng context nhưng model trả lời sai | Prompt hoặc LoRA |
| Corpus không có dữ kiện | Thêm dữ liệu có nguồn |
| Paraphrase thấp, exact-name cao | Thêm kênh dense, không thêm alias từng câu |
| OOD thấp sau khi thêm dense | Tăng/hiệu chỉnh `theta`, không xóa cổng |
| Gợi ý thiếu đa dạng | Cân bằng dữ liệu trước, sau đó mới MMR |
| LLM bịa ngày/địa điểm/thời tiết | Đưa field sang typed record/card renderer |

## 12. Việc tiếp theo ngay bây giờ

1. Chốt report retrieval hiện tại làm baseline mới.
2. Chạy base và LoRA trên cùng 76 mẫu, sửa metadata report.
3. Tạo spike embedding trong bộ nhớ trên 349 chunks.
4. Chọn embedding model dựa trên top-3 của PARAPHRASE.
5. Sau khi chọn model, hoàn thiện pgvector và bắt đầu batch dữ liệu đầu tiên cho
   Lễ hội, Làng nghề, Nghệ thuật và Danh thắng.

Không train LoRA và không xây recommendation trước năm bước trên.
