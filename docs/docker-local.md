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
