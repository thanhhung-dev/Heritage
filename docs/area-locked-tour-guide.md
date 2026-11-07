# Area-Locked AI Tour Guide

Ngày kiểm tra: 07/11/2026. Nhánh: `feat/HER-area-locked-tour-guide`.

## Phạm vi và API

Widget 3D và chat thường dùng **POST `/api/chat/message`** để lưu hội thoại;
`POST /api/chat` vẫn giữ tương thích cho chat không lưu. Cả hai router
legacy/refactored dùng chung DTO. Chat thông thường chỉ gửi `message` vẫn hoạt động;
request có ngữ cảnh tour phải có `active_area_id`. Đây là phạm vi tham quan công
khai do client chọn, không phải cơ chế phân quyền tài khoản.

```json
{
  "message": "Vua Tự Đức sống ở đây thế nào?",
  "active_area_id": "khiem-lang",
  "heritage_context": {"slug": "lang-tu-duc"},
  "scene_context": {"key": "s0", "title": "Hòa Khiêm Điện"},
  "conversation_context": []
}
```

`khiem-lang`, `lang-tu-duc`, `tu-duc-tomb`, Khiêm Lăng và Lăng Tự Đức được backend
chuẩn hóa thành `khiem-lang`. Heritage slug trong context phải khớp area.
Registry còn có Lăng Minh Mạng, Đại Nội Huế, Lăng Khải Định và Chùa Thiên Mụ để
đổi phạm vi khi người dùng chủ động mở tour tương ứng. Slug chưa đăng ký bị khóa
chat ở widget; ID không hợp lệ hoặc context mâu thuẫn trả **422**.

Response giữ `answer`, `sources`, `answer_type`, bổ sung:

```json
{
  "active_area_id": "khiem-lang",
  "follow_up_questions": ["Lịch sử hình thành Khiêm Lăng (Lăng Tự Đức) như thế nào?"]
}
```

Các trường trên chỉ là phần bổ sung của response, không phải một response hoàn chỉnh.
Mỗi source của câu trả lời có căn cứ mang `active_area_id`, `passage_id`, tên nguồn
và URL nếu có. Widget từ chối response thiếu/sai area hoặc citation sai phạm vi;
vì vậy cần cập nhật backend trước khi dùng widget mới với API public cũ.

## Thông báo khi hỏi ngoài khu vực

Khi đang xem tour Khiêm Lăng và hỏi tổng quan “Cố đô Huế”, API trả **200** với
`answer_type="out_of_scope"`, `active_area_id="khiem-lang"`, `sources=[]` và câu trả lời:

> Bạn đang tham quan Khiêm Lăng (Lăng Tự Đức), nên hiện mình chỉ hướng dẫn và giải đáp về khu vực này. Nếu muốn khám phá nơi khác, bạn có thể mở tour tương ứng. Còn ở đây, bạn muốn cùng mình tìm hiểu lịch sử, kiến trúc hay những câu chuyện thú vị?

Đây là tin nhắn bình thường trong chat; không phải lỗi kết nối, không tự mở trang
hoặc đổi scope. Tên địa điểm lấy từ registry của area đang mở. Các chip gợi ý vẫn
chỉ hỏi về area hiện tại. “Cố đô Huế” là chủ đề rộng, không được gán thành alias
của Đại Nội. Câu hỏi nói rõ mối liên hệ của Khiêm Lăng trong quần thể Cố đô Huế
vẫn có thể truy xuất bằng chứng của Khiêm Lăng; không mở rộng kho dữ liệu.

## Các tầng khóa

1. Câu hỏi nêu di sản khác hoặc so sánh với di sản khác trong registry bị từ chối
   trước embedding, Hybrid search và LLM. Tên nhân vật như vua Tự Đức hoặc vua Minh
   Mạng không tự động bị coi là yêu cầu đi tới một lăng khác.
2. Câu hỏi truy xuất được gắn tên area hiện tại; **cả BM25 và kNN** lọc keyword
   `active_area_id` trước ranking. Passage thiếu/sai nhãn không được sử dụng.
   Repository và service kiểm tra lại metadata, text và tên nguồn trước prompt.
3. GraphRAG chỉ được chạy trên snapshot riêng của area. Không có snapshot phù hợp
   thì giữ Hybrid đã lọc; không chạy graph toàn cục rồi lọc kết quả sau.
4. System policy do server tạo tách khỏi dữ liệu người dùng. Scene label chỉ giúp
   hiểu câu hỏi, không phải bằng chứng; history tối đa 6 tin, 2.000 ký tự/tin và
   6.000 ký tự tổng, loại lịch sử đề cập địa điểm ngoài phạm vi. Description từ
   client không được dùng làm nguồn dữ kiện.
5. ID citation phải thuộc evidence đang dùng. Câu trả lời nêu địa điểm khác đã
   biết hoặc chèn liên kết điều hướng bị thay bằng lời nhắc phạm vi, bỏ sources.
   Lời đáp kiến thức không có citation không được xuất dưới nhãn `conversation`.
   Gợi ý không hợp lệ được thay bằng ba mẫu chỉ hỏi về area hiện tại.
6. Widget remount theo tour/account, abort request khi rời tour, bỏ callback cũ,
   xóa draft/messages/gợi ý khi đổi tour. Đổi scene trong cùng tour giữ hội thoại.
   Với tài khoản đăng nhập, server lưu hội thoại và cung cấp history theo ownership;
   client giữ UUID riêng theo tài khoản/tour để khôi phục khi mở lại. Guest giữ luồng
   hiển thị trong memory; UUID của record Guest không cho phép đọc hay nối tiếp.
   Đổi tour không được đổi scope trên cùng conversation. Chi tiết:
   [Chat API](../apps/backend/CHAT_API.md).

Kiểm tra tên địa điểm là quy tắc bảo thủ dựa trên alias do team quản lý, không phải
bộ nhận diện mọi địa danh hoặc bộ kiểm chứng ngữ nghĩa cho mọi câu do LLM sinh.
Metadata corpus phải được biên tập đúng; model vẫn cần đánh giá chất lượng riêng.

## Dữ liệu cần chuẩn bị trước khi hỏi kiến thức thực tế

Code mới không tự gắn nhãn theo title và không thay đổi index đang chạy. Chỉ
re-import **package đã được review**, vào index local/staging được chọn rõ ràng.
Gắn nhãn ở document hoặc từng passage; nhãn passage mâu thuẫn document sẽ bị từ chối:

```json
{
  "documents": [{"key": "tu-duc-source", "active_area_id": "khiem-lang"}],
  "passages": [{
    "id": "existing-reviewed-passage-id",
    "document_key": "tu-duc-source",
    "active_area_id": "khiem-lang",
    "text": "<nguyên văn nội dung Khiêm Lăng đã xác minh>",
    "source_url": "<URL nguồn công khai đã review>"
  }]
}
```

Đây là minh họa cấu trúc, không phải dữ liệu dùng để trả lời. Giữ metadata nguồn,
ID, object key và nội dung thật từ package hiện có. Importer giữ ID ổn định và thêm
keyword mapping vào index cũ khi chạy bước ingestion chủ động:

```powershell
# Từ repository root; chọn OPENSEARCH_URL/OPENSEARCH_INDEX local hoặc staging trước.
& "C:\Capstone 1\.venv\Scripts\python.exe" -X utf8 -m apps.backend.db.import_passages `
  "<reviewed-area-package.json>" --env-file .env
```

Tài liệu trộn nhiều di sản cần tách và review các passage trước khi gắn nhãn.
Passage không nhãn cũ vẫn dùng được cho chat thông thường nhưng bị loại khỏi tour.
Khi không tìm thấy evidence trong area, API lưu chat trả **201**, `insufficient_evidence`,
`sources=[]`; không bịa kiến thức để làm demo. Khi tắt local fallback, lỗi pipeline
ở API lưu chat trả **500**, inference quá 30 giây trả **504**; API transient giữ mã
lỗi cũ. Local fallback của tour trả abstention với `service_unavailable`, không
dùng nguồn mock hay Gemini toàn cục. `wait_for` giới hạn phản hồi, không thể buộc dừng
ngay một native inference đang chạy trong thread.

## GraphRAG riêng theo area (tùy chọn)

Chỉ thực hiện sau khi đã có passage đúng nhãn. Export sang thư mục snapshot mới:

```powershell
& "C:\Capstone 1\.venv\Scripts\python.exe" -X utf8 -m pipelines.graph.microsoft_graphrag export `
  --root "<new-khiem-lang-snapshot>" --active-area-id khiem-lang --limit 100 --env-file .env
# Chạy index bằng interpreter của môi trường GraphRAG riêng đã cài đặt sẵn:
& "<graphrag-python>" -X utf8 -m pipelines.graph.microsoft_graphrag index --root "<new-khiem-lang-snapshot>"
```

Truyền `GRAPHRAG_ENABLED=true`, `GRAPHRAG_PYTHON` và mapping JSON phía backend:

```text
GRAPHRAG_AREA_ROOTS={"khiem-lang":"C:/absolute/path/to/indexed-khiem-lang-snapshot"}
```

`GRAPHRAG_ROOT` toàn cục không được dùng cho request đã khóa. Manifest và toàn bộ
input phải cùng area, hash đúng, trước khi adapter khởi chạy worker. Worker kiểm
tra lại manifest và hash snapshot trước khi load/query communities, entities,
relationships. Graph context chỉ được đưa vào prompt khi lineage thuộc các
passage cùng area đã xác thực trong OpenSearch. Không cần GraphRAG để chạy Hybrid.

## Tự kiểm tra local

Widget còn có [gợi ý theo từng câu chuyện s0/s1…](scene-chat-suggestions.md):
chip đổi theo scene đang xem, giữ khóa di sản và không bị phản hồi cảnh cũ ghi đè.

Chạy backend theo cấu hình local của dự án, sau đó gửi request ở phần API vào
`http://localhost:8000/docs` hoặc bằng `Invoke-RestMethod`:

```powershell
$body = @{ message = "So với lăng Minh Mạng thì Khiêm Lăng khác gì?"; active_area_id = "khiem-lang" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/chat/message" `
  -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Mong đợi **201**, `out_of_scope`, chỉ nhắc phạm vi Khiêm Lăng, không citation
ngoài khu vực. Câu hỏi này hoạt động cả khi chưa có OpenSearch/LLM.

Với corpus đã index đúng nhãn và LLM đang chạy, hỏi “Vua Tự Đức sống ở đây thế
nào?”: nếu nguồn đủ thì `answered` với source đúng area; nếu nguồn chưa đủ phải
`insufficient_evidence`. Mở `/content/lang-tu-duc/s0` nếu slug này tồn tại trong
data local, kiểm tra suggestion chips và `active_area_id` trong request. Khi một câu hỏi còn đang
chờ, đổi sang tour khác: messages/draft/gợi ý cũ biến mất, response cũ không được
chèn vào tour mới. Tour chưa đăng ký như `tapestry-test` hiển thị trạng thái chưa
cấu hình area và không gửi chat toàn cục.

## Kết quả kiểm thử tự động

- 21 test trong `test_tour_scope.py` kiểm tra cả entry path legacy/refactored,
  DTO, cả nhánh Hybrid, Graph snapshot, citation, history, scene, timeout, model
  output và injection qua yêu cầu chuyển phạm vi.
- Lượt chạy chat/retrieval/ingestion/OpenSearch sau khi chỉnh thông báo:
  **48 passed, 6 skipped**, 79 subtests passed. 6 skip cần `OPENSEARCH_TEST_URL` thật.
- Lượt đối chiếu thêm GraphRAG trước lần chỉnh thông báo: **52 passed,
  6 skipped, 4 failed**, 77 subtests passed.
- 4 failure đều tái hiện trên bản gốc `fd13d62` với `python -X utf8`: hai test
  gọi `/api/graphrag/query` không được mount trong app hiện tại; hai test process
  dùng `venv/bin/python` và executable shebang dành cho Linux trên Windows.
  Không đổi endpoint không liên quan hoặc sửa test để che các lỗi này.
- Frontend: **8/8 tests** (scene transport và scope guard); TypeScript
  `npx tsc --noEmit --incremental false` và targeted Next ESLint đều pass.
- External embedding/LLM/process IO trong test area được mock. Chưa chạy E2E
  trình duyệt hoặc xác nhận câu trả lời model thật với corpus area-tagged.

Các số liệu trong mục trên là lượt kiểm tra area-lock ban đầu. Lượt hoàn thiện
chat ngày 07/11/2026 đã chạy **91 tests + 85 subtests pass**, migration trên Postgres
local đã được phê duyệt và HTTP thật thành công; xem
[báo cáo hiện tại](../apps/backend/CHAT_TASK_AUDIT.md). Không chạy production reindex,
deploy hoặc port 3000. Vẫn cần corpus area-tagged đã review và model thật để đánh
giá chất lượng trả lời kiến thức trên môi trường người dùng.
