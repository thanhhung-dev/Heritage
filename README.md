# HeritageGraph — Chatbot văn hóa Đà Nẵng – Huế

Chatbot hỏi đáp về di sản, ẩm thực và nghệ thuật **Đà Nẵng – Huế**, chạy 100% local.

- **Retrieval**: BM25 theo từ + BM25 theo n-gram (chịu được gõ không dấu) hợp nhất
  bằng RRF, mở rộng và xếp lại bằng **knowledge graph dựng deterministic** — không
  gọi LLM lúc index, không Ollama, không vector DB (`backend/core/kg.py`).
- **LoRA fine-tune**: Hugging Face Transformers + PEFT FP16/BF16, chạy CUDA Docker/Kaggle
- **Backend**: FastAPI · **Frontend**: Next.js
- **Không cần API key, không cần internet** sau khi crawl xong corpus.

Đo được hiện tại: trong phạm vi `68/70`, paraphrase `9/39`, bằng chứng `34/34`,
ngoài phạm vi `31/38` bằng `eval/eval_attribution.py`; graph 510 node / 1135
edge, dựng hết 0.23 giây.

## Cấu trúc

```
HeritageGraph/
├── ingestion/
│   ├── crawl_by_location.py      # crawl theo 49 địa điểm curated (đang dùng)
│   ├── crawl_wiki_mientrung.py   # crawl rộng theo category (bản cũ)
│   └── chunk_corpus_mt.py
├── corpus/
│   ├── wiki_by_location/*.txt
│   └── locations_index.json      # 25 crawl được / 24 chưa
├── backend/
│   ├── app.py
│   ├── api/{chat,health,graph}.py
│   └── core/
│       ├── corpus.py             # đọc + chunk (DÙNG CHUNG train & serve)
│       ├── textutil.py           # chuẩn hoá tiếng Việt, bỏ dấu, n-gram
│       ├── kg.py                 # knowledge graph deterministic
│       ├── retriever.py          # BM25 x2 + RRF + graph
│       ├── rag.py                # chọn context + ba cổng từ chối
│       └── llm.py                # Qwen+LoRA inference
├── training/
│   ├── bootstrap_deep_qa.py      # sinh training data (đang dùng)
│   ├── train_hf.py, lora_config.yaml, Dockerfile
│   └── score_gold.py
├── eval/
│   ├── eval_retrieval.py         # đo recall + tỉ lệ từ chối (không cần model)
│   └── make_gold_template.py
├── scripts/
│   ├── build_graph.py            # xây / xem graph, truy dấu câu hỏi
│   ├── run_indexing.sh           # wrapper của build_graph.py
│   └── start_dev.sh
├── frontend/                     # Next.js (chưa hoàn thiện)
├── data/                         # train.jsonl + valid.jsonl
├── models/                       # peft-adapter/ + qwen-fused.gguf
└── docs/
```

## Quick start

### Bước 0: Setup

```bash
cd ~/CAP/HeritageGraph
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt

cd frontend && npm install && cd ..
```

Không cần Ollama và không cần package `graphrag`: graph được xây bằng
`backend/core/kg.py`, hoàn toàn deterministic.

### Bước 1: Crawl corpus (~10 phút)

```bash
backend/.venv/bin/python ingestion/crawl_by_location.py
```

Kết quả ghi vào `corpus/wiki_by_location/` + `corpus/locations_index.json`.

### Bước 2: Xây + kiểm tra graph (~1 giây)

```bash
bash scripts/run_indexing.sh                                   # thống kê + xuất artifact
backend/.venv/bin/python scripts/build_graph.py --node "triều Nguyễn"
backend/.venv/bin/python scripts/build_graph.py --query "lăng Minh Mạng xây năm nào"
backend/.venv/bin/python eval/eval_attribution.py              # retrieval + quy trách nhiệm lỗi
```

Artifact ra `graphrag/output/`: `graph.gexf` (mở bằng Gephi), `graph.json`
(node-link cho frontend), `stats.json`.

### Bước 3: Train LoRA

```bash
backend/.venv/bin/python training/bootstrap_deep_qa.py   # sinh data/train.jsonl + valid.jsonl
docker compose --profile training run --rm trainer       # Linux có NVIDIA GPU
docker compose --profile training run --rm trainer bash training/eval.sh
docker compose --profile training run --rm trainer bash training/fuse.sh  # → GGUF
```

Trên Kaggle chạy cùng `training/train_hf.py`, không chạy Docker lồng trong
notebook. Xem hướng dẫn đầy đủ và cách nâng model 8B tại
[`docs/training.md`](docs/training.md).

### Bước 4: Chạy app

```bash
docker compose up -d llm          # llama.cpp tại localhost:8080
backend/.venv/bin/uvicorn backend.app:app --port 8000
cd frontend && npm run dev      # terminal khác → http://localhost:3000
```

Hoặc `bash scripts/start_dev.sh`. Xem graph qua API (không cần model đã fuse):

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
backend/.venv/bin/python eval/eval_attribution.py

# Nửa dưới - model (cần gold set gán nhãn tay)
backend/.venv/bin/python eval/make_gold_template.py
backend/.venv/bin/python training/score_gold.py \
  --gold eval/gold.jsonl --out eval/report_lora.json
```

## Tài liệu

- [docs/architecture.md](docs/architecture.md) — kiến trúc, luồng dữ liệu, ba cổng từ chối
- [docs/chatbot.md](docs/chatbot.md) — kiến trúc chatbot chốt theo Microsoft GraphRAG + KAG
- [docs/metrics.md](docs/metrics.md) — 4 metric đánh giá
- [docs/demo-guide.md](docs/demo-guide.md) — hướng dẫn demo

## Chi phí

| Hạng mục | Chi phí |
|---|---|
| API | $0 |
| Điện | ~$0.10 |
| **Tổng** | **~$0.10** |
