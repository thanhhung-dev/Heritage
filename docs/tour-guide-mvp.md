# AI đồng hành tour — MVP kỹ thuật

Ngày kiểm tra: 2026-11-07. Phạm vi đã được người dùng duyệt trong thread
[AI đồng hành tour](https://ampcode.com/threads/T-01a1b651-f188-7522-b161-a06b61e70edf).

**Trạng thái:** source cục bộ đã nối ngữ cảnh/phiên và kiểm soát nhánh kể chuyện.
Chưa nghiệm thu toàn bộ MVP: thiếu tư liệu độc lập được duyệt cho Khiêm Lăng và
chưa chạy đánh giá retrieval/model thật. Không commit, push, migrate hay deploy.

## 1. Hành vi đã triển khai

- Cảnh thường vẫn chat được, không phụ thuộc Dive deeper. Explore suy ra từ
  route và dữ liệu: `standard`, `free`, `free_explore` → `walk`.
- Chọn điểm cập nhật ngữ cảnh dùng chung; đổi cảnh/thoát Explore xóa lựa chọn.
  Camera, hover, đổi cảnh và chọn điểm không tự gọi AI.
- Mỗi lần gửi chụp scene/mode/point. Phản hồi trễ vẫn mang nhãn lúc gửi; không
  bị đổi thành cảnh hiện tại. Metadata này cũng được lưu trong lịch sử hiện có.
- Backend xác minh quan hệ di sản đã xuất bản → scene → interaction → point
  bằng SQL. Không dùng tiêu đề do client gửi làm dữ kiện hoặc danh tính chuẩn.
- Hội thoại theo khu vực tiếp tục qua nhiều cảnh. Lịch sử giới hạn và điểm chọn
  cùng được truyền vào truy xuất/prompt. Đại từ có nhiều đối tượng hợp lý phải
  hỏi làm rõ; đây là chính sách prompt, cần đánh giá thêm với model thật.
- Nhánh biên soạn cần passage ID đã duyệt. Chỉ trả `story_id` khi câu trả lời
  `answered` trích đủ các passage đó. Không đủ bằng chứng thì không kể bù.
- Chỉ nhánh được trả lời thành công mới vào bộ nhớ tối đa 32 ID của phiên; gợi ý
  lọc những ID này. Lỗi, từ chối, timeout không đánh dấu đã kể. Người dùng vẫn
  có thể gõ yêu cầu nhắc lại. Không bảo đảm chống mọi lặp ngữ nghĩa trong chat tự do.
- Reload, mở hội thoại mới, đổi tài khoản/di sản reset bộ nhớ nhánh. Lịch sử
  tài khoản giữ cơ chế cũ; việc khôi phục chat không phục hồi tiến trình tour.
- Narration chỉ `completed` khi có `ended` và các khoảng `audio.played` phủ ít
  nhất 98% thời lượng. Skip là `skipped`; tua cuối/ghé cảnh không đồng nghĩa đã
  phát hết. Playback không chứng minh người dùng nghe hoặc hiểu nội dung.
- Một request đang chạy mỗi widget. Client hết chờ sau 35 giây, không tự retry;
  thông báo yêu cầu cũ có thể đã được server xử lý. Không có exactly-once guarantee.
- Nguồn hiển thị trong overlay, chỉ cho phép URL an toàn. Chat structured dùng
  `/api/chat/message` để nối đúng API lưu hội thoại; `/api/chat` cũ vẫn giữ nguyên.

Contract chi tiết: [`apps/backend/CHAT_API.md`](../apps/backend/CHAT_API.md).
Không đổi retrieval strategy, model, embedding, database schema, camera hay dependency.

## 2. Đối chiếu dữ liệu pilot

Nguồn danh tính: read-only GET development
`https://dev-api.worldheritagea.tech/api/heritages/lang-tu-duc/tour` trả 200.
Di sản ID 1, slug `lang-tu-duc`; các key thực là s0, s2, s3, s4, s5, **không có s1**.
DB ID, key cảnh, sequence và tên file audio không phải cùng một danh tính.

| Cảnh thật | Điểm tương tác thật | Narration đã nghe | Kết luận nhánh kể thêm |
| --- | --- | --- | --- |
| ID 3, s2, “Giấc mộng Khiêm Lăng” | Interaction 2, standard; point 4 “Tấm bia Khiêm Cung Ký”, point 3 “Văn tự trên bia” | `audio/s1.mp3`: nhà vua, sở thích văn chương, nơi tĩnh dưỡng khi còn sống, dẫn vào Bi Đình | Lịch sử xây dựng có thể là phần bổ sung, nhưng chưa tìm được passage độc lập phù hợp; chưa bật |
| ID 506, s3, “Khiêm Cung Ký – Lời tự thuật của nhà vua” | Interaction 4, standard; point 6 về nhà bia/Bi Đình | `audio/s2.mp3`: chủ yếu kiến trúc và chức năng bảo vệ của Bi Đình, không phải diễn giải chi tiết văn bia | Đã tìm được bài chính thức về văn bia; chưa có passage được duyệt trong kho để bật nhánh |
| ID 508, s5, “Lăng mộ – Bí ẩn nơi an nghỉ” | Interaction 5, standard; point 7 về nơi an nghỉ | `audio/s4.mp3`: kiến trúc, năm mất, bất định nơi chôn; có phân biệt giai thoại và lịch sử | Không khai thác giai thoại giật gân; chưa có nguồn độc lập cho nhánh mới |

Lưu ý chất lượng dữ liệu: point 2 của s2 mang tên “Giac Mong Khiem Lang” nhưng
text nói về chân bia. Metadata point 7 nhắc chuyện chém người khiêng quan tài và
tự ghi chưa kiểm chứng; bản audio được nghe không có cáo buộc đó. Không dùng các
nhãn/text này để tự biên soạn sử liệu. Audio xác minh tour đang nói gì, **không**
xác minh sự thật lịch sử. Các cảnh kiểm tra chưa có captions/timed highlights.

Đã đọc `data/knowledge.zip` tại chỗ: 103 file nội dung, 394.181 byte giải nén;
chủ yếu Thiên Mụ, Nguyễn Hoàng, Nguyễn Phúc Chu và bún bò Huế. Các đoạn nhắc Tự Đức
ở đó liên quan Thiên Mụ, không phải bằng chứng về lăng. Không tìm được passage
độc lập thích hợp cho ba cảnh trên trong gói cục bộ. Kho evidence trên development **chưa được
xác minh** vì không có interface đọc passage phù hợp được tìm thấy.

### Nguồn chính thức mới tìm được — chờ nhập kho/duyệt nhánh

[Bia Khiêm Cung Ký – Khiêm Lăng (lăng Hoàng đế Tự Đức)](https://hueworldheritage.org.vn/Di-san/Chi-tiet/tid/Bia-Khiem-Cung-Ky-Khiem-Lang-lang-Hoang-de-Tu-Duc/pid/6102E081-AD8E-4233-ADBE-AFB60104D5FE/cid/EC011130-B2C1-47C9-BCAD-AE660087B097),
ngày 27/02/2023, ký Bảo tàng Cổ vật Cung đình Huế, đăng trên cổng Trung tâm Bảo tồn
Di tích Cố đô Huế. Đã tải toàn bài bằng read-only GET HTTP 200 ngày 2026-11-07,
không chỉ dựa vào search snippet. Khi sử dụng ghi rõ nguồn theo yêu cầu website.

Bài xác nhận nhà vua tự soạn năm 1871; ghi “4.935 chữ Hán khắc trên cả hai mặt bia”;
mô tả nội dung “ghi lại quá trình xây dựng lăng, mô tả cảnh quan lăng, đồng thời
bày tỏ nỗi lòng của ông đối với đất nước cùng những việc riêng tư”. Đây là nguồn
độc lập với audio tour, nhưng **chưa phải passage đã có trong runtime retrieval**.

Hai câu hỏi ứng viên cho biên tập, chưa phải chip được bật:

- Point 4 của s2: “Khiêm Cung Ký khác các văn bia lăng Nguyễn ở điểm nào?”
- Point 3 của s2 hoặc nhánh scene s3: “Ngoài tự thuật, văn bia còn ghi lại những
  thông tin gì về khu lăng?”

Không biến mô tả tâm tư thành lời thoại/động cơ tự dựng. Chọn đoạn ngắn liên quan
Khiêm Lăng để nhập kho có provenance; không nhập cả trang chứa menu/dịch vụ hoặc
liên kết địa điểm khác. Chưa tự đặt passage ID, ghi vào kho dùng chung hay bật
registry. Mốc 4.935 dựa trên bài này, không suy ra từ ví dụ “4.000 chữ” ban đầu.

`services/tour_guide.py::GUIDE_STORIES` vì vậy để trống. Các gợi ý tổng quát
trước đây vẫn hoạt động dưới cổng bằng chứng; chúng không được quảng bá là nhánh
lịch sử đã duyệt. Chưa có cảnh đi bộ thật trong ba cảnh pilot; kiểm thử walk dùng
fixture được ghi rõ, không thay dữ liệu production.

## 3. Bằng chứng kiểm tra

### Automated và browser

- Backend: 27 targeted tests qua, kèm 43 subtests, cho scope/context, SQL ownership,
  citation gate, nối hội thoại và lưu/khôi phục snapshot qua cả hai router.
- Frontend: 19 targeted tests qua (18 request/suggestions/storage/scope và một
  snapshot/history); nhóm rộng hơn có lỗi cũ ghi riêng bên dưới. TypeScript qua.
- Lint các owner thay đổi không có error; còn warning dependency
  `interactive?.cam_pos` trong effect camera có từ trước, không sửa ngoài phạm vi.
- Chromium render các component thật với fixture mạng bị chặn toàn bộ ngoài máy
  cục bộ: cảnh thường, chọn A → B, thoát/vào Explore, nhánh thành công/thiếu nguồn,
  trả lời trễ sau khi chuyển cảnh, new conversation, walk không điểm chọn, lỗi và
  panel desktop/mobile. Ảnh được chụp sau animation và xem lại.
- Audio dùng HTMLAudioElement thật với WAV 8 giây và HTTP Range: Skip vẫn skipped;
  seek 7,98 → 8 chỉ có played `[7.98, 8]`, không completed; phát đủ thì completed.
- Đồng hồ trình duyệt mô phỏng quá 35 giây: hết loading, báo yêu cầu có thể đã
  được server xử lý, không retry. Đổi tài khoản khi đang chờ loại bỏ reply Guest cũ.
- Mock/network fixtures chứng minh orchestration và UI, không chứng minh chất
  lượng model, tính đúng lịch sử hoặc vận hành 3D end-to-end.

Các lệnh targeted (chạy bằng môi trường đã có, không cài dependency):

```text
python -m pytest apps/backend/tests/test_tour_context.py apps/backend/tests/test_tour_scope.py -q
python -m pytest apps/backend/tests/test_chat_conversation.py -k tour_snapshot -q
```

Tại `apps/frontend`:

```text
./node_modules/.bin/tsx --test tests/scene-chat-request.test.ts tests/scene-chat-suggestions.test.ts tests/tour-chat-scope.test.ts tests/conversation-storage.test.ts
./node_modules/.bin/tsx --test --test-name-pattern='tour replies' tests/chat-service.test.ts
./node_modules/.bin/tsc --noEmit --incremental false
```

### Lỗi có sẵn, không che bằng kiểm thử xanh

Đã chạy cùng các test trên snapshot `HEAD` chưa có thay đổi MVP:

- Frontend: kỳ vọng `ChatApiError` nhưng nhận `ApiError` khi hết phiên;
  kiểm thử raycast badge kỳ vọng null nhưng nhận ID 901.
- Backend conversation suite: 11 failure có sẵn ở đường chat không khóa khu vực,
  thiếu import `resolve_cited_source_ids` trong primary adapter. Không sửa vì
  không thuộc task. Test snapshot mới chạy qua cả hai adapter.

Log đối chứng và ảnh lưu trong `.amp/in/artifacts/mvp-*`; bản chụp checkout và
trang/script kiểm tra tạm được xóa sau xác minh. Không chạy full build hoặc full
suite toàn monorepo. Chưa đo được ngưỡng coverage 80%; không cài thêm tooling.

## 4. Cổng còn mở trước nghiệm thu

1. Cung cấp/duyệt passage độc lập về Khiêm Lăng, gắn đúng area provenance trong
   kho evidence hiện có; không chạy import hay sửa dữ liệu dùng chung ở task này.
2. Biên soạn 2–3 nhánh/cảnh theo ma trận audio, ghi passage IDs và đối chiếu từng
   khẳng định, rồi mới điền registry. Mẫu nguồn trong `area-locked-tour-guide.md`
   chỉ minh họa, không được dùng làm answer data.
3. Chạy retrieval và Qwen thực trên môi trường được phép: kiểm tra đại từ mơ hồ,
   nối chuyện s2 → s3 → s5, nhắc lại có chủ đích, câu thiếu nguồn và prompt injection.
4. Đo latency cùng tập câu hỏi trước/sau; health `model_ready=true` không thay
   cho một lượt sinh và đối chiếu nguồn thành công.
5. Chạy tour 3D tích hợp thật và kiểm tra điều khiển/playback, lịch sử tài khoản,
   Back/Forward; xử lý riêng các regression có sẵn nếu người dùng phê duyệt.

Local backend, llama server và OpenSearch chưa chạy; không tự bật Docker, không
gửi POST sang API development dùng chung. Không ký nghiệm thu model/nội dung hoặc
đưa vào production chỉ dựa trên các mock tests hiện tại.
