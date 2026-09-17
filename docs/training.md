# Training LoRA bằng Docker và Kaggle

Pipeline training không còn phụ thuộc MLX. Nguồn chuẩn là
`training/train_hf.py`; Docker và Kaggle chỉ là hai môi trường chạy cùng script.

## Luồng artifact

```text
data/train.jsonl + data/valid.jsonl
  -> LoRA FP16/BF16 bằng Transformers/PEFT
  -> models/peft-adapter
  -> gold evaluation
  -> merge FP16 + llama.cpp converter
  -> models/qwen-fused.gguf
  -> service llm trong docker-compose.yml
```

Adapter MLX cũ không tương thích với PEFT. Pipeline mới dùng thư mục
`models/peft-adapter`, vì vậy không ghi đè checkpoint MLX đang có.
Base model được load trực tiếp ở FP16/BF16 khi train; không có NF4 hay 4-bit.
GGUF Q8_0 chỉ là bản lượng tử hóa để chạy local sau khi LoRA đã train xong.

## 1. Chuẩn bị dữ liệu

Trainer nhận JSONL dạng chat hiện tại:

```json
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```

Sinh lại dữ liệu nếu cần:

```bash
backend/.venv/bin/python training/bootstrap_deep_qa.py
```

Nếu dùng teacher model, khởi động một llama.cpp server trước rồi chạy:

```bash
backend/.venv/bin/python training/bootstrap_deep_qa.py \
  --use-model --model http://localhost:8080
```

## 2. Train trong Docker

Yêu cầu máy Linux x86_64 có NVIDIA driver, NVIDIA Container Toolkit và Docker Compose.
Docker Desktop trên macOS không truyền Metal/GPU Apple vào Linux container; trên
Mac chỉ nên chạy unit test, không train LoRA trong container CUDA này.

```bash
docker compose --profile training build trainer
docker compose --profile training run --rm trainer
```

Trainer tự resume thư mục `checkpoint-N` mới nhất. Muốn bắt đầu run mới mà không
resume, nên đổi `output_dir` trong một config riêng, sau đó chạy:

```bash
docker compose --profile training run --rm trainer \
  python training/train_hf.py --config training/my_run.yaml --fresh
```

Không xóa hoặc dùng lại output của một base model khác. Optimizer state và LoRA
shape trong checkpoint gắn với đúng model/config đã tạo nó.

## 3. Train trên Kaggle

Kaggle đã chạy notebook trong container của Kaggle, vì vậy không chạy
`docker compose` bên trong notebook. Bật GPU và Internet, rồi dùng các cell:

```python
%cd /kaggle/working
!git clone https://github.com/thanhhung-dev/HeritageGraph.git
%cd HeritageGraph
!nvidia-smi
!pip install -r training/requirements.txt
```

`data/` bị Git ignore. Upload `train.jsonl` và `valid.jsonl` thành một Kaggle
Dataset riêng, attach nó vào notebook, rồi copy vào working directory:

```python
!mkdir -p data
!cp /kaggle/input/heritagegraph-training-data/train.jsonl data/train.jsonl
!cp /kaggle/input/heritagegraph-training-data/valid.jsonl data/valid.jsonl
!python training/train_hf.py --config training/lora_config.yaml --fresh
```

Output nằm ở `/kaggle/working/HeritageGraph/models/peft-adapter`. Sau khi train,
phải Save Version hoặc tải artifact về; `/kaggle/working` không phải nơi lưu trữ
lâu dài giữa các session.

```python
!python training/score_gold.py \
  --gold eval/gold.jsonl --out eval/report_lora.json
!python scripts/export_gguf.py --force
!tar -czf /kaggle/working/heritagegraph-lora-artifacts.tar.gz \
  -C models peft-adapter qwen-fused.gguf

from IPython.display import FileLink
FileLink("/kaggle/working/heritagegraph-lora-artifacts.tar.gz")
```

Link cuối cho phép tải cả adapter PEFT và GGUF về máy. Nếu Kaggle hết RAM khi
export, chỉ nén `peft-adapter`, tải về rồi export trên máy có đủ RAM.

### Đưa kết quả Kaggle về máy chạy local

Giải nén file vừa tải vào repository:

```bash
mkdir -p models
tar -xzf ~/Downloads/heritagegraph-lora-artifacts.tar.gz -C models
ls models/peft-adapter/adapter_model.safetensors models/qwen-fused.gguf
```

Chạy GGUF native trên Mac để dùng Metal:

```bash
brew install llama.cpp
llama-server --model models/qwen-fused.gguf --host 127.0.0.1 --port 8080 \
  --ctx-size 4096
```

Ở terminal khác, backend mặc định gọi `http://localhost:8080`:

```bash
backend/.venv/bin/uvicorn backend.app:app --port 8000
```

Cũng có thể chạy service llama.cpp bằng Docker, nhưng trên macOS container chỉ
dùng CPU nên chậm hơn bản native Metal:

```bash
POSTGRES_PASSWORD=local-only docker compose up -d llm
```

Nếu Kaggle chỉ trả về adapter mà chưa có GGUF, export trên máy local:

```bash
python3 -m venv .venv-export
.venv-export/bin/pip install torch -r training/requirements.txt
.venv-export/bin/python scripts/export_gguf.py --force
```

Muốn resume ở session Kaggle sau, đưa nguyên thư mục `peft-adapter` lên một
Kaggle Dataset, copy lại vào `models/`, rồi chạy trainer không có `--fresh`.

### Đóng gói để giao máy khách hàng

Sau khi `models/qwen-fused.gguf` đã nằm trong repository trên máy phát triển:

```bash
bash scripts/package_docker.sh
```

Gửi `heritagegraph-docker.tar.gz` cho khách hàng. Gói chứa code, corpus, GGUF và
`.env` đã sinh mật khẩu database ngẫu nhiên. Máy khách chỉ cần cài Docker, có
internet ở lần chạy đầu, rồi chạy:

```bash
tar -xzf heritagegraph-docker.tar.gz
cd HeritageGraph
docker compose up -d
```

Compose tự dựng frontend/backend, chạy PostgreSQL migration, import corpus và
khởi động llama.cpp. Giao diện mở tại `http://localhost:3000`. Nếu máy khách hoàn
toàn offline thì không thể chỉ dùng `compose up` từ source package; cần đóng gói
thêm toàn bộ Docker image và chạy `docker load` trước.

## 4. Đánh giá và xuất GGUF

Chạy trên Linux/Kaggle đã cài training requirements, hoặc dùng chính container:

```bash
docker compose --profile training run --rm trainer bash training/eval.sh
docker compose --profile training run --rm trainer bash training/eval.sh 75
docker compose --profile training run --rm trainer bash training/fuse.sh
docker compose --profile training run --rm trainer bash training/fuse.sh 75
```

Export đọc `base_model_name_or_path` từ `adapter_config.json`, do đó không thể vô
tình merge adapter vào sai base model. Kết quả `models/qwen-fused.gguf` được dùng
trực tiếp bởi service `llm` hiện tại.

Merge model 8B FP16 cần nhiều RAM. Nếu Kaggle hết RAM ở bước export,
chỉ train/evaluate adapter trên Kaggle, tải adapter về và export trên máy Linux
hoặc cloud instance có đủ RAM.

## 5. Chọn model để nâng cấp

Không có checkpoint chính thức tên `Qwen3.5-8B`; dòng gần nhất là
[`Qwen/Qwen3.5-9B`](https://huggingface.co/Qwen/Qwen3.5-9B). Qwen3.8 open hiện
có model dense 27B, quá lớn cho LoRA trên GPU Kaggle phổ thông và không phù hợp
làm bước nâng cấp kế tiếp của ứng dụng này.

Lựa chọn ít rủi ro nhất để nâng khả năng suy luận là
[`Qwen/Qwen3-8B`](https://huggingface.co/Qwen/Qwen3-8B): model text-only, hỗ trợ
Transformers ổn định, có thinking/non-thinking và có hệ sinh thái GGUF/llama.cpp.
Tạo config mới thay vì sửa run 3B đang dùng:

```bash
cp training/lora_config.yaml training/qwen3_8b.yaml
```

Sửa tối thiểu:

```yaml
model_id: Qwen/Qwen3-8B
output_dir: models/qwen3-8b-peft-adapter
batch_size: 1
gradient_accumulation_steps: 8
max_seq_length: 1024
target_modules: all-linear
```

Nếu chỉ có T4 16 GB và vẫn muốn LoRA không lượng tử hóa, dùng
[`Qwen/Qwen3-4B`](https://huggingface.co/Qwen/Qwen3-4B) trước. Một ứng viên cần
đo riêng cho tiếng Việt là
[`sail/Sailor2-8B-Chat`](https://huggingface.co/sail/Sailor2-8B-Chat), được tiếp
tục pretrain từ Qwen2.5 cho các ngôn ngữ Đông Nam Á gồm tiếng Việt. Không chọn
chỉ theo benchmark chung: chạy cùng gold set retrieval/citation/refusal và chọn
model thắng trên dữ liệu HeritageGraph.

LoRA không lượng tử hóa base model: riêng trọng số 8B FP16/BF16 đã gần 16 GB,
chưa tính activation và CUDA overhead. Kaggle T4/P100 16 GB không phải lựa chọn
an toàn cho LoRA 8B; nên dùng GPU tối thiểu 24 GB, 40 GB sẽ ổn định hơn. Bắt đầu
với batch 1, gradient checkpointing và `max_seq_length: 1024`, rồi tăng dần nếu
còn VRAM. Luôn train ra output mới và chạy lại toàn bộ gold evaluation trước khi
thay GGUF production.
