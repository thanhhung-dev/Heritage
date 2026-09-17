# 4 metric đánh giá

## Mục tiêu đo lường

| Metric | Mục đích | Loại |
|---|---|---|
| **NER micro-F1** | Đánh giá khả năng trích entity đúng 4 loại | Tự động |
| **Citation precision** | Đánh giá model trích dẫn đúng nguồn | Tự động |
| **Refusal accuracy** | Đánh giá model từ chối đúng khi ngoài nguồn | Tự động |
| **Style score** | Đánh giá văn phong kể chuyện, trang trọng | Bán tự động (chấm tay) |

## 1. NER micro-F1

**Công thức:** gộp tp/fp/fn của TẤT CẢ mẫu rồi mới tính một lần:
```
tp = |pred ∩ gold|, fp = |pred \ gold|, fn = |gold \ pred|   (so khớp không phân biệt hoa/thường)
precision = Σtp / (Σtp + Σfp)      recall = Σtp / (Σtp + Σfn)
F1        = 2 * precision * recall / (precision + recall)
```

**Vì sao micro chứ không phải macro theo mẫu:** bản cũ tính F1 riêng từng mẫu rồi
lấy trung bình, và quy ước F1 = 1.0 khi cả pred lẫn gold đều rỗng. Loại `sự kiện`
gần như không xuất hiện trong corpus (6 nhãn / 3 bài), nên hầu hết mẫu rơi vào trường
hợp rỗng-với-rỗng và được cộng 1.0 miễn phí - macro-F1 bị đẩy lên mà model không
làm gì cả. Micro-F1 không cộng điểm cho mẫu rỗng.

`report.json` in cả `ner_micro` (số chính) và `ner_by_type` (từng loại, kèm
`n_gold` để biết loại nào ít mẫu tới mức không kết luận được).

**Nhãn vàng ở đâu ra:** `backend/core/nerlabel.py` suy nhãn từ chính graph
deterministic (danh từ loại tiếng Việt -> loại NER + danh sách địa điểm curated +
mốc năm), rồi con người soát tay. Nhãn nào chưa soát còn cờ `"_prefilled": true`
trong `eval/gold.jsonl`. Phải nói rõ chỗ này trong báo cáo: phần chưa soát đo
"model có học được bộ luật trích entity" chứ chưa phải "trích entity đúng".

**Tại sao quan trọng:** Đây là metric chính cho mục tiêu 1 (NER domain). Trước/sau LoRA phải có sự khác biệt rõ rệt.

**Kỳ vọng:**
- Qwen2.5-3B base: **đo thật 0.1043** trên gold set 76 mẫu / corpus 45 bài
  (08/09/2026).
- Qwen2.5-3B + LoRA checkpoint 0000200: **0.7861** trên cùng tập và cấu hình.

## 2. Citation precision

**Công thức:**
```
citation_faithful_rate      = |câu trả lời CÓ trích dẫn và MỌI trích dẫn có thật trong nguồn| / |câu QA|
citation_rate               = |câu trả lời có trích dẫn| / |câu QA|
citation_precision_when_cited = |trích dẫn có trong nguồn| / |tổng trích dẫn| (chỉ tính câu có trích dẫn)
```

Số đưa vào báo cáo là `citation_faithful_rate`. **Không trích dẫn cũng là sai** -
bản cũ chỉ tính tỉ lệ trích dẫn đúng trên các trích dẫn model đưa ra, nên model
base (không trích dẫn lần nào trong 9 mẫu) đo ra 1.0, cao bằng model hoàn hảo.

**Pattern tìm citation trong output:**
- `[Nguồn: ...]`
- `(Nguồn: ...)`
- `Nguồn: ...`

**Match với source:** substring match (case-insensitive), sau khi cắt phần
` — <url>` ở cuối vì url không nằm trong nguồn.

**Tại sao quan trọng:** Đảm bảo model không bịa citation. Mục tiêu 4 của đồ án.

**Kết quả:**
- Base: **0.0370** faithful và **0.0370** coverage trên 27 mẫu QA.
- LoRA checkpoint 0000200: **0.7037** faithful và **0.7407** coverage trên cùng
  27 mẫu QA / corpus 45 bài (`eval/report_lora.json`).

## 3. Refusal accuracy

**Công thức:**
```
accuracy = |đúng refusal| / |tổng câu hỏi|
```

**Marker từ chối (case-insensitive):**
- "không tìm thấy"
- "không có thông tin"
- "ngoài phạm vi"
- "không được cung cấp"

**Tại sao quan trọng:** Tránh model bịa. Đặc biệt với văn hóa dân gian — nhiều thông tin nhạy cảm, dễ bịa.

**Kết quả:**
- Base: **0.3750** trên 24 mẫu.
- LoRA checkpoint 0000200: **0.9167** trên cùng 24 mẫu / corpus 45 bài
  (`eval/report_lora.json`).

Gold set phải có cả nhóm `refusal-ok-*` (nguồn ĐÚNG, không được từ chối). Không có
nhóm đó thì một model từ chối mọi câu vẫn đạt 100%.

## 4. Style score

**Thang:** 1-5 cho mỗi mẫu, tiêu chí:
- **5**: Văn phong trang trọng, kể chuyện cuốn hút, có chi tiết văn hóa
- **4**: Trang trọng, đủ ý
- **3**: Bình thường
- **2**: Khô khan, liệt kê
- **1**: Sai chính tả, câu rời rạc

**Quy trình:** Chấm tay 30-50 mẫu, lấy trung bình.

**Tại sao quan trọng:** UI là "story panel" — văn phong là yếu tố cốt lõi.

## So sánh base vs LoRA (format bảng cho báo cáo)

> **PHÉP SO SÁNH CÓ KIỂM SOÁT (08/09/2026):** base và LoRA được đo trên cùng
> 76 mẫu, prompt, corpus 45 bài / 349 chunks và greedy decoding. Hai report ghi
> đầy đủ checkpoint cùng SHA-256 của scorer, gold, prompt, corpus và adapter
> trong trường `meta`. Xem bản tóm tắt tại `eval/baseline-summary.md`.

| Metric | Base (76 mẫu) | LoRA checkpoint 0000200 (76 mẫu) |
|---|---|---|
| NER micro-F1 | **0.1043** | **0.7861** |
| Citation faithful rate | **0.0370** | **0.7037** |
| Citation coverage | **0.0370** | **0.7407** |
| Refusal accuracy | **0.3750** | **0.9167** |
| Style score (1-5) | chưa chấm tay | chưa chấm tay |

Đọc citation precision cho đúng: base đạt 100% khi có cite nhưng chỉ cite 1/27
câu QA. Vì vậy phải báo cáo cùng citation coverage 3,70%; LoRA cite 20/27 câu và
19/20 câu có cite là trung thực.

## 5. Retrieval: recall + tỉ lệ từ chối (ĐÃ ĐO)

Bốn metric trên đo NỬA DƯỚI của độ chính xác (model có trung thực với nguồn
không). Nửa trên - retrieval có lấy đúng đoạn không - đo riêng, không cần model:

```bash
backend/.venv/bin/python eval/eval_attribution.py
```

Kết quả hiện tại (08/09/2026), gồm cả truy vấn gõ không dấu và diễn giải:

```
trong phạm vi = 68/70   paraphrase = 9/39   ngoài phạm vi = 31/38
bằng chứng = 34/34   phường/xã = 18/20
```

41 lỗi còn lại gồm 18 `B_RANK`, 16 `C_GATE` và 7 `E_LEAK`. Paraphrase là nút
thắt chính; bước tiếp theo là spike embedding trước khi tích hợp Hybrid RAG.

`P(đúng) = P(lấy đúng đoạn) × P(model trung thực với đoạn đó)` - nên phải đo cả
hai nửa. Sửa retrieval để nâng recall rất dễ vô tình phá cổng từ chối, vì vậy
script này luôn in cả hai con số và chỉ exit 0 khi cả hai đều đủ.

## Chạy eval

```bash
# 1. Sinh gold set (chỉ lấy từ các bài thuộc split VALID - không có trong train)
backend/.venv/bin/python eval/make_gold_template.py

# 2. Soát tay các mẫu ner-* (nhãn do nerlabel.py điền sẵn, còn cờ "_prefilled")
nano eval/gold.jsonl

# 3. Đánh giá model base (làm trước, có sẵn ngay, không cần chờ train)
python training/score_gold.py --base \
  --model Qwen/Qwen2.5-3B-Instruct \
  --gold eval/gold.jsonl \
  --out eval/report_base.json

# 4. Đánh giá đúng adapter backend đang serve
python training/score_gold.py \
  --gold eval/gold.jsonl \
  --out eval/report_lora.json

# 5. So sánh 2 file
diff eval/report_base.json eval/report_lora.json
```
