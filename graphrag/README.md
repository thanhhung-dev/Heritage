# Microsoft GraphRAG MVP — Global Search

Microsoft GraphRAG được **ghép vào `/api/chat` cùng hybrid + BGE** khi `GRAPHRAG_ENABLED=true`, không thay graph NetworkX hiện tại. Dùng package chính thức `graphrag==3.3.0` để xây community reports; vẫn có endpoint Global Search riêng để kiểm tra báo cáo tổng hợp.

```text
PostgreSQL passage mapping → đọc text/checksum từ R2
  → snapshot input + source-manifest.json
  → Microsoft GraphRAG workflows → Parquet/community reports
  → /api/graphrag/query → Global Search → answer + community provenance về R2
```

## Phạm vi MVP

- Global Search; **chưa có Microsoft Local/DRIFT Search hoặc tự động chọn query engine**.
- Dùng OpenAI-compatible completion server 8080 hiện có; không tự bật/thay model.
- Chạy các workflow chính thức, bỏ claims và text embeddings vì Global Search không cần vector index. BGE của luồng hybrid giữ nguyên.
- Một request GraphRAG mỗi backend process; request trùng lúc nhận 503 thay vì dồn tải model. Với nhiều backend workers, giới hạn này không phải khóa toàn hệ thống.
- GraphRAG chạy subprocess trong `.venv-graphrag`, không đưa pandas/pyarrow/LiteLLM vào môi trường backend.
- Snapshot chỉ sẵn sàng sau khi indexing không có workflow error, bảng không rỗng và có đầy đủ lineage về manifest. Không phục vụ snapshot đang index hoặc đã bị sửa sau khi publish.
- Tích hợp hiện dành cho backend chạy local. Docker image backend hiện tại không chứa worker/venv; cần đóng gói riêng trước khi bật trong Docker hoặc production.

## 1. Cài môi trường riêng (Python 3.12)

Chạy tại thư mục gốc repository:

```bash
uv venv .venv-graphrag --python 3.12
uv pip install --python .venv-graphrag/bin/python -r graphrag/requirements.txt
```

Package có nhiều dependency. Không cài vào `.venv` đang phục vụ backend. Phiên bản GraphRAG được pin, nhưng đây chưa phải transitive lockfile cho mọi platform.

## 2. Xuất một snapshot nhỏ từ dữ liệu R2 thật

Backend `.venv` phải có `DATABASE_URL`, `R2_BUCKET`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` trong environment hoặc `.env`:

```bash
.venv/bin/python -m pipelines.graph.microsoft_graphrag export \
  --root graphrag/runs/thien-mu-001 --env-file .env --limit 5
```

Mặc định chọn theo passage ID tăng dần. Muốn chọn chính xác thêm `--passage-ids 18 19 20 21 22`; kiểm tra ID thuộc dữ liệu bạn muốn trước khi chạy. `--limit` vẫn áp dụng khi chỉ định ID.

Export chỉ đọc DB/R2 và tạo dữ liệu local; không upload, sửa hoặc xóa nguồn. Nó dùng `R2PassageStore.read_text` kiểm tra checksum, xuất mỗi passage thành một file `passage-<id>.txt`, kèm manifest chứa passage ID, bucket, object key, content hash và nhãn. Không ghép theo `S1/S2` vì các nhãn đó có thể trùng nhau. Đường dẫn snapshot phải chưa tồn tại; lỗi đọc nguồn không publish snapshot một phần.

## 3. Kiểm tra cấu hình rồi lập chỉ mục

`settings.yaml` được copy từ `graphrag/settings.example.yaml` lúc export. Các biến completion mặc định dùng server local; có thể đặt trong `.env`:

```dotenv
GRAPHRAG_MODEL=local-model
GRAPHRAG_API_BASE=http://127.0.0.1:8080/v1
GRAPHRAG_LLM_API_KEY=local-not-a-secret
```

Nếu server kiểm tra model ID, dùng ID từ `GET http://127.0.0.1:8080/v1/models`. Nếu dùng dịch vụ bên ngoài, cấu hình URL/key phù hợp và xét quyền gửi dữ liệu ra ngoài trước khi index. Script không tự chuyển sang nhà cung cấp trả phí.

```bash
.venv-graphrag/bin/python -m pipelines.graph.microsoft_graphrag index \
  --root graphrag/runs/thien-mu-001 --env-file .env
```

**Indexing gọi LLM nhiều lần, không phải một lần cho cả kho.** Bắt đầu từ 2–5 đoạn, kiểm tra tải và chất lượng trước khi tăng. Cấu hình mẫu dùng concurrency 1 và context budget nhỏ; budget là phần dữ liệu, không phải toàn bộ prompt cộng output. Model phải làm được extraction theo định dạng và community report JSON. Chat thông thường chạy được không bảo đảm GraphRAG indexing thành công.

Chỉ khi hoàn tất mới có `index-ready.json`. Bảng graph rỗng hoặc extraction lỗi thì không publish; không tạo dữ liệu giả để vượt kiểm tra. Không sửa/reindex snapshot đang phục vụ: export một thư mục mới, index, kiểm tra rồi đổi `GRAPHRAG_ROOT`. Không chỉnh settings của snapshot đã publish.

## 4. Query trực tiếp và bật endpoint

Trước khi bật backend, kiểm tra worker:

```bash
printf '%s' '{"message":"Những chủ đề chính trong tập tài liệu này là gì?","community_level":0}' | \
  .venv-graphrag/bin/python -m pipelines.graph.microsoft_graphrag query \
    --root graphrag/runs/thien-mu-001 --env-file .env
```

Sau khi index/query thành công, đặt trong `.env` rồi khởi động lại backend:

```dotenv
GRAPHRAG_ENABLED=true
GRAPHRAG_ROOT=graphrag/runs/thien-mu-001
GRAPHRAG_PYTHON=.venv-graphrag/bin/python
GRAPHRAG_QUERY_TIMEOUT=180
```

```bash
curl http://127.0.0.1:8000/api/graphrag/query \
  -H 'Content-Type: application/json' \
  -d '{"message":"Những chủ đề chính trong tập tài liệu này là gì?","community_level":0}'
```

Endpoint chỉ nhận câu hỏi và community level (mặc định 0), **không nhận đường dẫn file hoặc lệnh index từ client**. Chưa bật, snapshot lỗi, model lỗi, busy hoặc timeout trả 503 an toàn; không âm thầm giả làm kết quả hybrid. Timeout hủy worker; server LLM có thể còn cần thời gian phát hiện kết nối đã đóng. Câu hỏi trống/quá dài hoặc level ngoài 0–10 trả 422; level phải tồn tại trong snapshot.

## 5. Chat kết hợp hybrid + Microsoft GraphRAG

Với cùng cấu hình ở trên, gọi `/api/chat` như trước, không cần client tự gọi hai endpoint:

```bash
curl http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Cổng Tam Quan có liên quan gì đến chùa Thiên Mụ?","use_rag":true}'
```

Sau các bước resolve/kiểm tra đối tượng hiện có, pipeline lấy candidate từ BM25, n-gram, vector, graph nội bộ và Microsoft Global Search. Chỉ các nguồn GraphRAG khớp **passage ID + bucket + object key + content hash** với inventory hiện tại mới được hợp nhất. Candidate trùng được gộp theo passage ID, rồi cùng qua coverage, lọc subject/intent, đọc R2 kiểm tra checksum, BGE rerank và chọn context. GraphRAG không vượt qua các ngưỡng hoặc giới hạn context hiện tại.

**Không đưa câu trả lời do Global Search sinh ra vào prompt làm bằng chứng.** Chat cuối chỉ đọc văn bản gốc R2; report không được tự nâng thành dữ kiện đã xác minh. Response chat giữ schema cũ; passage được chọn từ kênh Microsoft có thêm `microsoft_graphrag` trong `sources[].retrieval_methods`. Nhãn này chỉ xuất hiện nếu passage đó còn được chọn sau rerank/context selection.

Nếu tắt GraphRAG, snapshot chưa sẵn sàng, worker busy/lỗi/timeout, chat tiếp tục bằng hybrid. Snapshot cũ hoặc thuộc bucket khác không được gắn vào passage mới. Các trường hợp query rỗng, ambiguity, thiếu anchor hay kho nguồn lỗi vẫn giữ các cổng an toàn hiện có; không dùng GraphRAG để tự đoán đối tượng. Endpoint Global Search riêng vẫn có thể dùng cho câu hỏi tổng hợp không có anchor mà chat hiện từ chối.

Trong Langfuse, xem `rag.request` → `retrieval` → `retrieval.microsoft_graphrag` → `graphrag.global_search`, sau đó `retrieval.rerank`, `context.assembly`, `generation`. Bước hợp nhất ghi snapshot ID, candidate và trạng thái `used`, `no_matching_sources`, `disabled` hoặc `hybrid_fallback`. Không có bảo đảm GraphRAG luôn thêm nguồn mới hoặc tăng chất lượng với mọi câu hỏi.

Luồng này gọi Global Search trước khi sinh câu trả lời chat, nên có thêm lượt LLM map/reduce và độ trễ. `GRAPHRAG_QUERY_TIMEOUT` cũng là thời gian chờ tối đa bước GraphRAG trong chat; chỉ fallback sau khi bước đó lỗi/hết thời gian. Không bật thêm model, nhưng tổng lượng inference tăng. Snapshot mẫu chỉ chứa các passage đã export, không tự bao phủ toàn bộ kho R2 khi thêm dữ liệu mới.

## Dẫn nguồn và giới hạn tin cậy

Response của endpoint Global Search riêng có `answer`, `snapshot_id`, `context_reports`, `sources`, `source_scope="community_context"`, `grounding_verified=false`.

`sources` là **các passage thuộc community reports đã cấp cho truy vấn**, không phải khẳng định từng nguồn chứng minh từng câu. Global Search dùng report tổng hợp, không trực tiếp đọc lại passage R2 ở mỗi query. Model có thể tạo citation sai; adapter này không xác minh từng citation hay từng mệnh đề. Giữ nguyên `[Data: Reports (...)]` để đối chiếu với `context_reports`; report ID chỉ có ý nghĩa trong snapshot đó.

Với GraphRAG 3.3.0, report ID trong context là **community ID**, không phải UUID, chỉ số dòng hay `human_readable_id` của bảng report. Adapter nối community/level → text unit → document filename → manifest → passage R2; thiếu liên kết thì query thất bại, không tự đoán nguồn. Các quan hệ do LLM sinh vẫn cần kiểm tra trước khi coi là dữ kiện.

Trong Langfuse, xem `graphrag.request` → `graphrag.global_search`: câu hỏi, response, snapshot ID, community level, số report/nguồn và thời gian worker. `OBSERVABILITY_CONTENT_CAPTURE` vẫn kiểm soát nội dung. MVP này **chưa xuất từng lượt map/reduce, token usage hay chi phí bên trong subprocess** sang Langfuse. Không mặc định đây là trace generation chi tiết như luồng hybrid.

## Kiểm thử tích hợp

Hai môi trường có bộ kiểm thử riêng, không cần gọi model:

```bash
LANGFUSE_ENABLED=false .venv/bin/python -m unittest apps.backend.tests.test_microsoft_graphrag
.venv-graphrag/bin/python -m unittest pipelines.graph.test_microsoft_graphrag
```

Bộ đầu kiểm tra export, provenance, API, virtualenv isolation, lỗi subprocess, timeout và snapshot bị sửa. Bộ thứ hai dùng cấu hình, kiểu kết quả workflow và Parquet của SDK thật, nhưng stub lời gọi indexing/search để kiểm tra adapter độc lập với chất lượng LLM. Chúng không thay cho lần chạy index/query thật trên dữ liệu R2.

`apps.backend.tests.test_chat_graphrag` chạy với `PASSAGE_TEST_DATABASE_URL` trỏ PostgreSQL có pgvector. Bộ này dùng TEMP table, không ghi DB/R2 lâu dài; kiểm tra hợp nhất candidate, rerank, nguồn snapshot cũ/khác bucket và hybrid fallback. Tắt `GRAPHRAG_ENABLED=false` khi chạy các kiểm thử hybrid khác để không gọi model thật ngoài ý muốn; kiểm thử tích hợp tự bật GraphRAG với worker giả lập có kiểm soát.

## Nguồn API

- [Microsoft GraphRAG v3.3.0](https://github.com/microsoft/graphrag/releases/tag/v3.3.0)
- [Official build_index API](https://github.com/microsoft/graphrag/blob/v3.3.0/packages/graphrag/graphrag/api/index.py)
- [Official global_search API](https://github.com/microsoft/graphrag/blob/v3.3.0/packages/graphrag/graphrag/api/query.py)
