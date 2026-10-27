# Kiến trúc chatbot HeritageGraph

Ngày cập nhật: 04/10/2026.

## 1. Mục tiêu và quyết định kiến trúc

HeritageGraph dùng kiến trúc **R2-backed Domain GraphRAG/KAG-lite**:

- **Cloudflare R2 là kho tri thức bền vững**: giữ tài liệu gốc, nội dung đã biên
  soạn, passage đã xử lý và manifest theo phiên bản;
- **search index là projection có thể dựng lại**: giữ vector, lexical index,
  metadata lọc và `object_key`, không phải nguồn sự thật của nội dung;
- **PostgreSQL là kho nghiệp vụ**: giữ entity, claim, relation, timeline, trạng
  thái ingestion, corpus release, hội thoại, cache và audit;
- MVP có thể dùng PostgreSQL + pgvector làm search index để giảm hạ tầng, nhưng
  nội dung chuẩn vẫn nằm trên R2 và index phải có thể dựng lại;
- khi quy mô vượt khả năng một PostgreSQL, chuyển search index sang OpenSearch,
  Qdrant, Pinecone, Weaviate hoặc Milvus mà không đổi cấu trúc tri thức trên R2;
- Qwen3-4B local chỉ tổng hợp evidence, không làm kho kiến thức hoặc search engine.

R2, search index và PostgreSQL không phải ba bản sao ngang hàng. Mỗi lớp có một
trách nhiệm khác nhau:

| Lớp | Nguồn sự thật cho | Không chịu trách nhiệm |
|---|---|---|
| R2 | Nội dung và phiên bản corpus | Semantic/keyword search trực tiếp |
| Search index | Tìm candidate passage nhanh | Lưu bản gốc duy nhất |
| PostgreSQL | Nghiệp vụ, graph, trạng thái và cache | Lưu mọi file crawl/binary |
| Qwen | Diễn đạt câu trả lời từ evidence | Tự bổ sung hoặc tự xác minh tri thức |

## 2. Kiến trúc tổng thể

```text
                         OFFLINE — KNOWLEDGE PIPELINE

Nguồn web / PDF / tài liệu biên soạn
                 │
                 ▼
      R2 raw/ — bản gốc bất biến
                 │
                 ▼
 Trích text → làm sạch → chia passage → embedding
                 │
        ┌────────┴─────────┐
        ▼                  ▼
R2 curated/processed/   PostgreSQL
text + manifest         entity/claim/relation/
theo corpus version     timeline/job/release
        │                  │
        └────────┬─────────┘
                 ▼
        Search index có thể dựng lại
        vector + lexical + object_key
                 │
                 ▼
             Publish version


                           ONLINE — QA SOLVER

User → Query cache → Normalize → Resolve entity → Query planner
          │ hit                                      │
          ▼                         ┌─────────────────┼───────────────┐
       Trả cache                    ▼                 ▼               ▼
                              Exact/Graph       Vector/keyword    Section
                              PostgreSQL         search index     operator
                                   └─────────────────┬───────────────┘
                                                     ▼
                                       Lấy top object_key/passages
                                                     ▼
                                      Fetch 3–8 evidence từ R2
                                                     ▼
                                         Evidence Context Builder
                                                     ▼
                                                Qwen3-4B
                                                     ▼
                                          Citation/Grounding Gate
                                           ├── answered
                                           ├── clarify
                                           └── abstained
```

Runtime **không quét toàn bộ R2 cho mỗi câu hỏi**. Nếu search index không có kết
quả, solver phải `abstain` hoặc báo corpus chưa được xử lý; nó không fallback sang
việc tải hàng loạt object. File mới chỉ phục vụ chatbot sau khi ingestion và
publish index hoàn tất.

## 3. Tổ chức kho tri thức trên R2

R2 không có thư mục thật; các đường dẫn dưới đây là object key dùng prefix để mô
phỏng cây thư mục. Tên key dùng chữ thường, không dấu và dấu gạch ngang.

```text
knowledge/
├── raw/
│   └── web/2026/hue-gov-vn/<content-hash>.html
├── curated/
│   └── vi/
│       ├── hue/do-an/dia-diem/chua-thien-mu/
│       │   ├── tong-quan/<content-hash>.md
│       │   ├── kien-truc/<content-hash>.md
│       │   ├── lich-su/<content-hash>.md
│       │   ├── co-vat/<content-hash>.md
│       │   ├── le-hoi/<content-hash>.md
│       │   └── nhan-vat-lien-quan/<content-hash>.md
│       └── nhan-vat/nguyen-hoang/
│           ├── tieu-su/<content-hash>.md
│           └── di-san-lien-quan/<content-hash>.md
└── processed/
    └── corpus-v1/
        ├── passages/<document-id>/<passage-id>.json
        └── manifest.json
```

Ba namespace có ý nghĩa cố định:

- `raw/`: HTML, PDF, DOCX, JSON, ảnh hoặc text crawl nguyên bản; không sửa tại chỗ;
- `curated/`: Markdown đã được người biên soạn tổng hợp và review;
- `processed/`: passage, metadata và manifest do pipeline tạo; luôn gắn phiên bản.

Mỗi phiên bản nội dung dùng một key chứa content hash và không bị overwrite. Có
thể duy trì `latest.json` thân thiện cho người biên soạn, nhưng manifest release
chỉ được trỏ tới key bất biến. Tiểu sử đầy đủ của nhân vật có canonical key riêng;
chủ đề `nhan-vat-lien-quan` trong địa điểm chỉ mô tả vai trò của nhân vật tại địa
điểm đó để tránh sao chép tiểu sử.

Bucket phải private. Backend lưu `object_key`, không lưu public URL cố định; khi
cần cho người dùng tải nguồn thì cấp signed URL có thời hạn. Đổi tên key được xem
là copy sang key mới, cập nhật manifest/mapping rồi mới xóa key cũ.

## 4. Document, passage và mapping

### 4.1 Document

Một document là một nguồn độc lập: URL web, PDF, Markdown biên soạn hoặc hồ sơ.
Metadata tối thiểu:

```json
{
  "document_id": "DOC-000101",
  "title": "Lịch sử chùa Thiên Mụ",
  "source_url": "https://example.org/source",
  "object_key": "knowledge/curated/vi/hue/do-an/dia-diem/chua-thien-mu/lich-su/<content-hash>.md",
  "content_hash": "sha256:...",
  "source_type": "official",
  "language_code": "vi",
  "corpus_version": 1
}
```

`object_key + content_hash + corpus_version` xác định chính xác nội dung đã được
lập chỉ mục. Search hit thuộc phiên bản khác phiên bản đang publish không được đưa
vào context.

### 4.2 Passage

Passage là đoạn nhỏ lấy từ document và là đơn vị retrieval, citation, extraction
và provenance. Chunker ưu tiên ranh giới heading → đoạn → câu, không cắt cứng theo
số ký tự.

Cấu hình khởi đầu để đo bằng eval:

- mục tiêu 400–700 token, tối đa khoảng 800 token;
- overlap 50–120 token, khoảng 10–20%;
- giữ heading và thông tin nguồn cùng passage;
- bảng giữ header với các dòng liên quan;
- không dùng ranh giới trang PDF làm ranh giới ngữ nghĩa.

Khi một hit nằm sát ranh giới, retriever có thể lấy passage trước/sau theo
`document_id + passage_index`, sau đó gộp và loại phần overlap trùng. Không luôn
lấy `±1` vì sẽ lãng phí token budget.

Target lưu trữ passage:

```json
{
  "passage_id": "PSG-000305",
  "document_id": "DOC-000101",
  "passage_index": 3,
  "heading": "Khởi dựng",
  "text": "...",
  "source_object_key": "knowledge/curated/.../lich-su.md",
  "passage_object_key": "knowledge/processed/corpus-v1/passages/DOC-000101/PSG-000305.json",
  "corpus_version": 1
}
```

Search index chỉ cần giữ `passage_id`, vector/lexical index, metadata lọc,
`passage_object_key` và phiên bản. `source_object_key` dùng để truy nguyên tài
liệu; `passage_object_key` dùng để fetch evidence online. Nếu passage được gom
thành shard, mapping thay bằng `shard_object_key + byte_start + byte_length` để
runtime đọc đúng byte range mà không tải và chia lại toàn bộ document. MVP được
phép giữ `passage.text` trong PostgreSQL để triển khai nhanh, nhưng đó là
projection có thể tái tạo từ R2, không phải bản gốc duy nhất.

## 5. Biên soạn nhiều nguồn và provenance

Không trộn nội dung nhiều website thành một văn bản rồi mất dấu nguồn. Mỗi URL là
một document riêng trong `raw/`; nội dung tổng hợp nằm trong `curated/` và phải
trỏ về passages nguồn.

```text
Source document D1 ──┐
                     ├──▶ Claim C1 ──▶ narrative lich-su.md
Source document D2 ──┘
```

Một claim có thể có nhiều evidence:

```text
claim_evidence
├── claim_id
├── passage_id
└── support_type: supports | contradicts
```

Nguồn mâu thuẫn không được ghi đè nhau. Claim canonical chỉ chuyển sang
`accepted` sau review; claim còn nghi vấn giữ `proposed` hoặc `disputed`. Context
Builder phải giữ đủ evidence để câu trả lời trình bày xung đột thay vì che giấu.

Thứ tự ưu tiên mặc định:

1. cơ quan quản lý, hồ sơ và văn bản chính thức;
2. nghiên cứu học thuật, sách chuyên khảo;
3. bảo tàng và trung tâm lưu trữ;
4. báo chí uy tín;
5. encyclopedia cộng đồng, blog và website du lịch.

LLM được phép đề xuất extraction hoặc bản nháp, nhưng không được tự publish claim,
relation hoặc narrative.

## 6. Knowledge pipeline và publish nhất quán

Pipeline chạy offline hoặc khi có tài liệu thay đổi:

1. Upload bản gốc vào `raw/`, tính hash và ghi metadata.
2. Trích text; chạy OCR nếu nguồn là ảnh/PDF scan.
3. Làm sạch Unicode, khoảng trắng, navigation, quảng cáo và nội dung lặp.
4. Biên soạn/review nội dung `curated/` khi cần tổng hợp nhiều nguồn.
5. Chia passage có overlap và tạo embedding.
6. Trích entity, alias, claim, event, relation cùng provenance.
7. Ghi passage vào `processed/corpus-vN/` và dựng search index staging.
8. Chạy validation, retrieval eval và kiểm tra object key tồn tại.
9. Tạo release descriptor trỏ tới immutable index build; trong một transaction
   PostgreSQL, ghi release published và CAS active-release pointer sang release mới.

Importer phải idempotent. `document_id` được xác định từ source identity ổn định,
không từ nội dung vì hai nguồn khác nhau có thể có cùng text. Derived artifact
được định danh bởi `document_id + content_hash + processing_config_digest`, trong
đó digest bao phủ extractor/OCR, cleaning, chunking, embedding model và dimension.
Thay đổi một document chỉ tái xử lý document đó; publish vẫn tạo corpus version
mới để runtime không trộn index cũ với object mới.

Publish qua R2, search service và PostgreSQL không thể là một transaction ACID.
Hệ thống dùng protocol activation có bù lỗi:

1. Upload tất cả object và release descriptor bất biến.
2. Build immutable index mang cùng `release_id` và `index_build_id`.
3. Verify object, manifest, graph snapshot và immutable index.
4. Trong một transaction PostgreSQL, ghi trạng thái published và CAS
   active-release pointer từ release cũ sang descriptor mới.

Nếu bước 1–4 lỗi, active pointer vẫn giữ release cũ; index mới và object mới trở
thành staging/orphan để job dọn sau, không được runtime đọc. Rollback chỉ cần CAS
pointer về descriptor cũ vì các index build và object đã publish đều bất biến.
Release cũ chỉ hết điều kiện rollback sau retention window và một lần diễn tập
rollback thành công.

Manifest tối thiểu chứa:

```json
{
  "release_id": "REL-000001",
  "corpus_version": 1,
  "processing_config_digest": "sha256:...",
  "embedding_model": "<model-id>",
  "embedding_dimension": 1024,
  "lexical_index_config": {"kind": "postgres-fts", "version": "v1"},
  "index_build_id": "IDX-000001",
  "documents": [{"document_id": "DOC-000101", "object_key": "...", "sha256": "...", "size": 123}],
  "passages": [{"passage_id": "PSG-000305", "document_id": "DOC-000101", "passage_object_key": "...", "sha256": "...", "size": 456}],
  "created_at": "2026-10-04T00:00:00Z"
}
```

Manifest thực tế tuân theo một JSON Schema được version hóa. Ngoài các trường
minh họa trên, schema phải giữ chunking config, source-to-processed mapping và
checksum của chính manifest để một release có thể verify/rebuild độc lập.

## 7. Search layer và chiến lược mở rộng

Search layer luôn là dữ liệu dẫn xuất và phải rebuild được từ manifest + objects
trên R2.

| Quy mô | Search layer | Nội dung đầy đủ |
|---|---|---|
| Pilot/MVP | PostgreSQL FTS + pg_trgm + pgvector | PostgreSQL projection hoặc fetch R2 |
| Nhiều địa điểm, traffic vừa | Qdrant cho vector + PostgreSQL FTS | R2 |
| Hybrid search lớn | OpenSearch vector + BM25/n-gram | R2 |
| Vector rất lớn | Milvus/Pinecone/Weaviate | R2 |

Không chọn công nghệ chỉ theo số document. Quyết định tách search dựa trên p95,
kích thước index, thời gian rebuild, tải đồng thời và chi phí vận hành.

Nếu search service chỉ giữ vector + mapping, hệ thống có semantic search nhưng
không có keyword search. Hybrid retrieval cần một inverted index từ text, dù có
thể tắt lưu `_source` và fetch nội dung cuối từ R2.

## 8. Runtime query, cache và consistency

### 8.1 Luồng truy vấn

1. Resolve active-release pointer đúng một lần và ghim `release_id`, corpus,
   manifest, graph snapshot và immutable `index_build_id` cho toàn bộ request.
2. Chuẩn hóa câu hỏi và resolve entity trong release đã ghim.
3. Tính cache key có `release_id`, model và prompt version.
4. Cache hit hợp lệ thì trả kết quả đã kiểm grounding.
5. Cache miss thì Query Planner chọn operator.
6. Search layer trả candidate `passage_id + passage_object_key + score`.
7. Backend fetch 3–8 passage mạnh nhất từ R2, có timeout và giới hạn byte.
8. Context Builder hợp nhất evidence từ search và PostgreSQL, loại trùng, kiểm
   release/version và cấp citation ID.
9. Qwen sinh câu trả lời; grounding gate kiểm tra rồi mới cache.

Exact, timeline và graph operator đọc PostgreSQL nhưng không trả claim/relation
trần cho model. Mỗi record phải có supporting `passage_id`; mapping của release
chuyển ID đó thành `passage_object_key` và trả cùng evidence contract với Text
operator. Record thiếu evidence trong release đang ghim không được serve.

Cache câu trả lời không thay thế retrieval index. Câu hỏi diễn đạt khác nhau có
thể dùng semantic cache, nhưng ngưỡng phải bảo thủ và cache key phải bao gồm:

```text
normalized_query hoặc question_embedding
entity_ids
release_id
model_version
prompt_version
```

Publish corpus mới làm cache cũ tự mất hiệu lực nhờ version, không cần xóa đồng
loạt trong transaction phân tán.

### 8.2 Query Planner

| Intent | Operator chính |
|---|---|
| `overview` | Local Context/Entity Dossier |
| `field` | Exact claim |
| `timeline` | Timeline |
| `relationship` | Graph tối đa 1–2 hop |
| `section` | Narrative + passages |
| `comparison` | Multi-operator |
| `open_text` | Hybrid vector/keyword |
| `out_of_scope` | Abstain |

Planner không phải autonomous agent. Exact claim không được thay bằng vector
search; graph traversal chỉ qua predicate allowlist; Text operator có thể hợp
nhất BM25, n-gram và vector bằng RRF rồi rerank.

## 9. Evidence Context Builder và grounding

Mọi operator trả cùng contract:

```json
{
  "evidence_id": "PSG-000305",
  "entity_id": "ENT-000012",
  "content": "...",
  "source_title": "Lịch sử chùa Thiên Mụ",
  "source_url": "https://example.org/source",
  "source_object_key": "knowledge/curated/.../lich-su.md",
  "corpus_version": 1,
  "retrieval_score": 0.92,
  "reason": "supports timeline event 1601"
}
```

Context Builder:

1. loại evidence và overlap trùng;
2. từ chối object/index khác corpus version;
3. ưu tiên tier nguồn và độ mới phù hợp;
4. giữ nguồn mâu thuẫn cần thiết;
5. chọn 3–8 evidence trong token budget;
6. cấp citation ID cho model.

Qwen chỉ nhận evidence đã chọn. Mọi khẳng định factual phải có citation; số và
ngày phải xuất hiện trong evidence; thiếu bằng chứng thì `clarify` hoặc `abstain`.
QA Solver không sửa corpus trong lúc trả lời.

## 10. Trạng thái lỗi và suy giảm

| Sự cố | Hành vi |
|---|---|
| R2 tạm thời lỗi, cache hit | Trả cache còn hạn và ghi rõ version |
| R2 lỗi, cache miss | Không sinh từ metadata rỗng; trả lỗi tạm thời/abstain |
| Search index lỗi | Không quét R2; trả degradation có quan sát được |
| Object key thiếu | Loại evidence, ghi lỗi integrity, không đưa cho Qwen |
| Version mismatch | Loại hit và cảnh báo deployment/index drift |
| Evidence không đủ | `clarify` hoặc `abstained` |
| Nguồn mâu thuẫn | Trình bày khác biệt và citation từng phía |

R2 và search index cần health check riêng. Dashboard theo dõi object thiếu,
passage không có mapping, index lag, ingestion failure và cache hit rate.

## 11. Bảo mật và chi phí

- Bucket private; credential chỉ cấp quyền tối thiểu theo service account.
- Ingestion có quyền ghi; runtime chatbot ưu tiên chỉ đọc.
- Không đưa secret hoặc signed URL còn hạn vào log/chat history.
- Giới hạn kích thước object, MIME type và checksum trước xử lý.
- Không tạo một object cực nhỏ cho mọi token; passage là đơn vị hợp lý ở pilot.
  Khi request count trở thành vấn đề, gom passage thành shard JSONL/Parquet và lưu
  mapping shard + offset/range.
- Không áp lifecycle xóa lên raw/curated/processed input của bất kỳ release nào
  còn được giữ hoặc còn nghĩa vụ provenance. Chỉ được hết hạn staging object chưa
  từng publish, multipart upload lỗi, cache artifact và release đã qua retention,
  đã export archive kiểm checksum và không còn reference.

## 12. Ánh xạ vào repository

| Trách nhiệm | Owner dự kiến |
|---|---|
| R2 client, signed URL | adapter mới trong `apps/backend/` |
| Ingestion orchestration | `pipelines/ingestion/` |
| Chunking dùng chung | `apps/backend/core/corpus.py` |
| Entity resolution | `apps/backend/services/kg.py` |
| Search adapter | interface core + adapter pgvector/OpenSearch/Qdrant |
| Query planner | module riêng trong `apps/backend/core/` |
| Evidence Context Builder | `apps/backend/core/rag.py` |
| Prompt | `apps/backend/core/prompt.py` |
| Qwen inference | `apps/backend/core/llm.py` |
| Chat/cache orchestration | `apps/backend/services/chat.py` |
| Metadata, graph, release, audit | SQLAlchemy/Alembic/PostgreSQL |
| Evaluation | `pipelines/evaluation/` + regression tests |

Endpoint `/api/chat` chỉ validate/serialize; không chứa SQL, R2 SDK, retrieval,
prompt hoặc citation validation trực tiếp. Core phụ thuộc port/interface, không
phụ thuộc SDK của Cloudflare hay search vendor.

## 13. Hiện trạng và đích chuyển đổi

Hiện trạng repository đã có PostgreSQL/pgvector, bảng `document`, `passage`,
`corpus_release` và retrieval từ database. Đây là **as-built**, không phải lý do
để PostgreSQL tiếp tục là nguồn nội dung duy nhất.

Đích chuyển đổi:

- bổ sung `object_key`, hash và storage metadata cho document/passage;
- upload raw/curated/processed content lên R2;
- coi `passage.text` trong PostgreSQL là projection có thể rebuild trong giai
  đoạn chuyển tiếp;
- thêm storage port để retrieval có thể fetch top passages từ R2;
- giữ search adapter thay thế được để tách khỏi PostgreSQL khi có số liệu cần tách.

Không xóa `passage.text` trước khi R2 ingestion, manifest, rollback và retrieval
eval chạy ổn định. Migration phải theo kiểu expand → backfill → verify → switch →
contract, không reset volume.

## 14. Roadmap triển khai

### Giai đoạn 0 — Chốt contract và baseline

**Deliverables**

- Chốt object-key convention, document/passage schema và corpus manifest.
- Đo baseline retrieval, p95, dung lượng database và kích thước corpus hiện tại;
  ghi ngân sách gate vào release policy.
- Chọn Chùa Thiên Mụ làm vertical slice đầu tiên.

**Gate:** một document, passage và citation có ID ổn định; test hiện tại chạy xanh;
baseline ghi đủ recall@1, citation coverage, p95 và error rate.

### Giai đoạn 1 — R2 làm kho tri thức

**Deliverables**

- Tạo bucket private, credential theo quyền và cấu hình môi trường.
- Upload cây `raw/` và `curated/` cho Thiên Mụ; chưa publish `processed/`.
- Thêm mapping `object_key`, `content_hash`, `corpus_version` và health check.
- Có lệnh kiểm tra toàn bộ object trong manifest tồn tại và đúng checksum.

**Gate:** 100% raw/curated object trong manifest tồn tại, đúng size/checksum và có
thể khôi phục package nguồn pilot chỉ từ R2.

### Giai đoạn 2 — Pipeline xử lý có thể tái lập

**Deliverables**

- Extract/OCR/clean/chunk/overlap/embedding theo một pipeline version.
- Import idempotent; reprocess một document không làm thay đổi ID document khác.
- Publish corpus version bằng activation protocol và rollback về version trước.
- Tạo mapping provenance tối thiểu từ claim/relation/narrative tới passage trước
  khi bất kỳ nội dung curated nào được phép serve.

**Gate:** chạy pipeline hai lần tạo cùng stable IDs, object checksums và config
digest; index có cùng ID/count và retrieval score trên bộ cố định không lệch quá
ngưỡng đã chốt ở Giai đoạn 0; rollback trả lại đúng release descriptor cũ.

### Giai đoạn 3 — Retrieval từ index + R2

**Deliverables**

- Search adapter trả `passage_id`, score và `passage_object_key`.
- Runtime fetch chỉ top evidence từ R2, có timeout, retry giới hạn và dedupe.
- Hybrid retrieval, neighbor expansion và citation contract có regression test.

**Gate:** recall@1 ≥95%, citation coverage 100%, không có factual claim thiếu
evidence trong bộ pilot; p95 đầu-cuối ≤8 giây; tắt R2 hoặc index cho ra degradation
đúng thiết kế, không hallucinate và không scan fallback.

### Giai đoạn 4 — Curation và provenance nhiều nguồn

**Deliverables**

- Workflow raw source → evidence → claim/relation/narrative đã review.
- Mở rộng mapping evidence tối thiểu từ Giai đoạn 2 thành workflow nhiều nguồn,
  hỗ trợ `supports | contradicts` và review conflict.
- Dashboard phát hiện claim mâu thuẫn, source thiếu và object orphan.

**Gate:** 100% factual answer pilot truy ngược được đến passage + source object;
mọi conflict fixture giữ citation của cả hai phía.

### Giai đoạn 5 — Cache và quan sát vận hành

**Deliverables**

- Exact/semantic cache gắn release/model/prompt version và TTL.
- Metrics cache hit, retrieval latency, R2 latency, index lag, abstention và lỗi
  grounding.
- Load test câu hỏi lặp, paraphrase và cache invalidation khi publish corpus mới.

**Gate:** 0 cache hit sai release trong test publish/rollback; p95 giữ ≤8 giây và
không tăng quá ngân sách so với baseline đã chốt ở Giai đoạn 0.

### Giai đoạn 6 — Mở rộng và tách search service khi cần

**Deliverables**

- Nhân pipeline sang Huế/Đà Nẵng và các địa điểm tiếp theo.
- Đo ngưỡng PostgreSQL theo index size, QPS, p95 và thời gian rebuild.
- Chỉ khi vượt ngưỡng, chạy shadow index trên OpenSearch/Qdrant, so sánh quality và
  latency trước cutover.

**Gate:** shadow index giữ recall/citation không thấp hơn gate Giai đoạn 3, đạt
ngân sách p95/error rate đã chốt; cutover/rollback không đổi API chatbot, corpus
R2 hoặc ID evidence.

## 15. Tiêu chí hoàn thành kiến trúc

- R2 là nơi có thể khôi phục toàn bộ nội dung và phiên bản corpus.
- Search index bị xóa vẫn dựng lại được mà không crawl lại Internet.
- PostgreSQL hỏng cache không làm mất tài liệu tri thức gốc.
- Runtime không quét R2 và không dùng Qwen để thay thế retrieval.
- Mọi hit search ánh xạ được tới object + checksum + corpus version hợp lệ.
- Passage xử lý đúng ranh giới, overlap và neighbor expansion qua kiểm thử.
- Claim/relation/narrative truy ngược được về một hoặc nhiều nguồn.
- Câu factual có citation; xung đột nguồn được trình bày; thiếu nguồn thì abstain.
- Search backend có thể đổi qua adapter mà không thay contract của QA Solver.

Kiến trúc chốt:

> **R2 versioned knowledge store → reproducible ingestion → replaceable hybrid
> search index → KAG-lite query planner → Evidence Context Builder → Qwen3-4B →
> grounding gate; PostgreSQL giữ graph, nghiệp vụ, trạng thái và cache.**

## 16. Langfuse local cho đánh giá chatbot

Stack quan sát chạy trong project `heritage-local`, profile `langfuse`, network
`langfuse` và năm volume riêng (PostgreSQL, ClickHouse data/logs, Redis, MinIO).
Không tạo lại, kết nối network hay dùng volume của PostgreSQL/OpenSearch nghiệp
vụ thuộc project `heritagegraph`. Chỉ web `127.0.0.1:3003` và S3
`127.0.0.1:9090` được publish; worker, database, Redis và console MinIO không
publish cổng. Truy cập UI tại **http://localhost:3003** trên chính máy chạy Docker.

### Cấu hình và credentials

Tham chiếu [Compose chính thức](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml):
web `docker.langfuse.com/langfuse/langfuse:4`, worker
`docker.langfuse.com/langfuse/langfuse-worker:4`, PostgreSQL `17`, ClickHouse
`25.12`, Redis `7`, MinIO `cgr.dev/chainguard/minio:latest`. Đây là các tag có thể
thay đổi; ghi lại image digest thực tế khi chốt một lượt đo, không tự pull nâng
phiên bản giữa lượt chạy.

Tạo file **`.amp/in/langfuse.env`** local (quyền `600`), không sửa `.env` hiện có,
không copy toàn bộ `.env.example` vào file này. Trước khi ghi file, bảo đảm
`/.amp/in/` nằm trong Git exclude local (`git rev-parse --git-path info/exclude`);
không commit credentials hoặc nội dung trace. File chỉ cần các biến Langfuse và
cấu hình capture dành riêng cho lượt đánh giá. Không bật shell tracing (`set -x`),
không in file hoặc chạy `docker compose config` không có `--quiet`.

Các biến **bắt buộc**, không có secret mặc định:

| Biến | Yêu cầu |
|---|---|
| `LANGFUSE_POSTGRES_PASSWORD` | Mật khẩu riêng; dùng hex để an toàn trong URI PostgreSQL |
| `LANGFUSE_CLICKHOUSE_PASSWORD` | Mật khẩu riêng ClickHouse |
| `LANGFUSE_REDIS_AUTH` | Mật khẩu riêng Redis, dùng hex không có khoảng trắng/newline |
| `LANGFUSE_S3_ACCESS_KEY_ID` | Access key riêng MinIO, ít nhất 3 ký tự |
| `LANGFUSE_S3_SECRET_ACCESS_KEY` | Secret riêng MinIO, ít nhất 8 ký tự |
| `LANGFUSE_SALT` | Giá trị ngẫu nhiên, giữ ổn định cùng dữ liệu |
| `LANGFUSE_ENCRYPTION_KEY` | Đúng 64 ký tự hex (32 byte ngẫu nhiên) |
| `LANGFUSE_NEXTAUTH_SECRET` | Secret session ngẫu nhiên |
| `LANGFUSE_PUBLIC_KEY` | Project API public key, dạng `pk-lf-<giá trị ngẫu nhiên>` |
| `LANGFUSE_SECRET_KEY` | Project API secret key, dạng `sk-lf-<giá trị ngẫu nhiên>` |
| `LANGFUSE_INIT_USER_EMAIL` | Email hợp lệ của tài khoản local ban đầu |
| `LANGFUSE_INIT_USER_PASSWORD` | Mật khẩu mạnh, tối thiểu 12 ký tự |

Sinh từng secret độc lập bằng bộ sinh mật mã, chẳng hạn `openssl rand -hex 32`
với output **redirect vào file bảo vệ**, không in ra terminal/log. Dùng hex cho
các secrets để tránh vấn đề escaping trong URI, Redis config và dotenv. Không
đổi salt/encryption key khi tái sử dụng volumes. Credentials trong environment
container vẫn có thể được người có quyền Docker đọc; đây chỉ là stack local.

Giá trị không bí mật mặc định:

- `LANGFUSE_INIT_ORG_ID=heritage-local`, `LANGFUSE_INIT_ORG_NAME=Heritage Local`;
- `LANGFUSE_INIT_PROJECT_ID=heritage-chatbot`,
  `LANGFUSE_INIT_PROJECT_NAME=Heritage Chatbot`;
- `LANGFUSE_INIT_USER_NAME=Local Evaluator`;
- SDK: `LANGFUSE_HOST=http://localhost:3003`, `LANGFUSE_ENABLED=false` trong
  `.env.example`; đổi thành `true` **chỉ trong môi trường backend đánh giá**;
- SDK: `LANGFUSE_TIMEOUT=60` giây cho stack local; mặc định SDK là 5 giây và
  đã phát sinh exporter timeout khi đo trên máy dùng chung tài nguyên. Biến này
  phải được nạp vào process backend, không chỉ file environment của Compose.
  Tăng timeout không khôi phục span đã mất; không đổi giữa lượt đo đang chạy;
- `OBSERVABILITY_CONTENT_CAPTURE=metadata` mặc định. Chỉ lượt đo local có chủ ý
  mới dùng `full` (nội dung đã redact); sau đó trả về `metadata` hoặc `none`.

Compose chỉ nội suy biến `LANGFUSE_*`; `DATABASE_URL`, `POSTGRES_*`, `REDIS_*`
nghiệp vụ không thể ghi đè endpoint/credentials Langfuse. Trong container,
PostgreSQL user/database và ClickHouse user là `langfuse`; bucket MinIO là
`langfuse`, prefix `events/` và `media/`, region `auto`, path-style bật. TLS Redis,
ClickHouse cluster, telemetry, experimental features và batch export tắt cho
local. Không cần OTEL collector hoặc cài thêm Python dependencies.

Web dùng headless initialization để tạo org/project/user và project API keys
ngay lần khởi động đầu. Cặp `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` được map
trực tiếp sang `LANGFUSE_INIT_PROJECT_PUBLIC_KEY`/`LANGFUSE_INIT_PROJECT_SECRET_KEY`:
SDK và project dùng cùng cặp key, không phải hai cặp khác nhau. Init không phải
công cụ rotate key/reset password trên dữ liệu đã tồn tại; nếu tái sử dụng volumes,
phải giữ đúng credentials đã provision hoặc quản lý thay đổi trong UI. Signup
công khai bị tắt; đăng nhập bằng user đã khởi tạo.

### Bật, kiểm tra và dừng

Chạy từ repository root sau khi file credential đã sẵn sàng:

```bash
docker compose --env-file .amp/in/langfuse.env --profile langfuse config --quiet
docker compose --env-file .amp/in/langfuse.env --profile langfuse up -d
docker compose --env-file .amp/in/langfuse.env --profile langfuse ps
curl --fail --silent --show-error http://localhost:3003/api/public/health
# Dừng stack quan sát, giữ nguyên volumes và dịch vụ nghiệp vụ:
docker compose --env-file .amp/in/langfuse.env --profile langfuse stop
```

Chỉ chạy các lệnh khởi động khi đã được phép. Không chạy `down -v`, không xóa
volume hay khởi động lại project `heritagegraph`. Health web chỉ chứng minh web
đang sống; cần kiểm tra API xác thực và trace ingestion riêng bằng project keys.
Không đưa keys vào command line, báo cáo hoặc log. Khi khởi động backend đánh giá,
nạp các biến SDK từ file local vào **process riêng**, giữ nguyên model/prompt,
retrieval/reasoning và cấu hình kết nối nghiệp vụ; không thay môi trường của API
đang chạy. Langfuse lỗi phải giữ hành vi fail-open hiện có của chatbot.

Giới hạn RAM container: web/worker mỗi service 1024 MiB (Node heap 768 MiB),
ClickHouse 1536 MiB (memory accounting 1 GiB), PostgreSQL 384 MiB, Redis/MinIO mỗi
service 256 MiB, tổng trần khoảng **4,38 GiB**; CPU mỗi service 0,5–1 core. Redis
dùng AOF và `noeviction`, maxmemory 128 MiB để không tự loại job. Đây là cấu hình
thử nghiệm nhỏ, không phải sizing production hay bảo đảm không OOM. Với Docker
8 GiB dùng chung OpenSearch, kiểm tra RAM còn trống và `docker stats` trước khi
đo; migration/merge có thể gây đỉnh RAM. Nếu thiếu RAM, dừng đánh giá và ghi lại
giới hạn, không thay đổi/xóa OpenSearch hay lặng lẽ đổi cấu hình giữa lượt đo.

### Diễn giải lượt đánh giá 50 câu

Runner hỗ trợ `--hybrid-only` để không yêu cầu snapshot GraphRAG và `--balanced`
để lấy đều câu hỏi trải từ đầu tới cuối mỗi nhóm. Cờ hybrid chỉ điều khiển runner,
không tắt GraphRAG trong backend: phải kiểm tra môi trường backend riêng.
Ví dụ với inventory đã export và runtime manifest không chứa secrets:

```bash
.venv/bin/python -m pipelines.evaluation.eval_graphrag_chat \
  --url http://127.0.0.1:8001 \
  --inventory-root .amp/in/langfuse-50-inventory \
  --hybrid-only --balanced --limit 50 \
  --runtime-manifest .amp/in/artifacts/langfuse-50-runtime.json \
  --output .amp/in/artifacts/langfuse-50.jsonl
```

Runner không ghi đè kết quả cũ; dùng output mới cho lần chạy tiếp theo. Manifest
runtime cần ghi cấu hình **đã kiểm tra của server đang chạy**, không suy ra chỉ từ
`.env`. Summary dùng p95 nearest-rank, gồm cả response validation dự kiến; số
`all_evidence_groups_hit` chỉ là độ phủ ID nguồn kỳ vọng, không chứng minh mọi
khẳng định trong đáp án đều đúng. Langfuse v4 dùng Observations API v2 để đối soát
(`fields=core,basic,io,metadata,...`); API traces cũ không có trên events-only.

Chốt danh sách 50 câu (5 câu mỗi nhóm), model, prompt, reasoning settings và hash
corpus trước khi chạy tuần tự. Ghi correlation ID, timing, câu trả lời, lỗi và
run identity vào artifacts local bị Git bỏ qua. Không retry POST chatbot khi
transport lỗi mà chưa biết request có hoàn tất không; lưu phần đã có và báo số
câu chưa chạy. Ingestion bất đồng bộ cần được đợi/đối soát theo correlation ID;
chỉ đếm retrieval/context/generation nếu bước đó thực sự chạy, không suy từ HTTP
200 hay health check. Nội dung capture vẫn có thể nhạy cảm sau redact: chỉ dùng
câu đánh giá cố định, không chia sẻ trace thô ra ngoài.

Báo cáo phải tách HTTP/schema, bằng chứng được chọn/citation và nhận xét nội dung.
`grounded=True`, rubric/passage ID nội bộ hoặc trace đủ span **không phải** bằng
chứng đúng lịch sử; không công bố historical accuracy khi chưa thẩm định nguồn.
