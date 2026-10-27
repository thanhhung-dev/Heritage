# Local: OpenSearch trong Docker, backend và LLM native

`docker-compose.yml` chỉ chạy OpenSearch 3.3.0 single-node. Không còn service
PostgreSQL, backend, frontend, LLM, Langfuse/ClickHouse hay profile observability.
OpenSearch Dashboards chưa được chạy trong giai đoạn này.

```bash
docker compose up -d opensearch
docker compose ps
curl 'http://127.0.0.1:9200/_cluster/health?wait_for_status=yellow&timeout=30s'
```

Node dùng heap 512 MiB, giới hạn RAM container 2 GiB và 2 CPU, lưu dữ liệu trong
volume `heritagegraph_opensearch_data`. Đây là cấu hình local nhỏ, không phải
topology production/HA. Linux có thể cần `vm.max_map_count` theo yêu cầu OpenSearch.
Security bị tắt và cổng chỉ bind `127.0.0.1`; không mở cổng ra LAN/Internet.

Các container cũ có thể được Compose báo là orphan. Dừng các service cũ trước
khi chạy native để tránh trùng cổng và tải nền, nhưng **không xóa volume**, không
chạy `down -v` hay prune. PostgreSQL nghiệp vụ không bị migrate/drop bởi đổi search.

Backend, BGE-M3 và llama.cpp chạy trên host theo [README](../README.md).
Trên Mac, Metal không được sử dụng bởi image llama.cpp Linux cũ; chạy native
để dùng GPU Apple. Đừng chỉ tăng GPU layers trong container không hỗ trợ GPU.

Kiểm tra index và dừng node:

```bash
curl http://127.0.0.1:9200/_cat/indices?v
docker compose logs --tail=100 opensearch
docker compose stop opensearch
```

Dừng node giữ dữ liệu. Đổi model/analyzer/dimension thì tạo index có tên phiên
bản mới, ingest lại và đổi `OPENSEARCH_INDEX`; không tái sử dụng mapping không tương thích.

## Backend trong Docker

`docker-compose.yaml` ở repo root hiện chỉ có service `backend` (build từ
`apps/backend/Dockerfile`), PostgreSQL/OpenSearch/llama.cpp vẫn ở ngoài.

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

Trong container, `localhost` là chính container. Gọi service chạy native trên host
phải dùng `host.docker.internal` (đã khai báo `extra_hosts: host-gateway` nên chạy
được cả trên Linux). Compose tự đặt `LLAMA_SERVER_URL=http://host.docker.internal:8080`;
muốn trỏ Postgres/OpenSearch về host thì bỏ comment hai biến tương ứng trong
`environment` của service `backend`.

Cổng chỉ bind `127.0.0.1:${BACKEND_PORT:-8000}`. Healthcheck dùng `/` chứ không
dùng `/api/health`, vì endpoint sau trả 503 khi llama.cpp chưa chạy.

### Đổi biến môi trường phải tạo lại container

`env_file: .env` chỉ được đọc lúc container được tạo. Sửa `.env` (ví dụ
`CORS_ORIGINS`, `DATABASE_URL`) mà chỉ `docker restart` thì tiến trình vẫn giữ
biến cũ:

```bash
docker compose up -d backend      # compose thấy env đổi ⇒ tạo lại container
docker compose up -d --build backend   # khi đổi cả code trong image
```

Hai triệu chứng đã gặp thật, cùng một nguyên nhân:

- `GET /api/heritages` trả 500 `{"detail": "Internal server error"}` vì
  `DATABASE_URL` trong `.env` trỏ `127.0.0.1:5433` — trong container đó là chính
  container, không phải host. Compose override bằng tên service
  (`heritagegraph-db-1:5432`) trong block `environment`, block này thắng `env_file`.
- Trình duyệt báo `blocked by CORS policy` dù `.env` đã thêm origin: preflight
  `OPTIONS` vẫn trả 400 `Disallowed CORS origin` cho tới khi container được tạo
  lại. Kiểm tra nhanh:

  ```bash
  curl -si -X OPTIONS http://127.0.0.1:8000/api/heritages \
    -H "Origin: http://127.0.0.1:3000" -H "Access-Control-Request-Method: GET" | head -3
  ```


## Chạy backend native (Windows, không Docker)

Cần `.venv` đã cài `apps/backend/requirements.txt`.

```powershell
.\start-backend.ps1              # cổng theo BACKEND_PORT trong .env
.\start-backend.ps1 -Port 8001   # hoặc chỉ định cổng
```

```bat
start-backend.bat
```

Cả hai đều gọi `scripts/run-backend.py`, **không** gọi `uvicorn` trực tiếp. Lý do:
psycopg async không chạy trên `ProactorEventLoop` — event loop mặc định của Windows —
và `uvicorn.run()` đặt lại policy về mặc định, nên query DB đầu tiên ném
`InterfaceError: Event loop is closed`. `scripts/run-backend.py` đặt
`WindowsSelectorEventLoopPolicy` rồi tự chạy `Server.serve()` trên loop đó.

Đánh đổi: **không có auto-reload** (reloader của uvicorn chạy app trong tiến trình con
và tiến trình đó không đi qua script). Sửa code thì Ctrl+C rồi chạy lại.

Kiểm tra nhanh sau khi chạy:

```bash
curl --noproxy '*' http://127.0.0.1:8001/api/heritages
curl --noproxy '*' http://127.0.0.1:8001/api/heritages/lang-tu-duc/tour
```

`--noproxy '*'` cần thiết trên máy có biến `http_proxy` trỏ vào proxy nội bộ — không có
nó, request tới `127.0.0.1` sẽ bị proxy trả 502.

### Kết nối PostgreSQL

DB local nằm trong Docker **trên WSL**, publish ra cổng **5433**, user/database đều là
`heritagegraph`:

```dotenv
POSTGRES_USER=heritagegraph
POSTGRES_DB=heritagegraph
DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5433/${POSTGRES_DB}
```

Hai bẫy đã gặp thật:

- Dùng `localhost` thay `127.0.0.1` ⇒ phân giải ra IPv6 `::1` trước và treo tới hết
  `connect_timeout`. Luôn ghi `127.0.0.1`.
- Đổi `POSTGRES_PASSWORD` trong `.env` **không** đổi mật khẩu của container đã tạo
  (biến đó chỉ có tác dụng lần `initdb` đầu). Sai mật khẩu thì phải
  `alter user ... with password ...` bên trong container, hoặc xoá volume.

