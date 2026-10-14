# Ingestion tài liệu R2 trên local

Lệnh này nhận **link tới từng file**, tải qua HTTP(S), trích text, chuẩn hóa
Unicode, chia passage có overlap và xuất knowledge package tương thích với
`apps.backend.db.import_structured`. Không cần chạy model chatbot.

Đây là bước chuyển tiếp của kiến trúc trong `chatbot.md`: nội dung được nhập vào
PostgreSQL để dùng full-text/trigram search hiện tại. **Chưa tạo embedding, chưa
upload processed lên R2, chưa có active-release pointer và chưa chuyển runtime
sang fetch R2.** Mapping R2 được giữ trong package/manifest local; importer hiện
tại chưa lưu các object key vào database. Không coi manifest này là release
descriptor hoàn chỉnh của kiến trúc đích.

## 1. Cài môi trường

Chạy tại root repository, dùng Python 3.12 trở lên:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pipelines/ingestion/requirements.txt
mkdir -p data/ingestion
cp pipelines/ingestion/r2_sources.example.json data/ingestion/sources.json
```

`data/` đã được Git ignore. Không điền signed URL vào file example được track.

## 2. Điền link và metadata

Sửa `data/ingestion/sources.json`. Mỗi phần tử trong `documents` là một file:

| Trường | Ý nghĩa |
|---|---|
| `url` | Link tải trực tiếp từ R2, public hoặc signed URL còn hạn |
| `object_key` | Key thật trong bucket, không phải URL |
| `source_url` | URL nguồn gốc để trích dẫn, không chứa query/secret; giữ ổn định |
| `title` | Tên tài liệu |
| `region` | `hue` hoặc `da_nang` |
| `source_type` | `official`, `academic`, `management`, `press`, `encyclopedia`, `other` |
| `tier` | 1–4, số nhỏ ưu tiên cao; phải đánh giá nguồn, không mặc định mọi file là official |
| `observed_at` | Thời điểm thu thập nguồn, ISO datetime có múi giờ |
| `format` | Tuỳ chọn: `md`, `txt`, `html`, `pdf`; hữu ích nếu URL không có đuôi |

Nếu tài liệu tự biên soạn không có website nguồn, có thể dùng URL R2 không chứa
query làm `source_url`, nhưng đó là nguồn lưu trữ chứ không thay thế provenance
đến các tài liệu đã dùng để biên soạn. Mỗi nguồn riêng phải có `source_url` riêng,
kể cả khi nội dung giống nhau.

Không dùng link trang dashboard hoặc chỉ link bucket: HTTP public không có API
liệt kê toàn bộ bucket. Thêm các file cần xử lý vào `documents`.

Với signed URL, có thể thay `url` bằng `"url_env": "R2_DOCUMENT_URL"` và đặt biến
môi trường đó trong terminal. Download URL không được ghi vào package/manifest.
Không đặt signed URL trong `source_url`, `object_key` hay metadata khác.

Hỗ trợ Markdown, UTF-8 text, HTML (loại script/style/navigation) và PDF có text.
Ảnh, PDF scan cần OCR trước; DOCX cần export sang Markdown/text/PDF có text.
Kiểm tra text PDF sau extraction, nhất là tài liệu nhiều cột/bảng.

Chọn `corpus_version` **chưa có trong database**, không mặc định dùng version 2
nếu nó đã tồn tại. Importer cũ có thể cập nhật trạng thái release hiện có; tuyệt
đối không import package draft vào một version đang published.

## 3. Chạy ingestion

```bash
python -m pipelines.ingestion.ingest_r2 \
  --config data/ingestion/sources.json
```

Output mặc định là `data/ingestion/corpus-v<corpus_version>/`:

```text
corpus-v2/
├── raw/                 # bytes tải về, đặt tên theo SHA-256
├── processed/corpus-v2/passages/  # passage JSON, mapping nguồn + exact spans
├── package.json         # input cho importer PostgreSQL, mặc định draft
├── manifest.json        # mapping local/R2, config digest, checksum và size
└── manifest.sha256      # SHA-256 của manifest
```

Tuỳ chọn `--output <directory>` và `--max-bytes <bytes>` (mặc định 16 MiB/file).
Chunk mặc định tối đa 2400 ký tự, overlap mục tiêu 300 ký tự; ưu tiên ranh giới
đoạn → câu → từ, fallback cắt theo ký tự cho token rất dài. Đây **không phải**
token budget của model. Offset tính trên text đã trích/chuẩn hóa, không phải byte
offset của PDF/HTML gốc; bản bytes nguyên gốc được giữ riêng trong `raw/`.

Cùng nội dung, metadata và cấu hình tạo cùng output. Nếu output đã tồn tại nhưng
khác, lệnh từ chối ghi đè; tăng version và dùng output mới. Lỗi tải/xử lý bất kỳ
file nào sẽ không xuất package một phần. Không chỉnh sửa file trong output đã
hoàn thành nếu muốn rerun để kiểm tra tính tái lập.

## 4. Review và nhập database

Kiểm tra `package.json`: nguồn, text, passage, ngày, tên và số liệu. Package không
tự trích entity/claim/relation bằng LLM; các mảng đó để trống. Không tự publish
nội dung chưa review.

Đặt `DATABASE_URL` trỏ đến PostgreSQL **local/thử nghiệm** dùng driver
`postgresql+psycopg`. Lệnh không tự đọc `.env`; cần export biến trong terminal.
Database mới có thể khởi tạo bằng:

```bash
python -m apps.backend.db.init_db
```

Database phải tương thích với ORM backend hiện tại (`document`, UUID `passage`,
`corpus_release`). `init_db` chỉ tạo bảng thiếu, **không migrate bảng cũ**. Không
reset volume hay chạy `schema.sql` để khắc phục khác biệt schema.

Import bản draft (ví dụ version 2 chưa tồn tại):

```bash
python -m apps.backend.db.import_structured \
  data/ingestion/corpus-v2/package.json
```

Importer ghi trong một transaction và PostgreSQL tự tạo FTS index từ passage
text. Draft chưa được retrieval phục vụ. Sau review, để publish pilot thủ công,
copy `package.json` ra `data/ingestion/package-v2-reviewed.json`, đổi
`release_status` từ `draft` sang `published` trong bản copy rồi import:

```bash
python -m apps.backend.db.import_structured \
  data/ingestion/package-v2-reviewed.json
```

Không chạy lại bản draft sau publish: importer hiện tại sẽ đổi trạng thái về
draft. Không dùng quy trình publish thủ công này thay protocol activation của
kiến trúc đích. Backend phải trỏ tới cùng database; endpoint chat đang có lỗi
wiring riêng cần sửa trước khi kiểm thử trả lời end-to-end.

## 5. Test

```bash
python -m unittest \
  apps.backend.tests.test_r2_ingestion \
  apps.backend.tests.test_structured_import
```

Các test kiểm tra HTTP CLI local, extraction PDF/HTML, exact spans, overlap,
checksum, repeatability, giới hạn kích thước, lỗi tải và không lộ chữ ký URL.
