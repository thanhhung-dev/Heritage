# Cấu hình LoRA Qwen3-4B cho chat tham quan

**Khuyến nghị:** chưa train ngay. Hoàn thiện P1–P2 và cách trả lời một phần khi thiếu nguồn, chấm Qwen3-4B gốc trên bộ câu hỏi độc lập, rồi mới quyết định có cần LoRA không. File này là hướng dẫn **chuẩn bị một run thử nghiệm**, không phải cấu hình production hoặc bằng chứng model đã chạy tốt.

Đọc `AGENTS.md`, `docs/training.md`, [bản bàn giao P1–P2](tour-ai-p1-p2-qwen3-handoff.md) và [bộ câu hỏi thử Qwen3](https://ampcode.com/artifacts/bo-cau-hoi-thu-qwen3-4b-f3a6957d-52a8-4ccd-9830-09d0b3934167) trước khi thực hiện. Theo `AGENTS.md`, trình kế hoạch sửa source/config và xin duyệt trước khi làm. Không tự cài dependencies, chạy training, chuyển model production hay deploy.

## 1. LoRA ở đây cần dạy gì?

- **Dạy hành vi:** hiểu câu hỏi trong phạm vi địa điểm/cổ vật, chọn đúng `answer_type`, viết JSON hợp lệ, trích đúng passage, diễn đạt tự nhiên và nói rõ giới hạn khi thiếu chi tiết. Luật khóa phạm vi và kiểm tra nguồn vẫn do server thực thi.
- **Trả lời một phần, không từ chối máy móc:** hỏi “Ai khắc bia?” nhưng đoạn nguồn chỉ chứng minh “Vua Tự Đức tự soạn *nội dung* văn bia” → nói rõ **chưa biết người khắc**, chia sẻ thông tin người soạn cùng citation. Theo contract hiện có, đầu ra có thể là `answered` với `source_ids` của nguồn hỗ trợ phần biết được; chưa có nhãn `partial` riêng. Không đồng nhất người soạn với người khắc.
- **Chỉ dùng `insufficient_evidence` khi không có thông tin liên quan hữu ích** để đưa ra; `source_ids=[]`. Câu hỏi về địa điểm/cổ vật khác dùng `out_of_scope`, không phải `insufficient_evidence`. Không viết “đã tra nhiều nguồn” nếu chỉ truy xuất ít đoạn hoặc chưa tìm web.
- **Không train kiến thức lịch sử từ trí nhớ model:** dữ kiện vẫn phải đến từ passage được duyệt. Kết quả web (nếu về sau được bật) phải có provenance và cảnh báo riêng; **không trộn web chưa kiểm duyệt vào train như sự thật nội bộ**.

## 2. Hiện trạng pipeline cần biết

- `pipelines/training/lora_config.yaml` đã chọn `Qwen/Qwen3-4B`, LoRA FP16/BF16, `enable_thinking: false`, rank 16, alpha 32, dropout 0.05, `all-linear`, learning rate `1e-4`, ba epoch, batch 1, tích lũy gradient 8 và `max_seq_length: 1536`. Đây là **điểm xuất phát**, không phải bộ tham số tối ưu đã đo cho chat tour.
- `pipelines/training/train_hf.py` dùng Transformers/PEFT, tính loss **chỉ trên token của assistant**; đọc `train_file`, `valid_file` dạng JSONL với `messages`, rồi chọn checkpoint theo `eval_loss`. Trainer này cần NVIDIA CUDA; **không phải QLoRA 4-bit**. Không giả định 4B chắc chắn vừa một GPU cụ thể vì bộ nhớ phụ thuộc độ dài chuỗi, batch, precision và phần cứng.
- `data/train.jsonl` và `data/valid.jsonl` **chưa có trong checkout được kiểm tra**. Script `pipelines/training/make_train_set.py` gộp mẫu QA/NER cũ, không mặc định phù hợp P1–P2. `pipelines/evaluation/gold.jsonl` và `score_gold.py` hiện hướng về QA/NER cũ; không báo điểm của chúng là chất lượng chat tour.
- Tham số `--config` là cần thiết: mặc định của `train_hf.py` đang tìm `training/lora_config.yaml`, trong khi file cấu hình hiện có là `pipelines/training/lora_config.yaml`. Khi **được duyệt chạy**, truyền đường dẫn thật và tách output run mới; không sửa/ngầm ghi đè adapter khác.

## 3. Các tham số: nên giữ gì, phải đo gì?

| Tham số | Giá trị hiện có | Quyết định trước khi train |
| --- | --- | --- |
| `model_id` | `Qwen/Qwen3-4B` | Giữ đúng base đã chấm; không gộp adapter của base khác. |
| `train_file`, `valid_file` | `data/train.jsonl`, `data/valid.jsonl` | Chuẩn bị file **riêng cho tour**, chỉ trỏ config sau khi dữ liệu đã kiểm duyệt. |
| `output_dir` | `models/peft-adapter` | Dùng thư mục **mới theo run**, tránh resume hoặc ghi đè adapter cũ. |
| `enable_thinking` | `false` | Train và serve cùng chat template/chế độ; kiểm tra khả năng tương thích tokenizer. |
| `max_seq_length` | `1536` | Đo p50/p95/max token của *system + user + passages + assistant*. Kiểm tra câu trả lời không bị cắt. Tăng độ dài chỉ sau khi đo VRAM và giới hạn context lúc serve. |
| `lora_rank`, `lora_alpha`, `target_modules` | `16`, `32`, `all-linear` | Giữ ở run đầu để có baseline; chỉ đổi từng biến khi có lý do từ kết quả. |
| `learning_rate`, `num_train_epochs` | `1e-4`, `3` | Theo dõi validation loss **và** kết quả gold; giảm epoch nếu học thuộc/giảm chất lượng. Không coi train loss thấp là thành công. |
| `batch_size`, `gradient_accumulation_steps` | `1`, `8` | Điều chỉnh theo VRAM; batch hiệu dụng ban đầu là 8 mẫu cho mỗi GPU khi không có cấu hình phân tán khác. |
| `eval_steps`, `save_steps` | `25`, `25` | Kiểm tra số bước thực tế để có checkpoint và validation hữu ích, nhất là khi dataset nhỏ. |

### Mẫu config *dự kiến*, chưa tạo/trỏ tới dataset thật

Khi **đã được duyệt** và đã có data, có thể tạo file config **riêng** từ `pipelines/training/lora_config.yaml`, giữ các thông số còn lại và đổi tối thiểu:

```yaml
model_id: Qwen/Qwen3-4B
train_file: data/tour-train.jsonl
valid_file: data/tour-valid.jsonl
output_dir: models/qwen3-4b-tour-lora
enable_thinking: false
# max_seq_length, eval_steps và save_steps: đo dữ liệu thật trước khi chốt.
```

Đây chỉ là **các khóa cần thay**, không phải một file YAML hoàn chỉnh để chạy độc lập: trainer còn đọc các tham số trong config gốc. Không tự đặt `max_seq_length: 3072` hay giảm xuống 1024 chỉ vì phần cứng: phải kiểm tra rằng passage và câu trả lời còn nguyên sau tokenize. Dùng `pipelines/training/train_hf.py::tokenize_conversation` để phát hiện mẫu mất hết token assistant; tự kiểm tra thêm mẫu **bị cắt giữa câu trả lời** vì kiểm tra hiện tại chỉ từ chối mẫu mất *toàn bộ* phần assistant.

## 4. Chuẩn bị dữ liệu đúng với runtime

Một dòng train là JSONL gồm `messages`: `system`, `user`, `assistant`. Tạo `system` và `user` theo **đúng** `apps/backend/ai/answering/conversation.py::conversation_messages` của bản P1–P2 đã chốt; user message của tour gồm câu hỏi, trạng thái retrieval, đoạn `[Passage ID]`, `active_area_id`, lịch sử và marker đã xác minh. Assistant content là **chuỗi JSON** khớp `ConversationAnswer`/`conversation_json_schema` của runtime: `answer`, `answer_type`, `source_ids`. Không dùng mẫu QA/NER cũ có prompt “Nguồn: ... Câu hỏi: ...” như thể đã đúng định dạng chat tour. `follow_up_questions` chỉ nên đưa vào train nếu schema hướng dẫn sinh thật đã được thống nhất; schema hiện tại chưa cho phép trường này trong constrained JSON.

Dùng các ca có người kiểm duyệt: trả lời đầy đủ có citation; trả lời **một phần** có citation và nêu rõ chi tiết còn thiếu; nguồn sai cổ vật; thiếu tư liệu; hỏi nơi khác; hỏi nhân vật liên quan A có/không có bằng chứng; câu chào; câu mơ hồ; chỉ dẫn độc hại trong passage. Đừng gắn `answered` cho câu bịa hoặc `insufficient_evidence` cho câu có thông tin liên quan hữu ích. Kiểm tra nguồn gốc/quyền dùng tài liệu, ẩn dữ liệu cá nhân trong log nếu dùng câu hỏi thật.

Tách train/validation theo **passage hoặc cổ vật** và giữ bộ gold độc lập không bao giờ dùng train. Với dữ liệu ít, đánh giá thủ công vài mẫu đầy đủ thường hữu ích hơn tăng số lượng bằng câu trả lời do AI khác tạo mà chưa duyệt.

## 5. Trình tự kiểm tra, chưa phải lệnh phải chạy ngay

1. Xác minh P1–P2 và nguồn cho marker; chấm Qwen3-4B gốc trên bộ gold chat tour. Nếu bản gốc đã đạt yêu cầu, dừng: không cần LoRA.
2. Kiểm tra JSONL, citation, dữ liệu train/validation trùng nhau hay không; đo token/VRAM; lưu config và phiên bản base/tokenizer để tái lập kết quả.
3. Sau khi duyệt, train trên môi trường NVIDIA CUDA bằng script hiện có và `--config` trỏ tới **config run riêng**; không resume checkpoint của model/run khác.
4. So base và adapter bằng **cùng** bộ gold độc lập qua model thô và toàn server. Ghi lỗi ngoài phạm vi, tỷ lệ sai dữ kiện/citation, JSON, chất lượng lời kể và độ trễ; `eval_loss` không thay được phép đo này.
5. Chỉ khi chất lượng tốt hơn và được duyệt mới xuất GGUF và thử trên llama.cpp; thay model production, web fallback, migration và deploy là quyết định riêng.

**Bằng chứng hiện có:** mới kiểm tra file cấu hình/script và sự vắng mặt của `data/train.jsonl`/`data/valid.jsonl` trong checkout; **chưa chạy train, benchmark hoặc đo VRAM**. Cấu hình số cuối cùng phụ thuộc dữ liệu đã duyệt, máy GPU và kết quả Qwen3-4B gốc.
