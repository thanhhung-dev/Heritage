# HeritageGraph — Chatbot văn hóa Đà Nẵng – Huế

Hỏi đáp từ tài liệu di sản bằng **BGE-M3 + OpenSearch hybrid search + GGUF qua
llama.cpp**, phục vụ bởi FastAPI và Next.js.

README này là hướng dẫn vận hành kiến trúc hiện tại. Chạy các lệnh từ thư mục
gốc repository; mỗi terminal Python cần `source .venv/bin/activate`.

- [Cài đặt và chạy local](#chạy-local-trên-mac)
- [Ingest tài liệu từ R2](#ingest-tài-liệu-từ-r2)
- [Bảo trì và cập nhật dữ liệu](#bảo-trì-và-cập-nhật-dữ-liệu)
- [Chẩn đoán chậm và lỗi thường gặp](#chẩn-đoán-chậm-và-lỗi-thường-gặp)
- [Kiểm tra](#kiểm-tra)

## Luồng hiện tại

```text
INGESTION (offline)
Tài liệu R2 → tải/trích text → chuẩn hóa/chia chunk → BGE-M3
                                                   ↓
                              OpenSearch: text + vector + metadata
                                                   ↑
Q&A                                                │
User → Next.js → FastAPI → BGE-M3 embed câu hỏi → hybrid BM25 + vector
                                                   ↓
                              chọn chunk → ghép prompt → llama.cpp → answer + nguồn

Tùy chọn: OpenSearch → export snapshot → Microsoft GraphRAG index (offline)
          Q&A → GraphRAG global query → đối chiếu chunk gốc → bổ sung context
```

Chat không tải text từ R2 hoặc quét PostgreSQL để dựng index trong mỗi process.
OpenSearch sở hữu BM25, vector index và hợp nhất điểm hybrid. Bộ retrieval/KG
cũ và các script chỉ phục vụ nó đã được xóa, không giữ hai đường search song song.
Các số benchmark BM25/KG cũ **không phải kết quả của kiến trúc mới**.

## Chạy local trên Mac

Yêu cầu Python 3.12, Node 20, Docker Compose v2 và llama.cpp native (Metal).
Docker **chỉ chạy OpenSearch**; chưa chạy OpenSearch Dashboards hoặc Langfuse.
Model và dữ liệu không nằm trong Git, cần chuẩn bị riêng.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r apps/backend/requirements.txt -r pipelines/ingestion/requirements.txt
test -f .env || cp .env.example .env
docker compose up -d opensearch
curl -fsS 'http://127.0.0.1:9200/_cluster/health?wait_for_status=yellow&timeout=30s'
```

Nếu chưa có llama.cpp native, cài bằng `brew install llama.cpp`.
Kiểm tra các giá trị trong `.env`:

```dotenv
OPENSEARCH_URL=http://127.0.0.1:9200
OPENSEARCH_INDEX=heritage-passages-v1
INFERENCE_BACKEND=llama_server
LLAMA_SERVER_URL=http://127.0.0.1:8080
LANGFUSE_ENABLED=false
OTEL_TRACING_ENABLED=false
GRAPHRAG_ENABLED=false
DATABASE_URL=
```

Để `DATABASE_URL=` nếu chỉ chạy chat; DB nghiệp vụ là tùy chọn, không nằm trong
Compose mới. API nghiệp vụ cần PostgreSQL riêng và trả 503 nếu chưa cấu hình.
Không reset database/volume cũ. Backend đọc `.env` khi khởi động; biến đã export
trong shell được ưu tiên hơn `.env`. Sau khi đổi cấu hình, restart backend.

Chuẩn bị `models/qwen-fused.gguf` rồi chạy trong terminal riêng:

```bash
llama-server --model models/qwen-fused.gguf --host 127.0.0.1 --port 8080 \
  --ctx-size 4096 --parallel 1 --n-gpu-layers 99 \
  --chat-template-kwargs '{"enable_thinking":false}'
```

Native llama.cpp dùng Metal trên Mac; Docker Linux cũ không có Metal nên sinh
token trên CPU. Tên `qwen-fused.gguf` không bảo đảm model đã fine-tune: kiểm tra
file/symlink thực tế trước khi báo cáo chất lượng. Xem [training](docs/training.md).

Ingest tài liệu theo [hướng dẫn ingestion](docs/ingestion.md), sau đó chạy backend:

```bash
python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000
```

Frontend, terminal riêng:

```bash
test -f apps/frontend/.env.local || cp apps/frontend/.env.local.example apps/frontend/.env.local
npm --prefix apps/frontend ci
npm --prefix apps/frontend run dev
```

Frontend dùng `NEXT_PUBLIC_API_URL=http://localhost:8000` trong
`apps/frontend/.env.local`; restart frontend khi đổi biến này.

- Chat UI: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Model health: <http://localhost:8000/api/health> (không xác minh search index)
- OpenSearch: <http://localhost:9200> (local-only, security tắt; không public)

**Cổng 9200 là JSON API, không phải giao diện quản trị.** OpenSearch Dashboards
chưa có trong Compose nên chưa có UI ở cổng 5601. Các lệnh dưới đây dùng API
để xem dữ liệu; không cần cài Dashboards để ingestion hoặc chat hoạt động.

```bash
curl 'http://127.0.0.1:9200/_cat/indices?v'
curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Chùa Thiên Mụ xây năm nào?","use_rag":true}'
```

Lần embed đầu có thể tải BGE-M3 từ Hugging Face và nạp model vào RAM; cần Internet
cho lần tải đầu. Không đánh giá tốc độ chỉ bằng request cold-start này.

## Ingest tài liệu từ R2

### 1. Chuẩn bị nguồn

Upload tài liệu gốc lên R2 bằng công cụ quản lý R2 của bạn trước. Pipeline hiện
tại **không upload file, không tự liệt kê bucket**; nó tải các URL bạn khai báo.
Hỗ trợ TXT, Markdown, HTML và PDF có text; PDF scan phải OCR trước.

```bash
mkdir -p data/ingestion
test -f data/ingestion/sources.json || cp pipelines/ingestion/r2_sources.example.json data/ingestion/sources.json
```

Sửa `data/ingestion/sources.json`, ví dụ dưới đây là bản dữ liệu số 2:

```json
{
  "corpus_version": 2,
  "chunking": {"max_chars": 2400, "overlap_chars": 300},
  "documents": [
    {
      "url": "https://YOUR-R2-DOMAIN/knowledge/curated/thien-mu/lich-su.md",
      "object_key": "knowledge/curated/thien-mu/lich-su.md",
      "source_url": "https://YOUR-ORIGINAL-SOURCE/thien-mu",
      "title": "Lịch sử chùa Thiên Mụ",
      "region": "hue",
      "source_type": "official",
      "tier": 1,
      "observed_at": "2026-10-19T00:00:00Z"
    }
  ]
}
```

- `url`: link tải file trên R2. Với file riêng tư, thay `url` bằng
  `"url_env": "R2_DOCUMENT_URL"`, đặt signed URL vào biến môi trường của terminal
  chạy ingestion; không commit signed URL. CLI tải/chia chunk không tự đọc `.env`.
- `source_url`: trang nguồn để trích dẫn, phải không chứa query/secret và không
  trùng giữa các document. Đây không nhất thiết là link tải R2.
- `object_key`: đường dẫn object gốc trong R2, không phải URL.
- `title`: tên tài liệu, được dùng cùng text khi embed.
- Link không có đuôi file có thể khai báo thêm `"format": "pdf"` (hoặc `txt/md/html`).
- Nếu dùng `R2_BUCKET` trong `.env`, đặt đúng bucket nguồn trước khi import để
  metadata không trỏ sai. Q&A không cần credentials R2 để đọc chunk.

### 2. Tải, trích text và chia chunk

```bash
python -m pipelines.ingestion.ingest_r2 --config data/ingestion/sources.json
```

Kết quả ở `data/ingestion/corpus-v2/`: file gốc, passage JSON, `package.json`,
`manifest.json` và checksum. Chunk là **đoạn text thông thường**, không phải hash;
vector là trường riêng được tạo ở bước sau. Mặc định tối đa 2400 ký tự/chunk,
overlap mục tiêu 300 ký tự, ưu tiên ranh giới đoạn/câu/từ.

Mở package kiểm tra text, dấu tiếng Việt, tên tài liệu và nguồn trước khi index.
Output giữ nguyên khi chạy lại cùng input; nếu nội dung/config thay đổi, tăng
`corpus_version` và dùng thư mục output mới. Không sửa đè một release đã review.

### 3. Embed và import vào index mới

Ví dụ bản dữ liệu số 2 dùng index `heritage-passages-v2`:

```bash
OPENSEARCH_INDEX=heritage-passages-v2 python -m apps.backend.db.import_passages \
  data/ingestion/corpus-v2/package.json --env-file .env

curl -fsS 'http://127.0.0.1:9200/heritage-passages-v2/_count?pretty'
curl -fsS -X POST 'http://127.0.0.1:9200/heritage-passages-v2/_search?pretty' \
  -H 'Content-Type: application/json' \
  -d '{"size":2,"_source":["id","text","location_note","source_url","object_key"],"query":{"match_all":{}}}'
```

Importer tự tạo mapping + hybrid search pipeline, embed BGE-M3 1024 chiều và lưu
text/vector/metadata. Không phải tạo index bằng tay. Tên module `db.import_passages`
được giữ cho CLI, nhưng **không ghi PostgreSQL hay R2**.

Import cùng package vào cùng index là upsert theo ID ổn định, không tạo bản sao.
Nếu bulk lỗi có thể đã ghi thành công một phần: sửa lỗi rồi chạy lại cùng lệnh.
`release_status: draft` không chặn import; việc review là trách nhiệm vận hành.

### 4. Chuyển Q&A sang bản dữ liệu mới

Đổi `OPENSEARCH_INDEX=heritage-passages-v2` trong `.env`, restart backend, rồi chạy
smoke `/api/chat` như trên. Kiểm tra cả câu trả lời và nguồn; count/search thành
công chưa chứng minh câu trả lời đúng. Giữ index cũ để có thể rollback.

Xem [ingestion chi tiết](docs/ingestion.md) cho migration vector có sẵn và GraphRAG.

## Bảo trì và cập nhật dữ liệu

### Mỗi lần thêm, sửa hoặc bỏ tài liệu

1. Cập nhật danh sách nguồn đầy đủ cho release mới, tăng `corpus_version`.
2. Chạy tải/chia chunk, review package, import **toàn bộ release** vào index mới.
3. Kiểm tra số passage, text/metadata và Q&A rồi chuyển `.env` + restart backend.
4. Giữ package/manifest và index trước đó tới khi chấp nhận bản mới.

**Importer không tự xóa chunk cũ**. Chỉ upsert tài liệu đã sửa vào index đang
phục vụ có thể để lại cả nội dung cũ lẫn mới. Muốn bỏ tài liệu, loại nó khỏi danh
sách nguồn rồi rebuild index mới từ toàn bộ tài liệu còn lại. Không chỉ import
phần thay đổi vào một index trống: như vậy sẽ mất các tài liệu không nằm trong batch.

Rollback: đặt lại tên index cũ trong `.env`, restart backend và kiểm tra chat.
Không cần tải lại R2 hay embed lại nếu index cũ còn nguyên. Nếu đã bật GraphRAG,
re-export/index theo release mới và cấu hình đúng `GRAPHRAG_ROOT`; có thể tắt
GraphRAG trong lúc chuyển bản để không dựa vào snapshot lỗi thời.

### Kiểm tra tài nguyên và dữ liệu

```bash
docker compose ps
docker stats --no-stream heritagegraph-opensearch-1
docker compose logs --tail=100 opensearch
curl -fsS 'http://127.0.0.1:9200/_cluster/health?pretty'
curl -fsS 'http://127.0.0.1:9200/_cat/indices?v'
curl -fsS 'http://127.0.0.1:9200/_cat/allocation?v'
```

OpenSearch local có heap 512 MiB, giới hạn RAM 2 GiB và 2 CPU. Cấu hình single-node
này không phải HA/production. Theo dõi thêm Memory Pressure/Swap trong Activity
Monitor vì BGE-M3 và llama.cpp dùng chung RAM/GPU trên Mac.

### Lưu trữ và backup

- Giữ tài liệu gốc R2, config nguồn đã loại secret, package/manifest từng release,
  phiên bản code/model và tên index đang phục vụ. Bảo vệ cả dữ liệu tải về local;
  không commit tài liệu riêng tư hoặc `.env` vào Git.
- Volume `heritagegraph_opensearch_data` giữ index sau khi dừng container, nhưng
  **volume trên cùng máy không phải backup**. Nếu mất volume, có thể rebuild từ
  package đã lưu bằng importer; sẽ tốn thời gian embed lại.
- Chưa có backup OpenSearch tự động trong Compose. Trước khi triển khai dữ liệu
  quan trọng, cần cấu hình snapshot repository/backup độc lập và thử restore.
- Không chạy `docker compose down -v`, volume prune hoặc xóa database cũ để
  “dọn nhẹ máy”. Chỉ xóa index/release cũ sau khi xác nhận backup và rollback;
  hướng dẫn này không tự thực hiện thao tác xóa dữ liệu.

### Dừng và chạy lại hằng ngày

Dừng backend, frontend và llama-server bằng `Ctrl+C` ở terminal tương ứng;
`docker compose stop opensearch` dừng search nhưng giữ volume. Lần sau chạy
`docker compose up -d opensearch`, rồi khởi động lại llama-server, backend và
frontend theo phần local. **Không cần ingest lại mỗi lần bật máy.**

## Chẩn đoán chậm và lỗi thường gặp

| Hiện tượng | Kiểm tra / cách xử lý |
| --- | --- |
| Lần hỏi đầu chậm | BGE tải/nạp model lần đầu; so sánh lần cold với các lần warm, không restart backend giữa mỗi câu. |
| Máy nóng, swap tăng | Kiểm tra Activity Monitor và `docker stats`; tránh ingest/GraphRAG cùng lúc chat, dừng container legacy sau khi xác định đúng service. Không chạy nhiều backend worker trên máy ít RAM vì mỗi process có thể nạp BGE riêng. |
| Sinh answer chậm | Xem log terminal llama-server về Metal và tốc độ prompt/token generation. Chạy native, không dùng image Linux cũ trên Mac. OpenSearch nhanh hơn không làm bước sinh token tự nhanh hơn. |
| Không có nguồn hoặc search lỗi | Kiểm tra `_count`, tên `OPENSEARCH_INDEX`, OpenSearch health và import đã thành công. `/api/health` không kiểm tra index. Không tạo index thủ công thiếu mapping/pipeline. |
| Import lỗi sau khi đổi embedding | Tạo index mới và embed lại; không trộn model/vector khác phiên bản hoặc dimension. |
| Tải R2 lỗi | Kiểm tra quyền/link hết hạn/format file trong bước ingestion. Chat đọc text từ OpenSearch nên không tải lại file R2 để trả lời; link nguồn/media có thể vẫn cần R2 khi người dùng mở. |
| Đã sửa `.env` nhưng chưa đổi hành vi | Restart backend; kiểm tra biến shell cũ đang override `.env`. CLI import cần truyền `--env-file .env`. |

Để đo thời gian toàn request sau khi các service sẵn sàng:

```bash
curl -sS -o /tmp/heritage-chat-response.json -w 'HTTP %{http_code} — total %{time_total}s\n' \
  -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Chùa Thiên Mụ xây năm nào?","use_rag":true}'
cat /tmp/heritage-chat-response.json
```

Đây là tổng thời gian, không tách embedding/search/generation. Muốn kết luận
nút thắt, cần đối chiếu log và đo từng bước; không mặc định R2 hay search là nguyên
nhân. Hiện chưa có dashboard báo cáo latency/capacity tự động; `/internal/metrics`
là endpoint metrics, không phải UI và không thay thế benchmark tải thực tế.

## GraphRAG và phạm vi thay đổi

Microsoft GraphRAG vẫn là tùy chọn, mặc định `GRAPHRAG_ENABLED=false`. Export từ
OpenSearch rồi index trong `.venv-graphrag` riêng trước khi bật; xem
[ingestion](docs/ingestion.md). Global query có thêm lượt gọi LLM nên không phải
đường nhanh cho mọi câu hỏi. Graph chỉ bổ sung khi lineage còn khớp nguồn gốc.

Retrieval mới giữ tối đa 2 chunk nguyên vẹn trong 4800 ký tự. Các bộ sửa tên/gate
entity và reranker Python cũ không còn chạy trong chat; cần đánh giá lại gold set,
đặc biệt typo, câu ngoài miền và câu quan hệ. Điểm hybrid không phải xác suất đúng.
Không có chunk thì từ chối; có chunk không có nghĩa factual grounding đã được kiểm chứng.

## Kiểm tra

```bash
OPENSEARCH_TEST_URL=http://127.0.0.1:9200 LANGFUSE_ENABLED=false \
  python -m unittest apps.backend.tests.test_opensearch \
  apps.backend.tests.test_passages apps.backend.tests.test_chat_api \
  apps.backend.tests.test_chat_graphrag apps.backend.tests.test_microsoft_graphrag \
  apps.backend.tests.test_startup_config apps.backend.tests.test_db_init \
  apps.backend.tests.test_docker_database apps.backend.tests.test_r2_ingestion
```

Search integration tests dùng index tạm `heritage-test-*`; không sửa index phục vụ.
Benchmark model và toàn bộ Q&A phải chạy riêng với model/dữ liệu thật.

## Tài liệu và công cụ offline

- [Docker local](docs/docker-local.md) — giới hạn tài nguyên, volume và bảo mật.
- [Ingestion](docs/ingestion.md) — R2, chunk, import OpenSearch, chuyển dữ liệu cũ.
- [Training](docs/training.md) — Transformers + PEFT LoRA, export GGUF;
  profile `trainer` không còn trong Compose mặc định.
- `apps/backend/core/corpus.py` giữ chunking cho ingestion và loader corpus training;
  `core/kg.py` chỉ giữ trích tên/năm cho NER, không còn dựng/truy hồi graph.
- `pipelines/evaluation/eval_answers.py`, `eval_graphrag_chat.py` đánh giá qua API
  hiện tại. Các script retrieval/graph/alias legacy và generator phụ thuộc chúng
  đã bị loại bỏ. Các hướng dẫn lịch sử nhắc tới chúng không còn chạy được.
- [Metrics](docs/metrics.md), [secrets policy](docs/secrets-policy.md).
- [Architecture](docs/architecture.md), [chatbot design](docs/chatbot.md) và
  [demo guide](docs/demo-guide.md) là tài liệu thiết kế/luồng cũ, chưa phải
  hướng dẫn vận hành OpenSearch hiện tại; ưu tiên README và hai hướng dẫn trên.
