# Baseline đánh giá — 08/09/2026

Baseline này thay thế phép so sánh cũ dùng hai tập mẫu khác nhau. Base và LoRA
được chạy lại bằng cùng scorer, cùng 76 mẫu, cùng prompt, cùng corpus và greedy
decoding. Báo cáo đầy đủ được sinh tại `pipelines/evaluation/report_base.json`,
`pipelines/evaluation/report_lora.json` và bị bỏ qua bởi Git vì chứa toàn bộ raw outputs.

## Danh tính lần chạy

| Thành phần | Giá trị |
|---|---|
| Base model | `mlx-community/Qwen2.5-3B-Instruct-4bit` |
| LoRA adapter | `models/lora-serve` |
| LoRA checkpoint | `0000200` |
| Adapter SHA-256 | `704ae2cc01d58d2466060a7f0d5c985c9d037c79d31f8e87363a64c2db723a9e` |
| Gold samples | 76 |
| Gold SHA-256 | `7a6765f74ad0f834bfced0803b1fc4f38dfd674fbf6a9cbb973d515672e0d2e2` |
| System prompt SHA-256 | `6947063c86eeedee5bbb2f0f2e2f853f8b05140e0bc62b59e9501affa1c2dd4e` |
| Corpus SHA-256 | `e392ff805a325ecbfa50507b324d4b93453766e199f372f384a2a632c9c1db0f` |
| Corpus | 45 tài liệu / 349 chunks / 2 tài liệu bị loại |
| Sampling | greedy, temperature 0, max 768 tokens; NER max 256 tokens |

Worktree có thay đổi chưa commit tại thời điểm chạy. Vì vậy Git revision một mình
không đủ tái lập; các SHA-256 của scorer, prompt, gold, corpus và adapter trong
trường `meta` của hai report đầy đủ mới là định danh chính xác của lần chạy.

## Base so với LoRA

| Metric | Base | LoRA checkpoint 0000200 | Chênh lệch |
|---|---:|---:|---:|
| NER micro-F1 | 0,1043 | 0,7861 | +0,6818 |
| Citation faithful | 3,70% | 70,37% | +66,67 điểm % |
| Citation coverage | 3,70% | 74,07% | +70,37 điểm % |
| Citation precision khi có cite | 100% | 95% | −5 điểm % |
| Refusal accuracy | 37,50% | 91,67% | +54,17 điểm % |

Citation precision 100% của base không có nghĩa base tốt hơn: base chỉ trích dẫn
ở 1/27 câu QA. Hai chỉ số chính phải đọc cùng nhau là citation faithful và
citation coverage.

## Retrieval baseline

Báo cáo đầy đủ: `pipelines/evaluation/report_retrieval.json`.

| Suite | Kết quả |
|---|---:|
| Trong phạm vi | 68/70 |
| Paraphrase | 9/39 |
| Bằng chứng | 34/34 |
| Phường/xã | 18/20 |
| Ngoài phạm vi | 31/38 |

Quy trách nhiệm 41 lỗi còn lại:

- 18 `B_RANK`: đúng bài vào pool nhưng chưa đứng đầu.
- 16 `C_GATE`: bài đúng đứng đầu nhưng cổng chặn context.
- 7 `E_LEAK`: câu ngoài phạm vi vẫn nhận context.

## Kết luận cho bước tiếp theo

- LoRA có cải thiện lớn và đã vượt mục tiêu refusal 90%.
- LoRA chưa đạt citation faithful 85% và citation coverage 90%.
- Chưa train LoRA vòng mới: paraphrase 9/39 cho thấy tầng retrieval vẫn là nút
  thắt cần giải quyết trước.
- Bước tiếp theo là spike embedding trên 349 chunks, đo dense top-1/top-3 trên
  PARAPHRASE trước khi tích hợp pgvector.
