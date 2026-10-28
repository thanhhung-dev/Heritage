# Chạy integration tests Search với OpenSearch local

File `docker-compose.search-test.yaml` tạo một node OpenSearch 3.3.0 riêng cho
kiểm thử. Node dùng heap 512 MiB, giới hạn RAM 2 GiB / 2 CPU, cổng
`127.0.0.1:9200` và volume `heritage-search-tests_opensearch_test_data`.
Security plugin được tắt cho node test chỉ nhận kết nối loopback.
Cấu hình Compose mặc định của dự án không bị thay đổi.

Khởi động Docker Desktop, sau đó chạy từ repo root:

```powershell
docker compose -f docker-compose.search-test.yaml up -d opensearch
docker compose -f docker-compose.search-test.yaml ps
Invoke-RestMethod 'http://127.0.0.1:9200/_cluster/health?wait_for_status=yellow&timeout=30s'
```

Lần đầu cần tải image và chờ node khởi động. Chỉ chạy tests sau khi cluster trả
trạng thái `yellow` hoặc `green`.

Dùng virtualenv Backend đã cài `apps/backend/requirements-test.txt`:

```powershell
$env:OPENSEARCH_TEST_URL = 'http://127.0.0.1:9200'
python -m pytest apps/backend/tests/test_opensearch.py -q
```

File này có 3 transport tests và 6 integration tests. Integration tests sử dụng
vector xác định để kiểm tra cơ chế tìm kiếm; chúng không tải model embedding
hay gọi LLM. Mỗi test tạo index `heritage-test-<UUID>` và search pipeline riêng,
rồi xóa đúng các tài nguyên đó khi kết thúc.

Để chạy toàn bộ Backend cùng OpenSearch:

```powershell
$env:OPENSEARCH_TEST_URL = 'http://127.0.0.1:9200'
python -m pytest apps/backend/tests/ -q
```

Những lỗi Profile do schema danh tính UUID/integer là vấn đề riêng; việc có
OpenSearch không sửa các lỗi đó.

Dừng node khi không dùng; volume dữ liệu được giữ nguyên:

```powershell
docker compose -f docker-compose.search-test.yaml stop opensearch
```

Tham khảo [tài liệu Docker của OpenSearch 3.3](https://docs.opensearch.org/3.3/install-and-configure/install-opensearch/docker/).
