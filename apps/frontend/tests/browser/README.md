# Kiểm thử trình duyệt cho Knowledge Library

Chạy từ `apps/frontend`, dùng Node 22 trở lên và Edge/Chrome có CDP. Bộ kiểm thử chỉ chấp nhận địa chỉ `127.0.0.1`. Dữ liệu mẫu nằm trong tiến trình fixture, không nằm trong mã sản phẩm. Các PUT đến `r2.example.invalid` bị CDP chặn và trả phản hồi giả; không ghi hay xóa R2 thật.

## Chuẩn bị

Chọn các cổng còn trống. Các ví dụ dưới đây dùng frontend 3006, fixture 18927 và CDP 9225. Mở terminal riêng cho mỗi dịch vụ.

Terminal 1 — API giả lập:

```powershell
$env:KNOWLEDGE_FIXTURE_PORT = '18927'
node tests/browser/knowledge-fixture.cjs
```

Terminal 2 — frontend dùng API giả lập:

```powershell
$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:18927/api'
npm run dev -- --port 3006
```

Terminal 3 — Edge với profile riêng, không dùng profile cá nhân:

```powershell
$edgePath = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$reviewProfile = Join-Path $env:TEMP ('heritage-knowledge-' + [guid]::NewGuid().ToString('N'))
$browserProcess = Start-Process -FilePath $edgePath -WindowStyle Hidden -PassThru -ArgumentList @(
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=9225', ('--user-data-dir="' + $reviewProfile + '"')
)
```

## Chạy

Terminal 4:

```powershell
$env:KNOWLEDGE_FIXTURE_URL = 'http://127.0.0.1:18927'
$env:KNOWLEDGE_FRONTEND_URL = 'http://127.0.0.1:3006'
$env:KNOWLEDGE_CDP_URL = 'http://127.0.0.1:9225'
node tests/browser/knowledge-browser.cjs
```

Ảnh được lưu mặc định trong `.next/knowledge-browser-review/`. Đặt `KNOWLEDGE_BROWSER_ARTIFACTS` nếu muốn thư mục khác. Mỗi lần chạy fixture được reset; script chỉ đóng tab do nó tạo. Dừng hai server bằng Ctrl+C tại terminal tương ứng và dừng đúng `$browserProcess.Id` tại terminal 3 sau khi kiểm tra xong.

Nếu frontend đang chạy với một cổng API giả lập loopback khác, có thể đặt `KNOWLEDGE_BROWSER_API_PROXY` bằng origin API đó. Script sẽ chuyển tiếp các request Knowledge trong tab kiểm thử sang fixture riêng. Không dùng tùy chọn này với API thật.

## Phạm vi xác nhận

- Khung thư viện desktop 1920×1200: x=284, y=28, rộng 1612, cao 1144.
- Modal nền trắng, chọn thư mục thật từ fixture, chọn File và upload bằng XHR của ứng dụng.
- Header PUT không chứa Authorization; có MIME, `If-None-Match` và upload ID đúng; trạng thái Stored chỉ xuất hiện sau complete.
- Tạo thư mục cập nhật cây; xóa đúng key cập nhật danh sách; HTML trong preview không thực thi.
- Library, upload, details, metadata, review và ingestion ở desktop và mobile 390×844; modal mobile không tràn ngang.
- Trạng thái rỗng, 503, 401 và 403; không có JavaScript exception. Request CDP bị hủy do điều hướng được ghi riêng.

Đây là kiểm thử trình duyệt với API/R2 giả lập. Nó không xác nhận cấu hình CORS, credentials, migration hay khả năng kết nối Cloudflare của môi trường triển khai thật. Các trường hợp retry, mất phản hồi, 412, timeout và hủy upload được kiểm tra thêm trong `tests/knowledge-*.test.ts`.
