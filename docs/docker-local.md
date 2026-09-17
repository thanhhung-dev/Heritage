# Chạy HeritageGraph local bằng Docker Compose

Gói portable dùng `llama.cpp` + GGUF. Stack gồm PostgreSQL, Alembic migration, corpus importer,
`llm`, `backend` và `frontend`. PostgreSQL chỉ nằm trong mạng Compose và lưu dữ
liệu ở volume `postgres_data`.

## 1. Chuẩn bị GGUF và gói portable

Sau khi train PEFT trên Kaggle hoặc Linux NVIDIA, xuất GGUF trong training
environment (cần internet và đủ RAM để merge FP16):

```bash
python scripts/export_gguf.py
bash scripts/package_docker.sh
```

`export_gguf.py` đọc đúng base model từ `models/peft-adapter/adapter_config.json`,
merge adapter vào model FP16 tạm và chuyển một lần sang Q8_0. Có thể tải adapter
từ Kaggle về máy Linux đủ RAM rồi chạy bước này ngoài Kaggle.

Kết quả là `heritagegraph-docker.tar.gz`, bao gồm code, corpus và GGUF. Model và
corpus bị Git ignore nên clone repository đơn thuần **không đủ**. Script cũng tạo
sẵn `.env` với mật khẩu database ngẫu nhiên trong gói.

## 2. Chạy trên máy khác

Yêu cầu Docker Desktop/Engine có Compose v2, RAM tối thiểu 8 GB, khoảng 6 GB đĩa
trống và internet trong lần chạy đầu để tải/build image. CPU x86_64 và ARM64 đều
chạy được.

```bash
tar -xzf heritagegraph-docker.tar.gz
cd HeritageGraph
docker compose up -d
docker compose ps
```

Không cần cài Python/Node, export model hay thêm `--build`. Compose tự build
backend/frontend và tải image PostgreSQL/llama.cpp trong lần chạy đầu. Compose
tạo `DATABASE_URL` nội bộ từ các biến `POSTGRES_*`; không dùng hostname
`localhost` hoặc cổng host cho kết nối từ backend.

Service `migrate` đợi PostgreSQL healthy, chạy migration bootstrap rồi mới cho
backend khởi động. Database mới được upgrade bằng Alembic. Volume legacy chưa có
`alembic_version` chỉ được nhận vào baseline khi tập bảng và view khớp topology
legacy đã biết; wrapper sau đó bổ sung bảng `place_location` còn thiếu. Schema
lạ hoặc không đầy đủ bị từ chối an toàn. Nếu migration lỗi, backend không khởi
động và có thể xem chi tiết bằng:

```bash
docker compose logs migrate db
```

Sau migration, service `import-data` upsert 45 tài liệu corpus, passage, entity,
alias và location đã xác minh rồi mới cho backend chạy. Importer có UUID ổn định
và chạy lặp lại không tạo bản ghi trùng. Có thể chạy lại thủ công bằng:

```bash
docker compose run --rm backend python -m backend.db.import_corpus
```

Lần đầu Docker tải image và llama.cpp nạp model nên health check có thể mất vài
phút. Khi backend báo `healthy`:

- Giao diện: <http://localhost:3000>
- Backend health: <http://localhost:8000/api/health>
- API docs: <http://localhost:8000/docs>

Test một câu không qua giao diện:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Cao lầu là món gì?","use_rag":true}'
```

Xem log hoặc dừng hệ thống:

```bash
docker compose logs -f db migrate import-data llm backend
docker compose down
```

`docker compose down` giữ lại dữ liệu. Chỉ dùng `docker compose down -v` khi chủ
động muốn xóa toàn bộ database local.

## 3. Truy cập từ máy khác trong LAN

Sửa `.env` trước khi build, dùng IP máy chạy Docker:

```dotenv
NEXT_PUBLIC_API_URL=http://192.168.1.20:8000
```

Sau đó chạy `docker compose up --build -d`. Mở cổng 3000 và 8000 trên firewall.

## 4. Hiệu năng và kiểm định

Mặc định `LLAMA_GPU_LAYERS=0` để chạy được trên mọi CPU. Docker Desktop trên Mac
không truyền Metal vào container nên inference CPU sẽ chậm. Với NVIDIA Container
Toolkit, cần bổ sung quyền GPU cho service `llm` rồi tăng `LLAMA_GPU_LAYERS`.

GGUF là runtime khác với Transformers + PEFT dùng lúc đánh giá adapter. Trước khi
dùng số liệu trong báo cáo, chạy lại gold set qua API Docker và ghi thành một
baseline riêng; không mặc định xem kết quả GGUF giống hoàn toàn checkpoint PEFT.
