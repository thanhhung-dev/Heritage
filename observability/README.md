# Observability baseline

> **Tạm hoãn trong kiến trúc OpenSearch hiện tại.** Compose mặc định chỉ có
> OpenSearch; các lệnh/profile và cây observation dưới đây mô tả stack cũ,
> không còn chạy được bằng Compose hiện tại. Giữ `LANGFUSE_ENABLED=false` và
> `OTEL_TRACING_ENABLED=false`. File cấu hình được giữ để tham khảo/tích hợp lại
> sau, không khởi động thêm ClickHouse/Redis/MinIO. Retrieval mới có
> `query.embedding` và `retrieval.opensearch`, không còn inventory/R2 fetch.

Stack local gồm OpenTelemetry Collector → Tempo, Prometheus, Loki/Promtail, Grafana và Langfuse v4. Langfuse dùng PostgreSQL, ClickHouse, Redis và MinIO riêng. Các backend telemetry chỉ nằm trên Docker network; Grafana và Langfuse UI chỉ bind loopback. Dữ liệu Grafana demo giữ 7 ngày; dữ liệu Langfuse nằm trong named volumes cho đến khi operator chủ động xóa.

## Chạy local

```bash
cp .env.example .env                 # thay mật khẩu mẫu
# tạo secret bằng `openssl rand -hex 32`, thay mọi giá trị replace-* trong .env
# bật LANGFUSE_ENABLED=true sau khi đã đặt bootstrap public/secret key
OTEL_TRACING_ENABLED=true docker compose --profile observability up --build -d
./observability/smoke.sh local
```

Mở Grafana tại `http://127.0.0.1:3001` và dashboard **Heritage Observability Baseline**. Langfuse ở `http://127.0.0.1:3003`; đăng nhập bằng `LANGFUSE_INIT_USER_EMAIL` và `LANGFUSE_INIT_USER_PASSWORD`, project **HeritageGraph** được bootstrap tự động. Tìm log bằng `{service="heritage-api"} | json | correlation_id="<UUID>"`; correlation ID được parse lúc query thay vì làm label cardinality cao. Dùng ID này để chuyển từ response header sang log, Tempo và generation Langfuse.

Mặc định `OBSERVABILITY_CONTENT_CAPTURE=metadata`: không ghi input/output của các bước; vẫn ghi model/version, số lượng candidate, ngưỡng lọc, passage ID, token usage và latency. `none` tắt các observation RAG của ứng dụng trong Langfuse (không tắt metrics hoặc tracing OpenTelemetry riêng). Chỉ `full` mới ghi nội dung, sau khi che secret và các định danh cá nhân phổ biến. Không dùng raw prompt/evidence, IP, secret hay entity ID làm label metrics.

Langfuse là tùy chọn: `LANGFUSE_ENABLED=false` hoặc thiếu credentials làm SDK no-op; server down và lỗi SDK không thay đổi response nghiệp vụ. Tắt stack bằng `docker compose --profile observability down`. Không dùng `-v` nếu muốn giữ dữ liệu. Stack đầy đủ cần nhiều RAM/CPU hơn baseline do ClickHouse, PostgreSQL, Redis, MinIO, web và worker; cấu hình này chỉ dành cho local/demo, không phải topology HA production.

## Debug RAG trong Langfuse

Để xem cả nội dung khi debug local, đặt trong `.env`, rồi khởi động lại backend:

```dotenv
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3003
OBSERVABILITY_CONTENT_CAPTURE=full
```

`LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` phải thuộc project đang xem; không đưa secret vào log hoặc commit. Nếu backend chạy trong Docker, dùng host nội bộ `http://langfuse-web:3000` thay cho localhost. Chế độ `full` lưu câu hỏi và văn bản nguồn; redaction không bảo đảm loại bỏ mọi loại dữ liệu nhạy cảm, nên chỉ bật với dữ liệu được phép lưu trong Langfuse.

Gửi câu hỏi qua `POST /api/chat`, mở project **HeritageGraph** trong Langfuse, tìm observation **rag.request** mới nhất. Đối chiếu `metadata.correlation_id` với header `X-Correlation-ID` của response để chọn đúng lần gọi. Mở cây trace để xem:

| Observation | Nội dung cần kiểm tra (với `full`) |
| --- | --- |
| `rag.request` | Câu hỏi gốc, response API đầy đủ, trạng thái trả lời và passage được chọn. |
| `retrieval.inventory`, `retrieval.index` | Số passage hợp lệ, model embedding, cache hit/miss. |
| `query.resolve` | Query đã chuẩn hóa, subject, intent, correction và ambiguity. |
| `retrieval.gates` | Lý do dừng sớm: query rỗng, inventory rỗng, ambiguity hoặc không đủ điều kiện entity/admin. Chỉ xuất hiện khi bị chặn. |
| `query.embedding` | Query, model và số chiều; không lưu vector thô. |
| `retrieval.bm25`, `retrieval.bm25_ngram`, `retrieval.graph`, `retrieval.vector` | Candidate, điểm riêng từng kênh, graph seed và ngưỡng vector. Điểm giữa các kênh không cùng thang đo. |
| `retrieval.coverage`, `retrieval.filters` | Candidate được giữ/loại và lý do: thiếu coverage, subject, địa điểm hoặc năm. |
| `retrieval.r2_fetch` | Nội dung nguồn đã kiểm tra checksum và object key tương ứng. |
| `retrieval.rerank` | Query/text thực sự được rerank, điểm relevance và quyết định theo ngưỡng. Điểm này không phải xác suất câu trả lời đúng. |
| `retrieval.selection` | Thứ tự sau xếp hạng, quyết định chọn/loại do tỷ lệ điểm, giới hạn context hoặc số chunk. |
| `context.assembly` | Context thực sự gửi sang bước sinh câu trả lời và độ dài ký tự. |
| `generation` | Messages gửi model (đã redaction), câu trả lời, model, tham số, hash phiên bản system prompt, tổng token khi server cung cấp và `finish_reason`. |

Mỗi observation có thời gian chạy. Các bước lỗi ghi mức `ERROR` và tên loại lỗi, không ghi nguyên văn exception có thể chứa secret. Nếu retrieval lỗi nhưng API trả fallback an toàn, xem observation con: root vẫn có thể hoàn tất bình thường. Không có evidence thì sẽ không có bước generation.

Khi câu trả lời quá ngắn, đọc `retrieval.selection` → `context.assembly` → `generation`. Context thiếu thông tin thì kiểm tra retrieval; context đủ nhưng model bỏ qua thì kiểm tra messages và hành vi model. `finish_reason=length` cho biết đã chạm giới hạn sinh, còn `stop` là server báo kết thúc, không phải chứng nhận câu trả lời đầy đủ. Langfuse giúp quan sát, không tự sửa retrieval/model hay tự xác minh factual grounding: `grounding_verified=false`; trường legacy `grounded` chỉ nói rằng đã cấp evidence.

## AWS staging

Deploy backend với endpoint OTLP nội bộ trong VPC, `APP_ENVIRONMENT=staging` và `OTEL_TRACING_ENABLED=true`; giữ telemetry services sau security group/private load balancer. Không cần AWS credentials trong ứng dụng. Chạy:

```bash
BASE_URL=https://staging.example \
GRAFANA_URL=https://grafana.internal \
GRAFANA_TOKEN=replace-with-read-only-service-account-token \
./observability/smoke.sh staging
```

Smoke test gửi một correlation ID, chờ ID đó xuất hiện trong Loki và truy vấn Tempo bằng TraceQL, đồng thời kiểm tra telemetry endpoint không public. Có thể dùng `GRAFANA_AUTH=user:password` thay cho token ở môi trường demo. Public ingress phải chặn `/internal/metrics`, cổng 4317, 3100, 3200 và 9090. Chỉ đặt `ALLOW_PUBLIC_TELEMETRY=true` nếu policy staging chủ động cho phép metrics endpoint. Exporter và Langfuse là fail-open: sự cố telemetry không được làm request nghiệp vụ thất bại.
