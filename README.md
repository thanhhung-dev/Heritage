# HeritageGraph — Chatbot văn hóa Đà Nẵng – Huế

Chatbot hỏi đáp về di sản, ẩm thực và nghệ thuật **Đà Nẵng – Huế**, chạy 100% local.

- **Retrieval**: BM25 theo từ + BM25 theo n-gram (chịu được gõ không dấu) hợp nhất
  bằng RRF, mở rộng và xếp lại bằng **knowledge graph dựng deterministic** — không
  gọi LLM lúc index, không Ollama, không vector DB (`apps/backend/core/kg.py`).
- **LoRA fine-tune**: Hugging Face Transformers + PEFT FP16/BF16, chạy CUDA Docker/Kaggle
- **Backend**: FastAPI · **Frontend**: Next.js
- **Không cần API key, không cần internet** sau khi crawl xong corpus.

Đo được hiện tại: trong phạm vi `68/70`, paraphrase `9/39`, bằng chứng `34/34`,
ngoài phạm vi `31/38` bằng `pipelines/evaluation/eval_attribution.py`; graph 510 node / 1135
edge, dựng hết 0.23 giây.

## Cấu trúc

```
HeritageGraph/
├── apps/
│   ├── backend/
│   │   ├── app.py
│   │   ├── api/{chat,health,graph}.py
│   │   └── core/                 # retrieval, KG, RAG và LLM
│   └── frontend/                 # Next.js
├── pipelines/
│   ├── ingestion/                # crawl và chuẩn hóa corpus
│   ├── graph/                    # build, export và truy dấu knowledge graph
│   ├── training/                 # tạo dữ liệu, fine-tune và fuse model
│   └── evaluation/               # gold set, benchmark và báo cáo
├── corpus/
│   ├── wiki_by_location/*.txt
│   └── locations_index.json      # 25 crawl được / 24 chưa
├── data/                         # train.jsonl + valid.jsonl
├── models/                       # peft-adapter/ + qwen-fused.gguf
└── docs/
```

## Chạy local và kiểm tra health

Tất cả lệnh bên dưới chạy từ project root. Java không được sử dụng trong project.

### 1. Yêu cầu

| Công cụ | Phiên bản |
|---|---|
| Python | `3.12.11` |
| Node.js | `20.19.3` |
| npm | `10.8.2` |
| Docker | Docker Engine/Desktop có Compose v2 |

Kiểm tra môi trường trước khi cài:

```bash
python --version
node --version
npm --version
docker compose version
```

### 2. Cài backend và frontend

macOS/Linux:

```bash
python3.12 -m venv apps/backend/.venv
source apps/backend/.venv/bin/activate
python -m pip install -r apps/backend/requirements.txt

cd apps/frontend
npm ci
cd ../..
```

Windows PowerShell:

```powershell
py -3.12 -m venv apps/backend/.venv
.\apps\backend\.venv\Scripts\Activate.ps1
python -m pip install -r apps/backend/requirements.txt

Push-Location apps/frontend
npm ci
Pop-Location
```

### 3. Cấu hình môi trường

macOS/Linux:

```bash
cp .env.example .env
cp apps/frontend/.env.local.example apps/frontend/.env.local
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item apps/frontend/.env.local.example apps/frontend/.env.local
```

Mở `.env`, thay password mẫu và giữ `POSTGRES_PASSWORD` khớp với password
trong `DATABASE_URL`. Cấu hình local tối thiểu:

```dotenv
POSTGRES_DB=heritagegraph
POSTGRES_USER=heritagegraph
POSTGRES_PASSWORD=replace-with-a-random-local-password
DATABASE_URL=postgresql+psycopg://heritagegraph:replace-with-a-random-local-password@localhost:5433/heritagegraph
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=300
DATABASE_ECHO=false
DATABASE_SSL_MODE=disable
DATABASE_SSL_ROOT_CERT=
INFERENCE_BACKEND=llama_server
LLAMA_SERVER_URL=http://localhost:8080
LLAMA_SERVER_TIMEOUT=300
```

Frontend đọc `NEXT_PUBLIC_API_URL=http://localhost:8000` từ
`apps/frontend/.env.local`. Biến có tiền tố `NEXT_PUBLIC_` được gửi xuống trình
duyệt, vì vậy không đặt password hoặc API key vào đó. Không commit `.env` hoặc
`.env.local`.

Nếu `DATABASE_URL` thiếu hoặc sai định dạng, backend sẽ dừng ngay khi startup và
in ra biến cấu hình cần sửa; không mở cổng với cấu hình chưa hợp lệ.

AWS staging phải mount AWS RDS CA bundle vào runtime rồi cấu hình đường dẫn bên
trong máy/container chạy backend:

```dotenv
DATABASE_SSL_MODE=verify-full
DATABASE_SSL_ROOT_CERT=/run/secrets/aws-rds/global-bundle.pem
```

Không thêm password hoặc connection string vào log. `DATABASE_ECHO` mặc định
phải là `false`; chỉ bật tạm thời khi debug local.

### 4. Chuẩn bị corpus, database và model

Corpus không nằm trong Git. Crawl lần đầu bằng Python environment vừa tạo:

```bash
python pipelines/ingestion/crawl_by_location.py
```

Health check yêu cầu hai artifact sau tồn tại:

- `corpus/locations_index.json` và thư mục `corpus/wiki_by_location/`;
- `models/qwen-fused.gguf` khi dùng `llama_server` qua Docker Compose.

Xem [hướng dẫn training](docs/training.md) để tạo GGUF. Sau khi có corpus và
model, khởi tạo PostgreSQL, migration, dữ liệu và llama.cpp:

```bash
docker compose up -d db
docker compose run --rm migrate
docker compose run --rm import-data
docker compose up -d llm
```

Không cần Ollama hoặc package `graphrag`; graph được dựng trực tiếp bằng
`apps/backend/core/kg.py`.

### 5. Chạy backend và frontend

Terminal 1, từ project root và với Python virtual environment đã activate:

```bash
python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```bash
cd apps/frontend
npm run dev
```

Các địa chỉ local:

- Frontend: <http://localhost:3000>
- Backend API docs: <http://localhost:8000/docs>
- Backend health: <http://localhost:8000/api/health>

### 6. Kiểm tra health

macOS/Linux:

```bash
cd ~/CAP/HeritageGraph
cp .env.example .env
cp apps/frontend/.env.local.example apps/frontend/.env.local
python3 -m venv apps/backend/.venv
apps/backend/.venv/bin/pip install -r apps/backend/requirements.txt

```powershell
curl.exe -i http://localhost:8000/api/health
```

Khi llama.cpp và corpus đều sẵn sàng, endpoint trả HTTP `200`:

```json
{
  "status": "ok",
  "inference_backend": "llama_server",
  "model_ready": true,
  "corpus_ready": true
}
```

HTTP `503` với `status: "starting"` nghĩa là backend đã nhận request nhưng model
hoặc corpus chưa sẵn sàng. Kiểm tra lần lượt:

```bash
docker compose ps db llm
docker compose logs llm
```

Health endpoint hiện kiểm tra model runtime và corpus. Trạng thái PostgreSQL xem
bằng `docker compose ps db`.

### 7. Chạy toàn bộ bằng Docker

Nếu không chạy Python/Node trực tiếp, tạo `.env` từ template Docker, thay
`POSTGRES_PASSWORD`, bảo đảm corpus và GGUF đã có rồi chạy:

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl -i http://localhost:8000/api/health
```

Trên PowerShell, thay lệnh đầu bằng:

```powershell
Copy-Item .env.example .env
```

Hướng dẫn vận hành Docker chi tiết nằm tại [docs/docker-local.md](docs/docker-local.md).

## Chuẩn bị dữ liệu và model

### Crawl corpus (~10 phút)

```bash
python pipelines/ingestion/crawl_by_location.py
```

Kết quả ghi vào `corpus/wiki_by_location/` + `corpus/locations_index.json`.

### Xây và kiểm tra graph (~1 giây)

```bash
bash pipelines/graph/run_indexing.sh                            # thống kê + xuất artifact
python pipelines/graph/build_graph.py --node "triều Nguyễn"
python pipelines/graph/build_graph.py --query "lăng Minh Mạng xây năm nào"
python pipelines/evaluation/eval_attribution.py              # retrieval + quy trách nhiệm lỗi
```

Artifact ra `graphrag/output/`: `graph.gexf` (mở bằng Gephi), `graph.json`
(node-link cho frontend), `stats.json`.

### Train LoRA

```bash
python pipelines/training/bootstrap_deep_qa.py   # sinh data/train.jsonl + valid.jsonl
docker compose --profile training run --rm trainer       # Linux có NVIDIA GPU
docker compose --profile training run --rm trainer bash pipelines/training/eval.sh
docker compose --profile training run --rm trainer bash pipelines/training/fuse.sh  # → GGUF
```

Trên Kaggle chạy cùng `pipelines/training/train_hf.py`, không chạy Docker lồng trong
notebook. Xem hướng dẫn đầy đủ và cách nâng model 8B tại
[`docs/training.md`](docs/training.md). Xem graph qua API:

```bash
curl localhost:8000/api/graph/stats
curl 'localhost:8000/api/graph/trace?q=cao lau la mon gi'
curl 'localhost:8000/api/graph/subgraph?node=Huế'
```

## Tech stack

| Layer | Công nghệ | Vai trò |
|---|---|---|
| **Frontend** | Next.js 14, React 18, TypeScript | UI chat |
| **Backend** | FastAPI, Pydantic, Uvicorn | API, orchestration |
| **LLM runtime** | llama.cpp + GGUF | Sinh câu trả lời portable |
| **Retrieval** | BM25 tự viết + RRF + networkx | Lấy context, xếp lại theo graph |
| **Fine-tune** | Transformers + PEFT LoRA FP16/BF16 | Văn phong + trích dẫn + cách từ chối |
| **Corpus** | Wikipedia VN (Huế, Đà Nẵng) | 45 bài dùng được / 349 chunk |

## Đánh giá

Hai nửa của độ chính xác `P(đúng) = P(lấy đúng đoạn) × P(model trung thực)`:

```bash
# Nửa trên - retrieval (không cần model, chạy trong 1 giây)
python pipelines/evaluation/eval_attribution.py

# Nửa dưới - model (cần gold set gán nhãn tay)
python pipelines/evaluation/make_gold_template.py
python pipelines/training/score_gold.py \
  --gold pipelines/evaluation/gold.jsonl --out pipelines/evaluation/report_lora.json
```

## Tài liệu

- [docs/architecture.md](docs/architecture.md) — kiến trúc, luồng dữ liệu, ba cổng từ chối
- [docs/chatbot.md](docs/chatbot.md) — kiến trúc chatbot chốt theo Microsoft GraphRAG + KAG
- [docs/metrics.md](docs/metrics.md) — 4 metric đánh giá
- [docs/demo-guide.md](docs/demo-guide.md) — hướng dẫn demo
- [docs/secrets-policy.md](docs/secrets-policy.md) — quy tắc `.env`, API key và secret cho local/Docker/Jenkins

## Chi phí

| Hạng mục | Chi phí |
|---|---|
| API | $0 |
| Điện | ~$0.10 |
| **Tổng** | **~$0.10** |
