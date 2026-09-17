# Kiến trúc hệ thống

Số liệu trong tài liệu này là ĐO ĐƯỢC trên repo hiện tại (05/09/2026), không phải dự kiến.

> **QUAN TRỌNG — phân biệt as-built với thiết kế mục tiêu.** Toàn bộ mục
> "Lớp PostgreSQL" bên dưới (schema, docker-compose, seed_postgres,
> PostgresRepository, bảng 3D Story/Scene, bảng app_user/audit_log, bảng
> chat_session/chat_message/chat_feedback) là **THIẾT KẾ MỤC TIÊU cho Tuần 3
> trở đi**, KHÔNG phải hiện trạng. Trong repo hiện tại: không có tệp `.sql`,
> không có `docker-compose*`, không có driver DB trong venv, không có bảng nào.
> As-built hôm nay: graph dựng trong RAM lúc khởi động, không persist, không
> có người dùng, không có log.

Muốn tự đo lại: `bash scripts/run_indexing.sh` và `backend/.venv/bin/python eval/eval_attribution.py`.

## Sơ đồ tổng quan

```
┌──────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                    │
│  User hỏi → chat UI (localhost:3000)                     │
└────────────────────────┬─────────────────────────────────┘
                         │ POST /api/chat
                         ▼
┌──────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                     │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  /api/chat │───▶│   rag.py     │───▶│    llm.py    │ │
│  │ /api/graph │    │ (cổng từ chối)│    │              │ │
│  └────────────┘    └──────┬───────┘    └──────┬───────┘ │
└──────────────┬───────────┼───────────────────┼─────────┘
               │           ▼                   ▼
               │  ┌───────────────────────────────┐  ┌──────────────────┐
               │  │  retriever.py + kg.py         │  │ Qwen+LoRA GGUF   │
               │  │  - BM25 theo từ               │  │  models/         │
               │  │  - BM25 theo n-gram (bỏ dấu)  │  │ qwen-fused.gguf  │
               │  │  - graph 510 node / 1135 edge │  │  (Q8_0 runtime)  │
               │  │  dựng trong RAM, 0.23s        │  └──────────────────┘
               │  └───────────────────────────────┘
               │
               │   ┌──────────────────────────────────────────┐
               │   │  [THIẾT KẾ MỤC TIÊU — Tuần 3, chưa có]   │
               └──▶│  PostgresRepository (chỉ /api/graph)     │
                   │  - pgvector (0.8.6) cho entity embedding │
                   │  - Docker compose: postgres:16 + pgvector│
                   └──────────────────────────────────────────┘
```

Hệ hiện tại dựng graph trong RAM lúc khởi động (`@lru_cache` trên `get_retriever()`),
không persist xuống đâu cả. Không có Ollama, không có file parquet, không có
Neo4j, không có PostgreSQL (xem ghi chú đầu tài liệu).

## Luồng dữ liệu chi tiết

### 1. Ingestion (1 lần, offline)

```
Wikipedia VN (49 địa điểm Huế + Đà Nẵng trong training/locations_hue_danang.py)
       ↓ ingestion/crawl_by_location.py
corpus/wiki_by_location/*.txt   (45 crawl được / 2 bị loại - xem corpus/locations_index.json)
       ↓ backend/core/corpus.py: load_docs()
45 bài dùng được / 349 chunk    (bỏ 1 bài trùng nội dung, 1 trang định hướng)
```

`backend/core/corpus.py` là NGUỒN DUY NHẤT của việc chunk. Cả training và serving
đều import từ đây, nên đoạn `Nguồn:` lúc train có đúng hình dạng đoạn `Nguồn:`
lúc chạy thật.

### 2. Knowledge graph (dựng lại mỗi lần khởi động, 0.23s)

```
45 bài + corpus/locations_index.json
        ↓ backend/core/kg.py: build_graph()   ← KHÔNG gọi LLM
510 node: 235 entity, 222 year, 45 doc, 6 category, 2 region
1135 edge: 443 year, 242 mentions, 92 in_region, 92 in_category, 123 related, 98 in_ward, 45 is_about
1 thành phần liên thông, không có bài cô lập
```

> Lỗi đồ thị giữ đỉnh entity cho tài liệu bị loại đã được xử lý và suite retrieval
> đã chạy lại ngày 08/09/2026. Kết quả mới nằm ở cuối tài liệu.

Node entity đến từ hai nguồn deterministic:
- 49 địa điểm curated trong `locations_index.json` (kể cả 24 chưa crawl được -
  chúng vẫn là node hợp lệ để nối quan hệ);
- tên riêng bắt bằng mẫu "danh từ loại + tên riêng" của tiếng Việt
  (`lăng X`, `vua X`, `triều X`, `chùa X`...), yêu cầu xuất hiện ≥ 2 lần.

Vì vậy mọi node đều truy được về một chuỗi CÓ THẬT trong văn bản: graph không bao
giờ thêm thông tin sai vào hệ. Xuất artifact xem bằng Gephi/D3:
`bash scripts/run_indexing.sh` → `graphrag/output/{graph.gexf, graph.json, stats.json}`.

## Lớp PostgreSQL — THIẾT KẾ MỤC TIÊU (chưa triển khai)

> Mục này mô tả kế hoạch cho Tuần 3 (xem `docs/upgrade-plan.md` §2.2). Không có
> gì trong đó tồn tại trong repo hiện tại. Đọc như tài liệu thiết kế, không phải
> as-built.

PostgreSQL 16 + pgvector 0.8.6 dự kiến là nơi **persist** knowledge graph, không
phải lớp retrieval. Hai đường đi tách biệt:

| Đường | Dùng gì | Tại sao |
|---|---|---|
| `/api/chat` (retrieval) | `kg.py` build trong RAM | p95 retrieval phải < 50ms, BM25 + n-gram không cần RTT mạng |
| `/api/graph` (visualize/admin) | `PostgresRepository` đọc PG | người dùng/admin xem graph, cần persist giữa các lần restart |

```
graphrag/output/*.json (offline, một lần)
        ↓ scripts/seed_postgres.py          [chưa viết]
PostgreSQL 16 + pgvector 0.8.6              [chưa dựng]
   ├── entity          (kế hoạch: có embedding pgvector dim=1024)
   ├── relation
   ├── document        (45 bài Wikipedia Huế/Đà Nẵng)
   ├── passage         (349 chunk, char_start/char_end bất biến)
   └── category / region
        ↓ /api/graph
    Trả về D3-friendly JSON cho frontend graph viewer
```

### Schema (rút gọn — thiết kế, chưa có bảng nào)

**Lớp tri thức (KG + KG persistence):**

```sql
CREATE TABLE entity (
  id           TEXT PRIMARY KEY,           -- ENT-0001, do code cấp, không max+1
  kind         TEXT NOT NULL,              -- 'entity' | 'year' | 'doc' | 'category' | 'region'
  label        TEXT NOT NULL,              -- "Lăng Minh Mạng"
  aliases      TEXT[] DEFAULT '{}',
  embedding    vector(1024),               -- Qwen2.5-Embedding local
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE relation (
  id           TEXT PRIMARY KEY,           -- REL-0001
  subject_id   TEXT NOT NULL REFERENCES entity(id),
  predicate    TEXT NOT NULL,              -- closed vocab, xem AD-14 của spine
  object_id    TEXT NOT NULL REFERENCES entity(id),
  weight       REAL DEFAULT 1.0
);

CREATE TABLE document (
  id           TEXT PRIMARY KEY,           -- DOC-0001
  title        TEXT NOT NULL,
  url          TEXT,
  region       TEXT                        -- 'hue' | 'da_nang'
);

CREATE TABLE passage (
  id           TEXT PRIMARY KEY,           -- PSG-0001
  document_id  TEXT NOT NULL REFERENCES document(id),
  text         TEXT NOT NULL,              -- BẤT BIẾN, không bao giờ UPDATE
  char_start   INT NOT NULL,
  char_end     INT NOT NULL,
  UNIQUE(document_id, char_start, char_end)
);
```

**Lớp nội dung 3D (CMG Story/Scene — hệ đầy đủ trong spine):**

```sql
-- Quyền & công bố (một bản ghi cho mỗi Document/Scene; AD-6 sống trên chính bản ghi)
CREATE TABLE rights (
  owner_kind   TEXT NOT NULL,              -- 'document' | 'scene'
  owner_id     TEXT NOT NULL,
  license      TEXT,                       -- 'CC-BY-SA-4.0' | ...
  publication_state TEXT NOT NULL DEFAULT 'draft',  -- draft | in_review | published | withdrawn
  decided_by   TEXT REFERENCES app_user(id),
  decided_at   TIMESTAMPTZ,
  PRIMARY KEY (owner_kind, owner_id)
);

CREATE TABLE scene (
  id            TEXT PRIMARY KEY,          -- SCN-0001
  title         TEXT NOT NULL,
  sog_path      TEXT NOT NULL,             -- 'sog/kinhthanh.sog'
  transform_7dof JSONB NOT NULL,           -- {tx,ty,tz,qx,qy,qz,qw,sx,sy,sz} — AD-7
  proxy_mesh    JSONB,                     -- raycast mesh
  region        TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE story (
  id            TEXT PRIMARY KEY,          -- STY-0001
  title         TEXT NOT NULL,
  scene_id      TEXT NOT NULL REFERENCES scene(id),
  camera_path   JSONB NOT NULL,            -- keyframe JSON
  publication_state TEXT NOT NULL DEFAULT 'draft',
  created_by    TEXT NOT NULL REFERENCES app_user(id),
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE narration (
  id            TEXT PRIMARY KEY,          -- NAR-0001
  story_id      TEXT NOT NULL REFERENCES story(id) UNIQUE,
  audio_path    TEXT NOT NULL,             -- 'audio/sty-0001.mp3'
  duration_ms   INT NOT NULL,
  language      TEXT NOT NULL DEFAULT 'vi'
);

CREATE TABLE transcript (
  id            TEXT PRIMARY KEY,          -- TRT-0001
  narration_id  TEXT NOT NULL REFERENCES narration(id),
  text          TEXT NOT NULL,             -- bắt buộc (NFR07 accessibility)
  timecode_ms   INT[] NOT NULL             -- mảng mốc thời gian HH:MM:SS.mmm
);

CREATE TABLE hotspot (
  id            TEXT PRIMARY KEY,          -- HOT-0001
  story_id      TEXT NOT NULL REFERENCES story(id),
  entity_id     TEXT REFERENCES entity(id),
  x             REAL NOT NULL,
  y             REAL NOT NULL,
  z             REAL NOT NULL,             -- tọa độ Scene-LOCAL, trước khi nhân transform (AD-7)
  label         TEXT NOT NULL,
  description   TEXT
);

CREATE TABLE citation (
  id            TEXT PRIMARY KEY,          -- CIT-0001
  source_kind   TEXT NOT NULL,             -- 'passage' | 'transcript'
  passage_id     TEXT REFERENCES passage(id),
  transcript_id  TEXT REFERENCES transcript(id),
  char_start    INT,
  char_end      INT,
  snippet       TEXT NOT NULL,             -- text trích, snapshot lúc cite
  url           TEXT,
  CHECK ((passage_id IS NOT NULL) <> (transcript_id IS NOT NULL))
);
```

**Lớp người dùng & admin:**

```sql
CREATE TABLE app_user (
  id            TEXT PRIMARY KEY,          -- USR-0001
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,             -- argon2id, KHÔNG MD5/SHA
  role          TEXT NOT NULL DEFAULT 'admin',  -- v1: chỉ một vai admin
  session_token TEXT,                      -- HttpOnly cookie, hash SHA-256(token)
  created_at    TIMESTAMPTZ DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

CREATE TABLE audit_log (
  id            BIGSERIAL PRIMARY KEY,
  user_id       TEXT REFERENCES app_user(id),
  action        TEXT NOT NULL,             -- 'publish_story' | 'withdraw_doc' | ...
  target_kind   TEXT,                      -- 'story' | 'scene' | 'document'
  target_id     TEXT,
  payload       JSONB,
  created_at    TIMESTAMPTZ DEFAULT now()
);
```

**Lớp chatbot (log + feedback):**

```sql
CREATE TABLE chat_session (
  id            TEXT PRIMARY KEY,          -- SESS-xxxxxxxx
  started_at    TIMESTAMPTZ DEFAULT now(),
  user_agent    TEXT,
  ip_hash       TEXT                       -- hash IP, không lưu thô (privacy)
);

CREATE TABLE chat_message (
  id            BIGSERIAL PRIMARY KEY,
  session_id    TEXT NOT NULL REFERENCES chat_session(id),
  role          TEXT NOT NULL,             -- 'user' | 'assistant'
  content       TEXT NOT NULL,
  citations     JSONB,                     -- mảng {passage_id, snippet, url}
  abstained     BOOLEAN DEFAULT false,     -- AD-5: nếu false thì citations KHÔNG rỗng
  retrieval_strategy TEXT,                 -- 'bm25_ngram_graph' | 'bm25_only'
  latency_ms    INT,
  model         TEXT,                      -- 'qwen-fused-3b'
  corpus_version TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chat_feedback (
  id            BIGSERIAL PRIMARY KEY,
  message_id    BIGINT NOT NULL REFERENCES chat_message(id),
  rating        SMALLINT,                  -- 1 | -1
  comment       TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);
```

**Quy ước chung:**

- `id` luôn là `TEXT` kiểu `<PREFIX>-<NNNNNN>`, sequence cấp bởi DB, **không** dùng `max+1`
- `created_at` / `updated_at` luôn `TIMESTAMPTZ DEFAULT now()`
- Mọi bảng có `publication_state` (Document/Scene/Story) đều **không có** default `published` — phải qua admin gate (AD-6)
- Mọi `CHECK` ràng buộc ngữ nghĩa đặt ở DB, không phải ở app (AD-3)

### Khởi động và fallback (kế hoạch)

- **Lần đầu**: `docker compose up -d postgres` → `uv run python scripts/seed_postgres.py`
  → seed từ `graphrag/output/entities.json` + `relations.json` + corpus 45 bài.
- **Có PG**: `/api/graph` truy vấn trực tiếp bằng SQL (`psycopg[binary]>=3.2`).
- **Mất PG**: `kg.py` vẫn build trong RAM từ `corpus/` + `locations_index.json`
  như trước. `/api/graph` trả 503 với message hướng dẫn restart docker — đây là
  fallback **rõ ràng**, không phải silent degradation.

### Tại sao giữ BM25 trong RAM, không chuyển sang pgvector?

| Quyết định | Lý do |
|---|---|
| Retrieval vẫn ở RAM | p95 < 50ms, corpus 45 bài / 349 chunk load mất 0.23s vào RAM; SQL roundtrip thêm 5-15ms vô ích |
| Embedding entity lưu PG | Sau này có thể thêm semantic entity match (rerank) mà không phá retrieval shape |
| Không embedding chunks | chunks đã có BM25 + n-gram đủ tốt; thêm semantic là tốn chi phí index cho 349 dòng (định lại trong Tuần 5, Sprint 3, khi thêm kênh vector) |
| Không Neo4j | graph 510 node / 1135 edge là kích thước recursive CTE xử lý thoải mái; thêm container là chi phí không cân xứng với dự án một người |

### Docker compose (kế hoạch — chưa có trong repo)

```yaml
# infra/docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: heritagegraph
      POSTGRES_USER: hg
      POSTGRES_PASSWORD: ${PG_PASSWORD}     # từ .env, không commit
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

Embedding model cho entity: `Qwen/Qwen2.5-Embedding` chạy local bằng
`sentence-transformers`. Dim = 1024, không tinh chỉnh trong v1.

### 3. Training (1 lần, offline)

```
45 bài (cùng chunker với serving)
       ↓ training/bootstrap_deep_qa.py
data/train.jsonl + valid.jsonl        (sinh lại bằng script, số mẫu xem trong file)
       ↓ Transformers + PEFT LoRA (FP16/BF16, r=16, assistant-only loss)
models/peft-adapter/                  (Trainer checkpoint-N + best adapter)
       ↓ PEFT merge + llama.cpp converter (training/fuse.sh)
models/qwen-fused.gguf
```

Valid tách theo ĐỊA ĐIỂM, và mẫu valid nào dùng chung đoạn nguồn với train thì bị
bỏ - kiểm tra lại được bằng `source_of()` trong `bootstrap_deep_qa.py`.

### 4. Runtime (user hỏi)

```
User: "lang minh mang o dau"        (gõ không dấu - trường hợp rất thường gặp)
       ↓  POST /api/chat
retriever.retrieve()
   ├── BM25 theo từ    (có dấu, chính xác chính tả)
   ├── BM25 theo n-gram (4-gram trên text bỏ dấu → chịu được không dấu, sai chính tả)
   ├── hợp nhất bằng RRF (k=60, không cần scale điểm)
   ├── graph: find_seeds → "Lăng Minh Mạng" [entity]
   │          expand_docs 2 hop → điểm cho từng bài
   │          BƠM ỨNG VIÊN: chunk của bài được gọi đúng tên vào pool dù lexical thấp
   └── điểm = lexical + 0.35·graph + 0.15·entity_trong_chunk + 0.8·gọi-đúng-tên
       ↓
rag.retrieve_context()  → BA CỔNG TỪ CHỐI (xem bên dưới)
       ↓
context = 1 hoặc 2 chunk NỐI LIỀN (≤ 2200 ký tự, giữ thứ tự trong bài)
       ↓
llm.generate_response(): "Nguồn: {context}\n\nCâu hỏi: {question}"
       ↓
Qwen+LoRA: "... [Nguồn: <trích đoạn> — <url>]"
```

Context là MỘT đoạn văn liền mạch, không có dấu phân cách lạ, vì mỗi mẫu train có
`Nguồn:` là nội dung của một chunk. Nối nhiều chunk bằng ký hiệu lạ là tạo ra định
dạng model chưa từng thấy.

## Ba cổng từ chối (`backend/core/rag.py`)

Chatbot miền đóng thì TỪ CHỐI ĐÚNG quan trọng ngang trả lời đúng.

| Cổng | Điều kiện | Chặn được gì |
|---|---|---|
| Neo vào graph | câu hỏi phải nhắc tên một entity/bài/vùng/loại mà graph biết | câu ngoài miền ("giá bitcoin", "giải phương trình") |
| Bằng chứng | đã gọi đúng tên riêng thì chunk tốt nhất phải thuộc bài đó hoặc phải nhắc tên đó | câu neo đúng miền nhưng hệ CHƯA có tư liệu ("Đàn Nam Giao thờ ai" - có node, không có bài) |
| Coverage | ≥ 0.25 trọng số IDF của từ khoá câu hỏi có trong chunk | phần dư |

Đo trên 30 câu trong phạm vi / 16 câu ngoài phạm vi / 22 câu bằng chứng / 8 câu
scope / 11 câu chủ đề / 12 câu phường-xã / 20 câu paraphrase: coverage một mình
KHÔNG phân tách được (trong 0.36-0.80, ngoài 0.19-1.00 - hư từ tiếng Việt có mặt
trong bài wiki nào cũng vậy), còn "có neo vào graph" phân tách sạch. Đây là chỗ
graph trả giá trị rõ nhất: nó là thứ duy nhất biết câu hỏi có thuộc miền tri thức
này không.

Khi cổng chặn, context rỗng → `llm.py` ghi `Nguồn: (không có)` → đúng dạng các mẫu
refusal đã train, nên model từ chối lịch sự. Đây là hành vi mong muốn, không phải lỗi.

## Kết quả đo (`eval/eval_attribution.py`, ngày 08/09/2026)

```
trong phạm vi = 68/70   paraphrase = 9/39   ngoài phạm vi = 31/38
bằng chứng = 34/34   phường/xã = 18/20
```

41 lỗi còn lại được quy trách nhiệm: 18 `B_RANK`, 16 `C_GATE`, 7 `E_LEAK`.
Nút thắt chính là paraphrase; xem `eval/baseline-summary.md`.

Bao gồm cả truy vấn không dấu (`lang minh mang o dau`, `me xung lam tu gi`,
`cao lau la mon gi`, `bao tang co vat cung dinh hue trung bay gi`).

Con số này chỉ là NỬA TRÊN của độ chính xác:
`P(đúng) = P(lấy đúng đoạn) × P(model trung thực với đoạn đó)`. Nửa dưới do LoRA
lo và phải đo riêng bằng gold set (`eval/`).

## Tại sao thiết kế này?

| Quyết định | Lý do |
|---|---|
| Graph deterministic thay vì để LLM extract entity | Corpus 45 bài; index bằng LLM local mất 8-12 giờ, prompt extract mặc định bằng tiếng Anh trên văn bản tiếng Việt sai nhiều, và entity do LLM sinh có thể BỊA. Cách này build 0.23s và không bao giờ bịa. |
| Graph để MỞ RỘNG/XẾP LẠI retrieval, không để sinh câu trả lời | Câu trả lời phải truy được về văn bản gốc để trích nguồn |
| Graph vừa rerank vừa BƠM ứng viên | Truy vấn ngắn không dấu sinh nhiều n-gram phổ biến làm bài đúng rơi khỏi top-30; rerank thuần không cứu được, phải đưa bài đúng vào pool |
| BM25 + n-gram thay vì embedding | Không phải tải model, chạy offline ngay, và n-gram bỏ dấu xử lý được truy vấn không dấu - chỗ mà embedding tiếng Việt cũng hay trượt |
| RRF thay vì cộng điểm có trọng số | Hợp nhất theo THỨ HẠNG nên không phải chuẩn hoá thang điểm giữa hai nhánh |
| LoRA thay vì RAG-only | RAG cấp kiến thức, LoRA dạy văn phong + định dạng trích dẫn + CÁCH TỪ CHỐI |
| Qwen2.5-3B + LoRA FP16/BF16 | Vừa VRAM Kaggle phổ biến; kiến thức đến từ nguồn nên không cần model lớn |

## Trade-offs đã chọn

| Chọn | Bỏ qua | Lý do |
|---|---|---|
| kg.py tự viết | Microsoft GraphRAG + Ollama | 8-12h index, prompt tiếng Anh, entity có thể bịa, corpus quá nhỏ để đáng |
| Dựng index trong RAM cho retrieval | Vector DB / file parquet cho retrieval | 0.23s, và không bao giờ lệch với corpus hiện tại |
| PG chỉ persist graph (kế hoạch) | Neo4j / Qdrant | 510 node / 1135 edge nhỏ hơn ngưỡng cần graph DB riêng; recursive CTE đủ dùng, ít container hơn |
| Embed chỉ entity (kế hoạch) | Embed cả 349 chunk | Entity embedding rẻ, đủ cho semantic rerank; chunk đã có BM25 + n-gram (định lại trong Tuần 5 khi thêm kênh vector) |
| Từ chối khi không neo được | Cố trả lời mọi câu | Câu bịa tự tin tệ hơn câu từ chối |
| LoRA r=16 | r=64, full FT | Tránh overfit trên tập train nhỏ |
| Corpus Wikipedia trước | Nguồn học thuật | Mở rộng dần; pipeline không phụ thuộc nguồn |
