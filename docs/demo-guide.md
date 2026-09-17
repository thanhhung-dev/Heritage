# Hướng dẫn demo cho hội đồng

## Trước buổi bảo vệ (1 ngày)

- [ ] Chạy full pipeline: crawl → xây graph → sinh data → train → fuse
- [ ] Verify backend + frontend chạy được
- [ ] Test 5-10 câu hỏi mẫu, chuẩn bị "demo script"
- [ ] In sẵn 4 metric (NER F1, Citation, Refusal, Style) + số đo retrieval
- [ ] Chuẩn bị slide với sơ đồ kiến trúc

## Setup trong phòng bảo vệ (10 phút trước)

```bash
# 1. Mở Terminal, cd vào project
cd ~/CAP/HeritageGraph

# 2. Verify graph + retrieval (1 giây, không cần model)
backend/.venv/bin/python eval/eval_attribution.py
#    → trong phạm vi 68/70; paraphrase 9/39; bằng chứng 34/34;
#      phường/xã 18/20; ngoài phạm vi 31/38

# 3. Chạy cả backend + frontend
bash scripts/start_dev.sh

# 4. Mở browser
open http://localhost:3000
```

Không cần khởi động Ollama: graph được xây deterministic trong RAM lúc backend
lên, không có bước index bằng LLM.

## Demo flow (10-15 phút)

### 1. Giới thiệu kiến trúc (2 phút)
- Mở slide kiến trúc
- Giải thích: graph + BM25 (knowledge) + LoRA (output style) + FastAPI/Next.js (app)
- Cho xem graph thật, không chỉ sơ đồ:
  `backend/.venv/bin/python scripts/build_graph.py --node "triều Nguyễn"`

### 2. Demo chatbot (5 phút)
Mở `http://localhost:3000`, hỏi tuần tự:

| Câu hỏi | Mục đích demo |
|---|---|
| "Hãy kể về Festival Huế" | Trả lời dài, có citation, văn phong trang trọng |
| "Trích entity từ đoạn sau: Điện Hòn Chén được vua Minh Mạng cho tu sửa và mở rộng vào tháng 3/1832." | NER đúng 4 loại, format JSON |
| "Ngũ Hành Sơn có ý nghĩa gì trong văn hóa Đà Nẵng?" | Kết hợp kiến thức + citation |
| "Hãy kể chi tiết về Hoàng thành Huế" | Test với câu hỏi dài, multi-entity |
| "Chùa Một Cột được xây năm nào?" | Ngoài phạm vi corpus → phải TỪ CHỐI, không bịa |

Chỉ hỏi về 45 bài đã crawl được (`backend/.venv/bin/python -c "..."` hoặc xem
`corpus/locations_index.json`). Lưu ý danh mục bị lệch: Di tích lịch sử 22,
Ẩm thực 9, Danh thắng 6, Nghệ thuật 4, Lễ hội 2, Làng nghề 2 — nên câu hỏi về
lễ hội/làng nghề dễ rơi vào "ngoài phạm vi": đúng theo thiết kế, nhưng đừng đưa
vào phần demo kiến thức.

### 3. So sánh base vs LoRA (3 phút)
Mở terminal:
```bash
# Sinh gold set (lấy từ 5 bài KHÔNG có trong train) rồi soát tay phần ner-*
backend/.venv/bin/python eval/make_gold_template.py

# Đo base và đo LoRA bằng CÙNG một prompt (backend/core/prompt.py)
python training/score_gold.py --base --model Qwen/Qwen2.5-3B-Instruct \
  --gold eval/gold.jsonl --out eval/report_base.json
python training/score_gold.py \
  --gold eval/gold.jsonl --out eval/report_lora.json
```

Bảng so sánh có kiểm soát: cả hai cột đo trên cùng 76 mẫu, corpus 45 bài,
prompt và greedy decoding (08/09/2026):

| Metric | Base (76 mẫu) | LoRA checkpoint 0000200 (76 mẫu) | Lấy ở đâu trong report |
|---|---|---|---|
| NER micro-F1 | 0.1043 | 0.7861 | `ner_micro.f1` |
| Citation faithful rate | 0.0370 | 0.7037 | `citation_faithful_rate` |
| Citation coverage | 0.0370 | 0.7407 | `citation_coverage` |
| Refusal accuracy | 0.3750 | 0.9167 | `refusal_accuracy` |

> Hai report có trường `meta` để kiểm tra checkpoint và fingerprint; bản tóm tắt
> dùng cho slide nằm tại `eval/baseline-summary.md`.

Ba điều phải nói thẳng nếu hội đồng hỏi:
- Nhãn NER trong gold do `backend/core/nerlabel.py` điền sẵn từ graph rồi soát tay;
  phần chưa soát vẫn còn cờ `"_prefilled": true`.
- Loại `sự kiện` gần như không có mẫu (danh mục Lễ hội chỉ có 2 tài liệu trong
  corpus 45 bài), nên F1 của riêng loại đó không đủ dữ liệu để kết luận - đọc
  `ner_by_type.<loại>.n_gold`. Nguyên nhân gốc: danh mục lễ hội/làng nghề chưa
  đạt ngưỡng ≥8 tài liệu — việc bổ sung nằm trong upgrade-plan §1.1 (Tuần 4).
- NER base 0.08 phần lớn là lỗi ĐỊNH DẠNG (4/8 mẫu trả về markdown thay vì JSON),
  không phải trích sai hết. Nói đúng như vậy, đừng để bảng tự nói quá.

### 4. Q&A hội đồng (5 phút)
Câu hỏi thường gặp + cách trả lời:

**"Tại sao không dùng GPT-4 thay vì Qwen?"**
> "Mục tiêu đồ án là fine-tune AI cho bài toán cụ thể, không phải gọi API. Qwen + LoRA cho phép customize format output (NER, citation, refusal) mà GPT-4 prompt-only khó đạt được độ ổn định. Ngoài ra chạy 100% local giúp demo reproducible, không phụ thuộc API key."

**"Tại sao dùng graph thay vì vector search?"**
> "Hai lý do đo được. Một: graph giúp xác định câu hỏi có thuộc miền tri thức và giữ bằng chứng 34/34, nhưng ngoài phạm vi hiện mới chặn đúng 31/38. Hai: graph bơm thêm ứng viên vào pool retrieval, nên câu gõ không dấu như 'cao lau la mon gi' vẫn lấy đúng bài dù điểm từ khoá thấp."

**"Sao không dùng Microsoft GraphRAG?"**
> "Đã cân nhắc và bỏ. Nó cần LLM extract entity: 8-12 giờ index trên corpus này, prompt mặc định bằng tiếng Anh chạy trên văn bản tiếng Việt sai nhiều, và entity do LLM sinh ra có thể bịa. Graph ở đây xây deterministic bằng khớp tên thực thể + mẫu 'danh từ loại + tên riêng' của tiếng Việt: 510 node / 1135 edge, build hết 0.23 giây, và mọi node đều truy được về một chuỗi có thật trong văn bản."

**"Tại sao dùng LoRA?"**
> "LoRA chỉ tối ưu các ma trận hạng thấp thay vì cập nhật toàn bộ model, nên giảm VRAM và kích thước artifact trong khi base model vẫn được train ở FP16/BF16. Kiến thức đến từ nguồn được truy xuất; LoRA chủ yếu dạy văn phong, trích nguồn và hành vi từ chối."

**"Mất bao lâu để train?"**
> "Thời gian phụ thuộc GPU Kaggle, sequence length và số mẫu. Pipeline ghi checkpoint và tự resume; thời gian thực tế phải lấy từ log của run CUDA hiện tại, không dùng lại số đo MLX cũ."

**"Chi phí toàn bộ dự án?"**
> "Dưới $1 (chỉ tính điện). Toàn bộ stack local, không tốn API."

## Checklist trước khi demo

- [ ] Laptop sạc đầy
- [ ] Internet tắt (để chứng minh chạy local)
- [ ] Terminal sẵn sàng
- [ ] Browser mở sẵn localhost:3000
- [ ] Slide mở sẵn
- [ ] 4 metric sẵn sàng show
