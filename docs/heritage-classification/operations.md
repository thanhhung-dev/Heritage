# Vận hành phân loại di sản và kho cổ vật

Nhánh triển khai: `feat/heritage-classification-artifact-collection`, từ `develop` tại `0bcab82`. Không có migration/backfill nào được chạy lên database ứng dụng hoặc production trong đợt triển khai này.

## Chuẩn bị và migration

Backend dùng dependency hiện có trong `apps/backend/requirements.txt`, gồm Alembic **1.18.4**. Frontend dùng package lock hiện có; manifest khai báo Node 24.x. Kiểm tra DB đang trỏ đúng môi trường trước khi áp dụng migration:

```powershell
Set-Location 'C:\Capstone 1\Heritage'
$py='C:\Capstone 1\.venv\Scripts\python.exe'
& $py -m alembic -c apps/backend/alembic.ini current
& $py -m alembic -c apps/backend/alembic.ini heads
# Xuất riêng SQL mới để review, không kết nối/chỉnh sửa DB:
& $py -X utf8 -m alembic -c apps/backend/alembic.ini upgrade 20261119_highlight_passage:head --sql |
  Set-Content -Encoding utf8 catalog-upgrade-review.sql
```

Revision mới là `20261120_classification`, sau `20261119_highlight_passage`. Khi operator triển khai vào DB dev/staging đã kiểm tra:

```powershell
& $py -m alembic -c apps/backend/alembic.ini upgrade head
```

Nếu DB đang ở revision cũ hơn, lệnh trên còn chạy những migration cũ đang thiếu: review chúng trước, không `stamp` giả để bỏ qua. DB local đã kiểm tra trong phiên này có 0 heritage và còn thiếu migration marker cũ; không có dữ liệu production được suy ra từ DB đó.

Migration mới chỉ tạo bảng/trigger, sao chép metadata hiện có sang projection và enqueue job. Không sửa `heritage`, media URL, `publish_state`, KG entity hoặc marker hiện có. Không tạo cổ vật, lễ hội hay nhân vật từ văn bản. Không dùng `init_db` thay cho migration này: catalog cần cả constraint và trigger, không chỉ bảng ORM. Legacy initializer được giới hạn để không tạo trước các bảng catalog thiếu trigger. Một phép thử bootstrap toàn bộ ORM còn gặp lỗi FK `user_profile.account_id -> admin_account` có sẵn ở model legacy; đường migration catalog không phụ thuộc vào việc sửa mapping đó.

## Worker tự động

Sau migration, chạy worker ở terminal/service riêng:

```powershell
& $py -X utf8 -m apps.backend.services.classification_worker
# Xử lý các job đang sẵn sàng rồi thoát:
& $py -X utf8 -m apps.backend.services.classification_worker --drain
# API Windows, dùng entry point đã có của develop:
& $py -X utf8 scripts/run-backend.py
```

Hoặc dùng service Compose opt-in, sau khi image và các biến Compose hiện có đã được chuẩn bị:

```text
docker compose --profile classification up -d classification-worker
```

Service chỉ phụ thuộc PostgreSQL; không yêu cầu OpenSearch hoặc LLM để phân loại bằng rules. Không có Docker service nào được khởi động trong phiên triển khai này. File Compose gốc có các biến Langfuse bắt buộc khi nội suy, kể cả profile khác: cần cấu hình sẵn hoặc dùng worker native ở trên. Kiểm tra cấu trúc Compose đã chạy thành công bằng placeholder không bí mật, không phải bằng credentials production.

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | Bắt buộc | Cùng PostgreSQL đã migrate với API |
| `HERITAGE_CLASSIFICATION_HIGH` | `0.9` | Ngưỡng tự áp dụng |
| `HERITAGE_CLASSIFICATION_MEDIUM` | `0.55` | Từ ngưỡng này đến high: chờ duyệt |
| `HERITAGE_CLASSIFICATION_USE_LLM` | `false` | Bật rõ ràng mới dùng provider llama.cpp hiện có |
| `LLAMA_SERVER_URL` | Theo cấu hình hiện có | Chỉ dùng khi LLM opt-in; request tối đa 20 giây |

Worker đọc source theo job, không quét knowledge documents. Chỉ dùng tóm tắt KG được liên kết rõ ràng, tên khớp chủ thể, trạng thái reviewed/published và có tham chiếu nguồn. Thay đổi/thu hồi entity KG liên kết sẽ enqueue lại. Marker/voice không tự trở thành nội dung catalog.

Mỗi content chỉ có một row queue; revision mới thay generation cũ. Worker claim bằng `FOR UPDATE SKIP LOCKED`, lease 120 giây, tối đa 5 lần thử, backoff lũy tiến tối đa 300 giây. Lease hết hạn được thu hồi; kết quả từ generation/lease cũ bị bỏ qua. Requeue cùng generation đang PENDING/RUNNING là idempotent. Lỗi job chỉ lưu loại lỗi đã làm sạch. `--drain` thoát khi không còn job sẵn sàng, không chờ đến giờ retry tương lai.

## Backfill có preview và rollback

```powershell
# Chỉ đọc, không LLM/network và không ghi classification:
& $py -X utf8 scripts/classify-heritage.py --dry-run --limit 1000
# Sau khi đọc báo cáo, operator áp dụng trên DB đã chọn:
& $py -X utf8 scripts/classify-heritage.py --apply --limit 1000
# Dùng next_after_id trong báo cáo để tiếp tục batch kế tiếp:
& $py -X utf8 scripts/classify-heritage.py --apply --limit 1000 --after-id <next_after_id>
# Phục hồi classification của một batch:
& $py -X utf8 scripts/classify-heritage.py --rollback <run_id>
```

Lặp batch đến khi `next_after_id=null`; lưu từng `run_id` để rollback theo thứ tự ngược. Báo cáo JSON có nhãn PREVIEW/APPLIED/UNCHANGED/SKIP_LOCKED/SKIP_CHANGED/SKIP_BUSY. Chạy lại không tạo classification trùng. Batch không giành job đang có lease hợp lệ.

Rollback chỉ phục hồi category/type/trạng thái phân loại nếu revision hiện tại và snapshot sau áp dụng vẫn khớp audit. Nội dung được sửa hoặc admin duyệt lại sẽ nhận SKIP_CONFLICT. Không khôi phục đè title, URL, trạng thái xuất bản hoặc lựa chọn featured. Sau rollback, job được để DONE để không tự áp dụng ngược trở lại; requeue rõ ràng nếu muốn phân loại tiếp. Schema downgrade bị chặn để bảo vệ dữ liệu đã duyệt; đây là rollback dữ liệu classification, không phải DROP bảng.

## API và duyệt thủ công

Swagger/OpenAPI nằm ở `/docs` và `/openapi.json` của backend. Các API heritage/tour/chat cũ được giữ nguyên.

| API public | Kết quả |
|---|---|
| GET `/api/catalog/categories` | 14 taxonomy key và tên hiển thị |
| GET `/api/catalog/contents?category=museum&entity_type=place&limit=20&offset=0&sort=title` | Danh sách published, classification applied và đúng revision |
| GET `/api/catalog/sections?limit=8` | Năm section, mỗi section có items và next_offset |
| GET `/api/catalog/sections/{section}?limit=8&offset=8&sort=newest` | Trang tiếp theo của section |
| GET `/api/catalog/contents/{slug}` | Chi tiết và related_entities đã published |

`limit` tối đa 100 (endpoint gộp sections tối đa 30), `offset` tối đa 10000; sort title hoặc newest, tie-break bằng ID. Category/type dùng làm filter đúng taxonomy, không dùng region hay publish_state làm loại. Public API không gọi LLM, không đọc toàn bộ corpus, không truy vấn theo từng card. Response `Cache-Control: no-store`; homepage refetch mỗi 30 giây khi visible, khi focus/online và có nút tải thêm. Phân loại pending/review/unclassified hoặc stale không xuất hiện công khai.

Các endpoint `/api/admin/catalog` yêu cầu bearer token ADMIN hiện hành; kiểm tra thêm role, active và locked_until từ account/roles trong DB. Token có claim admin nhưng tài khoản thực là user bị từ chối. Dùng login hiện có `/api/auth/login` và Authorize trong Swagger.

| API admin | Mục đích |
|---|---|
| GET `/contents?status=review&after_id=0&limit=20` | Queue duyệt; có thể lọc pending/applied/unclassified |
| GET `/contents/{id}` | Input revision, source, category/confidence/reason và khóa |
| POST `/contents` | Tạo thực thể độc lập artifact/collection/event/person/practice, yêu cầu source_url |
| PATCH `/contents/{id}` | Sửa thực thể độc lập hoặc chọn featured/rank; cần expected_revision |
| PUT `/contents/{id}/classification` | Duyệt category/type, lý do và locked; cần expected_revision |
| POST `/contents/{id}/reclassify` | Enqueue/retry, giữ nguyên khóa admin |
| GET `/contents/{id}/job` | Trạng thái, generation, attempts và lỗi đã làm sạch |
| POST `/contents/{id}/relations` | Liên kết located_at/held_at/member_of/associated_with/depicts kèm nguồn |

Payload duyệt một bảo tàng có kiến trúc đã xác minh:

```json
{
  "expected_revision": 1,
  "entity_type": "place",
  "categories": ["museum", "architecture"],
  "primary_category": "museum",
  "reasoning_summary": "Phân loại dựa trên nguồn tư liệu đã được người quản trị kiểm tra.",
  "locked": true
}
```

Thay revision bằng giá trị GET hiện tại. Muốn bỏ khóa, PUT lại phân loại đã kiểm tra với `locked=false`, sau đó reclassify khi cần. Worker không được tự ghi đè category đã khóa. Entity độc lập phải có type phù hợp hint đã duyệt; muốn sửa type thì PATCH hint hợp lệ trước. Không thể tạo place độc lập giả; place sử dụng heritage gốc. Khi sửa text/ảnh/publish của heritage, sửa **bảng heritage**, không sửa projection catalog. Admin PATCH projection không cho đổi các trường nguồn đó.

Các fact `period`, `material`, `origin`, `custodian` phải có dạng `{"value":"...","source_url":"https://..."}`. Chỉ điền giá trị đã xác minh; bỏ trống khi chưa có nguồn. API không suy đoán niên đại/chất liệu. Có thể liên kết `knowledge_entity_id`, `source_document_id`, `interactive_highlight_id` đã tồn tại thay vì tạo bản sao phục vụ RAG.

## Chính sách homepage

- Featured: opt-in `is_featured=true`; place cần tour có scene và model reference, practice cần primary cultural_experience; luôn published/applied/current/có ảnh hợp lệ theo URL policy.
- Artifacts & Treasures: thực thể **collection** đã có nguồn, không phải mọi bảo tàng.
- Kho tàng Cổ vật & Hiện vật: thực thể **artifact** riêng, kể cả artifact từ bản ghi heritage legacy nếu dữ liệu chủ thể chứng minh đúng loại.
- People & Traditions: person thật hoặc practice có primary tradition/craft/intangible; không lấy voice/narrator làm person.
- Festivals & Community Practices: event thật hoặc practice có primary ritual/festival; card mang tên chính lễ hội/thực hành, quan hệ held_at dẫn đến địa điểm.

Mỗi entity chỉ có một placement homepage để không lặp card. Nhiều category hợp lệ vẫn được giữ cho việc tìm theo taxonomy. Các section chưa có nội dung hiển thị empty state; không đổ dữ liệu giả hoặc đổi ảnh di sản thành ảnh cổ vật để lấp chỗ trống. Ảnh được kiểm tra syntax/allowlist tại API; không HEAD toàn bộ R2 trong request render. File media 404 vẫn cần operator sửa bằng dữ liệu thực.

## Kiểm tra tại local mà không động vào DB ứng dụng

```powershell
& $py -X utf8 scripts/verify-catalog.py apps/backend/tests/test_catalog_postgres.py apps/backend/tests/test_catalog_api.py
$env:HF_HUB_CACHE='C:\Capstone 1\.rag-test-runtime\hf-hub'
# API và worker thật, DB test riêng; model cache cần cho startup hiện có của API:
& $py -X utf8 scripts/preview-catalog.py --check
# Fixture UI có nhãn rõ ràng, chỉ ở DB test tự tạo:
& $py -X utf8 scripts/preview-catalog.py --fixtures --check
```

Để xem UI, chạy preview không có `--check`, mặc định port 18008. Terminal frontend đặt `NEXT_PUBLIC_API_URL=http://127.0.0.1:18008/api`, chạy Next ở port 3006. `.env.local` hiện tại trỏ dev API khác: cần override biến trong process test, không sửa file cấu hình đó. Giữ terminal preview; Ctrl+C dừng các child và xóa đúng DB test do nó tạo. Fixture không phải dữ liệu lịch sử và không được seed lên production.

Tham chiếu migration đã đối chiếu: [Alembic offline scripts](https://alembic.sqlalchemy.org/en/latest/offline.html), [Operations.execute](https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.execute). Cả offline SQL lẫn upgrade thật đã được thực thi trong kiểm thử.
