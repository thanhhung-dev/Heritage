# Test tay toàn bộ Backend của Khoa — Sprint 4

Đợt rà soát: 20/11/2026. Phạm vi BE-01 đến BE-10, đúng các dòng Backend giao cho Khoa trong bảng. “Manage Knowledge” ở đây là trạng thái **tài khoản**. Không bao gồm UI, lịch sử thao tác admin hoặc CRUD heritage của Hùng.

## 1. Khởi động bộ dữ liệu test riêng

Mở PowerShell tại repository:

```powershell
Set-Location 'C:\Capstone 1\Heritage'
$py='C:\Capstone 1\.venv\Scripts\python.exe'
& $py -X utf8 scripts/sprint4/manual_backend.py
```

PostgreSQL local và thông tin kết nối trong `.env` hiện có phải hoạt động; tài khoản PostgreSQL cần quyền tạo database test. Script tạo database mới tên ngẫu nhiên `test_sprint4_manual_*`, chạy API thật ở **http://127.0.0.1:18004/docs**, và in **mật khẩu ngẫu nhiên** dùng chung cho ba tài khoản test. Giữ terminal này mở.

| Dữ liệu | Giá trị ban đầu |
|---|---|
| Admin | `admin@example.com`, account ID `1` |
| User | `user@example.com`, account ID `2` |
| User bị vô hiệu hóa | `disabled@example.com`, account ID `3` |
| Heritage chính | ID `1`, slug `sprint4-test`, đã published |
| Heritage khác | ID `2` |
| Overview | Scene ID `1`, sequence `-1` |
| Hai scene chính | ID `2`, `3`, sequence `0`, `1` |
| Scene thuộc heritage khác | ID `4` |
| Model của scene 2 | Asset ID `1`, `models/camera.glb` |
| Model của scene 4 | Asset ID `2`, `models/foreign.glb` |
| Sky preset | ID `1` |

Đây là dữ liệu fixture để kiểm tra API và tham chiếu asset trong database. Các khóa GLB mẫu không phải file 3D được upload bởi script; việc hiển thị một mô hình thật trong UI là kiểm tra tích hợp frontend/asset riêng.

**Ctrl+C** sẽ dừng API/worker và dọn database, object R2 và index do script sở hữu. Chạy lại sẽ có dữ liệu sạch và mật khẩu mới. `.env` và database ứng dụng không bị sửa. Có thể đổi cổng bằng `--port 18005` nếu cổng 18004 đang được dùng.

Nếu chỉ cần chạy API với database dev đã chuẩn bị sẵn, dùng `python -X utf8 -m apps.backend`. Entry point này chọn event loop tương thích psycopg trên Windows; lệnh Uvicorn mặc định không có reload có thể trả 503 khi đăng nhập trên Windows.

## 2. Bật RAG thật để test đủ BE-06

Chế độ mặc định ở trên đủ để test auth, account, pipeline CRUD, scene và 3D. Để chạy reindex thật, dừng sandbox rồi mở hai terminal.

**Terminal A — OpenSearch test đã cài tại workspace này:**

```powershell
$ragSearchHome=(Get-Content -LiteralPath 'C:\Capstone 1\.rag-test-runtime\opensearch-short-path.txt' -Raw).Trim()
$env:OPENSEARCH_JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.6.7-hotspot'
$env:OPENSEARCH_TMPDIR='C:\CAPSTO~1\RAG-TE~1\tmp'
$env:TEMP=$env:OPENSEARCH_TMPDIR
$env:TMP=$env:OPENSEARCH_TMPDIR
$env:PATH="$ragSearchHome\plugins\opensearch-knn\lib;$env:PATH"
$env:OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m -XX:ActiveProcessorCount=4 -Djava.library.path=$ragSearchHome\plugins\opensearch-knn\lib"
& "$ragSearchHome\bin\opensearch.bat" -s
```

Đợi `http://127.0.0.1:19200` trả về cluster `sprint4-rag-verification`.

**Terminal B — API và worker thật:**

```powershell
Set-Location 'C:\Capstone 1\Heritage'
$py='C:\Capstone 1\.venv\Scripts\python.exe'
$env:OPENSEARCH_TEST_URL='http://127.0.0.1:19200'
$env:HF_HUB_CACHE='C:\Capstone 1\.rag-test-runtime\hf-hub'
$env:EMBEDDING_DEVICE='cpu'
$env:OMP_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
& $py -X utf8 scripts/sprint4/manual_backend.py --rag
```

Các biến R2 endpoint/key/bucket/prefix được đọc từ `.env` hiện có. Script tạo một file text kỹ thuật test trong prefix `sprint4-tests/<uuid>/`, đăng ký vào database test và in `RAG document_id`. API và worker dùng cùng database, JWT và index test. BGE-M3 dùng đúng revision đã cache, không tự download. Lần chạy đầu có thể cần chờ model nạp vào RAM.

Chế độ `--rag` chỉ dùng cluster test có tên trên. Object R2 được kiểm tra owner và ETag trước khi xóa. Không sửa file tri thức có sẵn hoặc index ứng dụng. Khi test xong, Ctrl+C terminal B, đợi thông báo cleanup, rồi Ctrl+C terminal A.

## 3. BE-01/02 — Admin login, quyền admin, logout

1. Trong Swagger, mở **POST `/api/admin/login`**, bấm **Try it out**. Gửi email `admin@example.com` và mật khẩu in ở terminal. Kỳ vọng **200**, có `access_token`, `token_type=bearer`, `user.role=admin`; không có password/hash.
2. Lưu token thành `ADMIN_TOKEN`. Bấm **Authorize**, dán **chỉ token**, không thêm chữ `Bearer`; Swagger tự thêm header. GET `/api/admin/rag/pipelines` → **200**.
3. Logout trong hộp Authorize để bỏ header, GET lại pipelines → **401**.
4. Login admin bằng password sai/email không tồn tại → **401**. Dùng tài khoản user với đúng password tại admin login → **403**.
5. POST `/api/auth/login` bằng `user@example.com` → **200**. Lưu `USER_TOKEN`, Authorize bằng token này; GET pipelines, GET scene hoặc PUT 3D → **403**. Chuyển Authorize về `ADMIN_TOKEN` để tiếp tục.
6. **Sau khi hoàn tất các module bên dưới**, POST `/api/admin/logout` bằng `ADMIN_TOKEN` → **204**; gọi lại → **204**; dùng token đó GET pipelines → **401**. Login lại và dùng token mới → **200**.

Token admin hết hạn sau 60 phút; token hết hạn phải nhận 401. Các trường hợp JWT giả, hết hạn và nhiều cách mã hóa cùng chữ ký được kiểm tra tự động trong `test_admin_auth.py`.

## 4. BE-03/04 — Bật/tắt tài khoản và phiên đang hoạt động

Dùng `USER_TOKEN` còn hiệu lực, GET `/api/auth/me` → **200**, sau đó Authorize lại bằng `ADMIN_TOKEN`.

1. PATCH `/api/admin/accounts/2/status` với `{"is_active":false}` → **200**, `is_active=false`.
2. Chuyển sang `USER_TOKEN` cũ; GET `/api/auth/me` → **401** ngay ở request tiếp theo. POST public login bằng user đó → **403**.
3. Authorize lại bằng admin; PATCH cùng body lần nữa → **200**, không làm lỗi hoặc tăng generation thêm lần nữa.
4. PATCH `{"is_active":true}` → **200**. `USER_TOKEN` cũ vẫn GET me → **401**. Public login lại lấy token mới; token mới GET me → **200**.
5. Authorize lại bằng admin. Body `{"is_active":"false"}` hoặc `{"is_active":1}` → **422**; ID `999` → **404**; ID `0` → **422**.

Không dùng account 1 để thử khóa ở bước này: khóa chính admin sẽ kết thúc phiên quản trị của bạn. Nếu muốn kiểm tra self-deactivation, làm cuối cùng rồi khởi động lại sandbox.

## 5. BE-05 — Pipeline CRUD

Authorize bằng admin. POST `/api/admin/rag/pipelines`:

```json
{"name":"Manual RAG","chunking":{"max_chars":200,"overlap_chars":20}}
```

Kỳ vọng **201**, lưu `id` thành `PIPELINE_ID`, revision ban đầu `1`.

1. GET list và GET theo ID → **200**, dữ liệu khớp. GET list với `limit=1`, dùng `next_cursor` nếu có; không lặp/mất pipeline giữa các trang khi dữ liệu không thay đổi.
2. PATCH theo ID: `{"expected_revision":1,"retrieval":{"top_k":7}}` → **200**, revision `2`, top_k `7`.
3. Gửi lại PATCH với expected_revision `1` → **409**, dữ liệu không bị ghi đè.
4. POST trùng tên → **409**. POST tên khác nhưng chunking `max_chars=100, overlap_chars=50`, hoặc retrieval `top_k=101`, hoặc embedding model khác → **422**.
5. Tạo một pipeline thứ hai tên `Delete me`, chưa trigger job. DELETE nó → **204**; GET nó → **404**.

Giữ `PIPELINE_ID` đầu tiên cho BE-06. Retrieval config được lưu; thao tác này không tự thay đổi chiến lược retrieval đang phục vụ chat. PATCH một section thay cả section đó, các trường không gửi trong section lấy giá trị mặc định.

## 6. BE-06 — Trigger reindex và trạng thái thật

Cần sandbox chạy với `--rag`. Dùng `RAG document_id` vừa in ở terminal:

```json
{"document_ids":["<RAG document_id>"]}
```

POST `/api/admin/rag/pipelines/{PIPELINE_ID}/reindex` → **202**, status **PENDING**. Lưu `id` thành `JOB_ID`.

1. GET `/api/admin/rag/jobs/{JOB_ID}` nhiều lần: PENDING → RUNNING → **COMPLETED**. Job nhanh có thể hoàn tất trước lần GET đầu. Kỳ vọng `processed_documents=1`, `indexed_passages>0`, started_at/finished_at có giá trị, error=null. Không có phần trăm tiến độ giả.
2. Gửi trigger thứ hai khi job đầu còn PENDING/RUNNING → **409**. Nếu job đầu đã terminal, một job mới được phép chạy. Không thể yêu cầu luôn nhận 409 sau khi job đầu hoàn tất.
3. Khi job đang active, PATCH config → **409**. DELETE pipeline có bất kỳ lịch sử job nào → **409**, kể cả job đã hoàn tất.
4. Document ID UUID không tồn tại → **404**; danh sách rỗng/trùng UUID → **422**; bỏ token → **401**; dùng user token → **403**.
5. Kiểm tra thất bại: sau khi không còn job active, Ctrl+C **OpenSearch ở terminal A**, rồi trigger một job khác. Poll đến **FAILED**, error đã được làm sạch, finished_at có giá trị. Khởi động lại OpenSearch trước khi trigger lại; worker vẫn chạy trong terminal B. Sau khi phụ thuộc hoạt động trở lại, một job mới phải có thể COMPLETED.

Nếu PENDING không đổi, kiểm tra worker terminal B có đang chạy. FAILED cần kiểm tra R2/model/search và revision nguồn. Nếu worker bị cưỡng bức kết thúc giữa job, RUNNING cần operator đối soát; API không cung cấp cancel/retry hay tự phục hồi job bị crash. Với sandbox, Ctrl+C và chạy lại sẽ tạo bộ dữ liệu mới.

## 7. BE-07/08 — Scene CRUD, liên kết và sắp xếp

Dùng heritage ID `1` và admin token.

1. GET `/api/admin/heritages/1/scenes` → overview ID 1 và scene ID 2,3 theo sequence. GET detail ID 2 → **200**; dùng heritage ID 2 với scene ID 2 → **404**.
2. POST scene `{"title":"Manual scene","description":"API test"}` → **201**, heritage_id `1`, sequence append `2`; lưu ID thành `NEW_SCENE`.
3. PATCH scene mới `{"title":"Updated scene","description":null}` → **200**, rồi GET xác nhận. Không cho PATCH heritage_id hoặc sequence → **422**.
4. POST scene thứ hai với sequence đã dùng → **409**. Title rỗng hoặc sequence `-2` → **422**.
5. PATCH `/api/admin/heritages/1/scenes/order`:

```json
{"scene_ids":[3,2,5],"expected_scene_ids":[2,3,5]}
```

Trong bộ dữ liệu mới, NEW_SCENE là `5`. Nếu ID trả về khác 5, thay cả hai số 5 bằng ID thực tế. Kỳ vọng **200**, sequence mới `0,1,2`; overview vẫn `-1`. Gửi lại nguyên body → **409** do expected order đã cũ. Đổi scene_ids thành `[3,3,2]`, bỏ một scene hoặc thêm scene `4` của heritage khác → **422** khi expected_scene_ids phản ánh đúng thứ tự hiện tại; dữ liệu không đổi.

6. DELETE scene mới → **204**; GET lại → **404**. API không xóa file R2 khi xóa scene. Test tự động PostgreSQL còn xác nhận cascade asset và interactive/highlight nhiều tầng.
7. Có thể thử hai cửa sổ gửi cùng một yêu cầu reorder với cùng expected order: một request **200**, request còn lại **409**. Bộ kiểm thử PostgreSQL đã chạy trường hợp đồng thời này.

ID là định danh ổn định. Sau reorder, public slug s1/s2 được tính lại theo sequence; UI không nên dùng slug làm định danh cố định của scene.

## 8. BE-09/10 — Cấu hình 3D và kiểm tra tham chiếu

PUT `/api/admin/scenes/2/3d-config`:

```json
{
  "camera": {
    "node_name":"Camera_Main",
    "start_position":[1,2,3],
    "start_target":{"x":0,"y":0,"z":0},
    "path_url":"models/camera.glb",
    "instant_move":true
  },
  "sky_preset_id":1,
  "model_asset_ids":[1]
}
```

1. PUT → **200**. GET cùng URL → **200**, nội dung khớp. path_url có thể được ghép CDN theo cấu hình R2 hiện có.
2. GET `/api/heritages/sprint4-test` → **200**; tìm scene ID `2` trong `scenes` (vị trí có thể thay đổi sau reorder). Camera, sky và model phải khớp dữ liệu vừa lưu.
3. PUT `{"camera":{"node_name":"Reset"}}` → **200**; start_position/start_target/path_url/sky được xóa, instant_move=false. Các model vẫn thuộc scene. Đây là **PUT thay thế**, không phải PATCH.
4. Lần lượt gửi: vector thiếu phần tử; tọa độ string/boolean; chỉ position không target; position=target; tọa độ lớn hơn 1000000; instant_move dạng string → **422**.
5. path_url `../private.glb`, `file:///x.glb`, `models/%2e%2e/x.glb` → **422**. Dùng `models/foreign.glb`, model_asset_ids `[2]`, `[999]` hoặc sky_preset_id `999` → **422**.
6. Sau mỗi PUT bị từ chối, GET lại xác nhận cấu hình trước đó không đổi. Scene `999` → **404**. User token → **403**; không token → **401**.

model_asset_ids chỉ kiểm tra tham chiếu đã đăng ký đúng scene; không chuyển quyền sở hữu hoặc chọn/xóa LOD. Sky preset dùng chung được tham chiếu, không bị sửa toàn cục.

## 9. Hoàn tất và bằng chứng

Thực hiện logout ở mục 3, sau đó Ctrl+C sandbox và đợi thông báo dọn tài nguyên. Với `--rag`, thông báo phải gồm xóa R2 + HEAD 404, xóa index/pipeline test và xóa database test. Nếu thông báo owner/ETag thay đổi, script sẽ từ chối xóa object đó để operator kiểm tra.

Muốn tự chạy nhanh kiểm chứng lại chính server HTTP thật thay cho thao tác Swagger:

```powershell
& $py -X utf8 scripts/sprint4/manual_backend.py --check
# Với cấu hình RAG của mục 2:
& $py -X utf8 scripts/sprint4/manual_backend.py --rag --check
```

Kết quả rà soát và các lệnh regression nằm trong [backend-reaudit-2026-11-20.md](backend-reaudit-2026-11-20.md); contract đầy đủ trong [backend-api-contract.md](backend-api-contract.md).
