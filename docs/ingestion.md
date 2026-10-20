# Ingestion R2 → BGE-M3 → OpenSearch

## 1. Chuẩn bị và chia chunk

```bash
pip install -r apps/backend/requirements.txt -r pipelines/ingestion/requirements.txt
mkdir -p data/ingestion
cp pipelines/ingestion/r2_sources.example.json data/ingestion/sources.json
python -m pipelines.ingestion.ingest_r2 --config data/ingestion/sources.json
```

Config có `corpus_version` nguyên dương và `documents`: mỗi nguồn có link tải
`url` (hoặc `url_env` cho signed URL), `object_key`, `source_url`, `title`, `region`,
`source_type`, `tier`, `observed_at`. Không commit signed URL/secret. `source_url`
phải là URL nguồn để trích dẫn, không chứa query/secret. Không tự scan bucket.

Hỗ trợ TXT/Markdown/HTML/PDF có text; PDF scan/ảnh cần OCR trước. Text được chuẩn
hóa Unicode rồi chia tối đa 2400 ký tự, overlap mục tiêu 300, ưu tiên đoạn/câu/từ.
Các offset tính trên text chuẩn hóa, không phải byte PDF gốc.

Output mặc định `data/ingestion/corpus-vN/` gồm raw bytes, passage JSON,
`package.json`, `manifest.json` và checksum. Bước này chỉ tải/ghi local, không
gọi embedding, không upload R2, không ghi DB. Review text và metadata trước import.
Cùng input/config có cùng output; nội dung thay đổi phải dùng version/output mới.

## 2. Embed và index vào OpenSearch

```bash
docker compose up -d opensearch
python -m apps.backend.db.import_passages \
  data/ingestion/corpus-v2/package.json --env-file .env
```

Tên module được giữ cho CLI, nhưng importer **không còn dùng PostgreSQL**.
Importer validate batch, tạo embedding BGE-M3 1024 chiều, rồi upsert vào
`OPENSEARCH_INDEX` (mặc định `heritage-passages-v1`). Index lưu nguyên văn chunk,
vector, phiên bản embedding, tên tài liệu, source URL và mapping nguồn R2.
BM25 có analyzer lowercase/asciifolding và chuẩn hóa đ/d để tìm không dấu.
Hybrid search dùng normalization pipeline của OpenSearch, không RRF/BM25 Python.

Đây là thao tác đưa dữ liệu đã review vào index đang phục vụ; trường `draft`
của package local **không phải release gate của OpenSearch**. Nếu cần review
staging, import vào một `OPENSEARCH_INDEX` riêng rồi chuyển cấu hình sau review.

ID dùng `key` của passage trong package hoặc ID ổn định từ nguồn/vị trí/nội dung.
Import lại cùng input không tạo bản sao. Import là upsert, **không tự xóa chunk
cũ đã bỏ khỏi tài liệu**; với release mới, dùng index mới rồi chuyển cấu hình.
Bulk có thể thành công một phần khi server lỗi; CLI trả lỗi, không báo atomic.
Sửa lỗi và chạy lại cùng input để hoàn tất an toàn.

Q&A đọc text trực tiếp từ OpenSearch, **không cần R2 credentials hay DATABASE_URL**.
R2 vẫn lưu tài liệu gốc; không cần upload thêm từng passage để chat hoạt động.

## 3. Chuyển dữ liệu đã có

Không xóa database/volume cũ. Export các passage với text đã xác minh, ID, vector
và `embedding_model`. Với export tin cậy có cùng đúng phiên bản BGE-M3:

```bash
python -m apps.backend.db.import_passages data/migration/passages.json \
  --env-file .env --reuse-embeddings
```

Flag này bỏ qua inference và kiểm tra model ID/dimension/vector hữu hạn; nó không
tự xác minh vector có thật sự được tạo từ text hay không. Không dùng với payload
không tin cậy. Cách mặc định luôn embed lại text bằng model được pin trong code.

## 4. Microsoft GraphRAG tùy chọn

```bash
python -m pipelines.graph.microsoft_graphrag export \
  --root graphrag/runs/opensearch-v1 --env-file .env --limit 1000
.venv-graphrag/bin/python -m pipelines.graph.microsoft_graphrag index \
  --root graphrag/runs/opensearch-v1 --env-file .env
```

Export lấy text từ OpenSearch, giữ ID/hash/mapping trong manifest. Không đọc R2
hoặc PostgreSQL. Index cần môi trường GraphRAG riêng và LLM đã sẵn sàng; chỉ bật
`GRAPHRAG_ENABLED=true`, đặt `GRAPHRAG_ROOT` sau khi có `index-ready.json`.
Runtime chỉ nhận graph source còn khớp ID/hash/mapping và graph context có đủ
chunk gốc được chọn. Snapshot cũ giữ nguyên; re-export/index nếu nguồn đã đổi.

## 5. Test

```bash
OPENSEARCH_TEST_URL=http://127.0.0.1:9200 LANGFUSE_ENABLED=false \
  python -m unittest apps.backend.tests.test_opensearch \
  apps.backend.tests.test_passages apps.backend.tests.test_chat_graphrag \
  apps.backend.tests.test_r2_ingestion
```

Integration tests chỉ tạo/xóa index có tên ngẫu nhiên `heritage-test-*`, không
ghi R2/PostgreSQL và không dùng model thật. Chạy smoke Q&A riêng với BGE/LLM thật
trước khi công bố chất lượng/tốc độ của hệ thống.
