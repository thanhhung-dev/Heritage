# Bàn giao AI tham quan: P1, P2 và thử Qwen3-4B

**Quyết định đã chốt:** AI tham gia mỗi lượt chat trong tour để hiểu ý và diễn đạt; server luôn giữ phạm vi địa điểm/cổ vật, giới hạn tư liệu và kiểm tra đầu ra. Làm server P1–P2 trước, thử Qwen3-4B *chưa fine-tune* sau, chỉ fine-tune khi đo được lỗi lặp lại. Đây là đặc tả để giao việc, **không xác nhận code đã triển khai hay cho phép deploy/migration**.

Đọc `AGENTS.md` trước khi thực hiện. Theo quy trình của repo, trình kế hoạch sửa file để người dùng duyệt **trước khi viết source code**; không chạy full build/test khi mới phân tích. Chỉ làm phần người dùng giao và đã duyệt, không tự đổi retrieval strategy, model production, database schema hay cấu hình production.

## Hiện trạng cần đọc trước khi sửa

- `apps/frontend/features/chat/TourChatWidget.tsx` gửi `active_area_id`, `heritage_id` và `tour_context.highlight_id`; `apps/frontend/lib/tour-chat-scope.ts` kiểm tra phản hồi từ tour. Không thay camera hoặc tương tác 3D.
- `apps/backend/services/tour_guide.py::resolve_tour_context` xác minh marker thuộc scene, heritage đã xuất bản và mode; `TourReplyContext.highlight_title` lấy từ DB. Tên popup là nhãn nhận diện, **không phải bằng chứng lịch sử**. `GUIDE_STORIES` hiện rỗng.
- `apps/backend/services/tour_scope.py` xác định 5 khu vực; `question_outside_area` hiện nhận diện một số nơi khác và `scoped_refusal` trả câu cố định. `apps/backend/services/tour_chat.py::answer_in_area` hiện trả ngay `out_of_scope` trước khi gọi model; lời chào cũng trả ngay. Cả hai nhánh này phải được xem lại để đạt yêu cầu **AI tham gia mọi lượt chat hợp lệ trong tour**.
- `apps/backend/ai/retrieval/passages.py` lấy đoạn tư liệu OpenSearch hybrid và tùy chọn GraphRAG, lọc theo **địa điểm**, chưa có ánh xạ đáng tin từ `highlight_id` tới passage. GraphRAG không tự là bằng chứng. `apps/backend/ai/answering/conversation.py` quy định JSON `answer_type`, `source_ids` và prompt; `tour_chat.py` xác nhận ID trích dẫn, nhưng ID hợp lệ **chưa chứng minh từng mệnh đề được nguồn hỗ trợ**.
- Hai luồng API phải đồng nhất: `POST /api/chat` và `POST /api/chat/message` (`apps/backend/api/public/chat/router.py`, `apps/backend/api/conversations.py`). Luồng sau lưu lịch sử và `reply_context`; `apps/frontend/services/chatService.ts` kiểm tra snapshot của scene/marker.
- Tư liệu pilot về Khiêm Lăng còn thiếu: xem `docs/tour-guide-mvp.md`. Không tự ghi passage ID, không đưa popup/audio/giai thoại chưa xác minh vào kho làm nguồn. Các scene key thực tế không nhất thiết liên tiếp.

## P1 — phạm vi địa điểm

**Khi đang tham quan Khiêm Lăng, mọi lượt chat hợp lệ đều gọi AI một lần để hiểu và diễn đạt**, kể cả lời chào và câu hỏi rõ ràng về địa điểm khác. Server xác minh khu vực, chỉ cung cấp passage thuộc khu vực đó, không để AI đổi tour; câu hỏi ngoài phạm vi là **phản hồi chat bình thường** `answer_type="out_of_scope"`, `sources=[]`, không phải HTTP exception. Trường hợp xác minh ngữ cảnh thất bại hoặc service lỗi giữ lỗi API hiện hành; nếu model lỗi/vượt phạm vi thì dùng lời đáp an toàn.

- Hỏi về địa điểm hiện tại: AI trả lời chỉ từ passage phù hợp, dẫn `source_ids` hợp lệ; không đủ bằng chứng thì nói rõ chưa xác nhận được chi tiết nào.
- Hỏi địa điểm khác: AI diễn đạt giới hạn một cách tự nhiên, nhắc tên nơi khác **chỉ để chỉ đường**, không trình bày dữ kiện lịch sử về nơi đó. Ví dụ: “Mình đang đồng hành cùng bạn tại Khiêm Lăng. Nếu muốn tìm hiểu Lăng Minh Mạng, bạn có thể mở tour của nơi đó nhé. Còn ở Khiêm Lăng, bạn muốn tìm hiểu lịch sử hay kiến trúc?” Chỉ mời mở tour đã biết là tồn tại; không tự tạo URL.
- Hỏi mơ hồ (“lăng kia”, “ông ấy”): dùng lịch sử trong phạm vi để hiểu; nếu vẫn không rõ thì hỏi lại, không đoán tên người/nơi. Hỏi chủ đề không liên quan thì nêu ngắn gọn giới hạn và gợi ý quay về tour.
- Duy trì hậu kiểm và fallback cho output sai. `allowed_output` hiện xem *mọi tên địa điểm khác* là sai; cần phân biệt **nhắc tên trong lời điều hướng** với **kể dữ kiện về nơi khác**. Không bỏ cổng kiểm tra để làm câu từ chối trông tự nhiên hơn. Prompt, dữ liệu truy xuất và lịch sử hội thoại không được tự thay đổi `active_area_id`.
- Giữ API response đang dùng: `active_area_id`, `answer_type`, `sources`, `follow_up_questions`, `reply_context` khi có tour context. Chưa thêm nút/URL chuyển tour hoặc đổi schema frontend.

## P2 — phạm vi cổ vật/marker trong Dive Deeper

Áp dụng thêm P2 khi **một marker có danh tính cổ vật đáng tin và đang được chọn**. Server xác minh `highlight_id` thuộc đúng scene/mode/heritage, rồi xác định cổ vật A; không dùng tiêu đề do client tự gửi làm danh tính hay bằng chứng. Bỏ chọn marker trở lại P1; các marker không phải cổ vật tiếp tục theo phạm vi địa điểm, không ép thành cổ vật.

- AI vẫn tham gia mỗi lượt chat; prompt hướng về A và các mối liên hệ với A. Server chỉ cung cấp passage có **liên kết được kiểm chứng với A**; cách liên kết có thể là danh mục biên tập marker → passage ID/alias đáng tin, không suy ra từ việc passage thuộc cùng địa điểm hoặc có một từ trùng tên.
- Hỏi A: trả lời chi tiết nào có nguồn cho chi tiết ấy. Nếu thiếu đúng chi tiết được hỏi nhưng có **dữ kiện liên quan** đã xác minh, nêu rõ phần chưa biết rồi chia sẻ phần biết được kèm citation. Ví dụ: có nguồn vua Tự Đức tự soạn **nội dung** văn bia thì vẫn không được suy ra ông trực tiếp **khắc chữ**. Hỏi nhân vật/sự kiện có quan hệ với A: chỉ cho phép kể quan hệ khi passage chứng minh; câu hỏi gợi mở tiếp theo cũng phải gắn A hoặc quan hệ có nguồn. Không hứa “câu chuyện kỳ lạ” nếu không có tư liệu về câu chuyện đó.
- Hỏi cổ vật B cùng địa điểm: AI hướng sang B, không trả lời dữ kiện về B. Chỉ nêu tên cảnh/marker nếu server tìm được **duy nhất một** điểm B trong scene/heritage đã xác minh; nếu chưa biết vị trí, chỉ hướng về trang khám phá/đề nghị làm rõ, **không đoán cảnh 4**. Hỏi địa điểm khác ưu tiên xử lý P1 trước P2.
- Không có thông tin liên quan hữu ích: dùng `insufficient_evidence`, không bịa. Không viết “đã tra nhiều nguồn” nếu server chưa thực sự tra; không biến một sự kiện chỉ có nguồn tham khảo trên web thành tư liệu nội bộ đã kiểm duyệt. Nguồn nội bộ có thể là văn bản lưu trong kho với provenance và ID; popup, audio, trí nhớ model và graph không phải nguồn độc lập. Tìm web khi thiếu chi tiết, kể cả đã trả lời được một phần, là **giai đoạn riêng** cần duyệt nhà cung cấp và API trước khi thực hiện.
- Chưa chốt cách lưu ánh xạ marker–passage/quan hệ. Trước P2, kiểm kê marker và evidence thực có; đề xuất registry biên tập nhỏ trong code nếu đủ nguồn, hoặc trình người dùng duyệt phương án DB/migration khi cần quản trị dữ liệu. **Không tự tạo sự kiện, quan hệ, passage ID hay dữ liệu production** để lấp chỗ trống.

## Tiêu chí kiểm tra P1–P2

Sau khi được duyệt triển khai, mở rộng test hiện có trong `apps/backend/tests/test_tour_scope.py`, `test_tour_context.py`, `test_chat_api.py`, `test_chat_conversation.py` và chỉ thêm frontend tests nếu đổi UI/contract. Test bằng generator/repository giả được kiểm soát; với câu tour hợp lệ, chứng minh AI được gọi đúng một lần, còn request sai danh tính bị chặn trước AI.

1. Đúng địa điểm, có passage: trả lời có `source_ids` thuộc phạm vi. Nếu chỉ biết phần liên quan, nêu phần đó cùng citation và nói rõ phần chưa xác nhận; không từ chối toàn bộ. Thiếu passage hoặc chỉ có passage về nơi/cổ vật khác: không trả lời dữ kiện.
2. Hỏi nơi khác bằng tên rõ ràng và cách nói mơ hồ: lời đáp hợp lý, không có citation ngoài phạm vi, không HTTP error cho từ chối. Input yêu cầu “bỏ qua phạm vi”, câu nhắc nơi khác trong lịch sử/passage và model trả lời sai phải không mở khóa tour.
3. Marker A đang chọn, hỏi về A hoặc nhân vật gắn A có passage: trả lời/gợi ý xoay quanh A. Hỏi B: chỉ nêu scene nếu lookup từ DB chính xác và duy nhất; không tự bịa scene khi B vắng hoặc trùng tên. Bỏ marker trở lại phạm vi địa điểm.
4. `reply_context`, `answer_type`, `sources`, `follow_up_questions` hợp lệ trên **cả hai** API, gồm lịch sử hội thoại đã lưu. Model timeout/JSON lỗi/sai phạm vi phải có đường xử lý an toàn, không lộ thông tin không được kiểm chứng.

Chạy **targeted tests** sau khi sửa source, rà Git diff và ghi rõ điều nào đã kiểm thực tế, điều nào bị chặn vì thiếu passage. Chưa có bằng chứng end-to-end với corpus thật thì không tuyên bố đã chứng minh được chất lượng câu kể.

## Thử Qwen3-4B trước khi fine-tune

Chỉ chuyển sang đây **sau khi hành vi P1–P2 và định dạng prompt/response đã ổn định**. Không đổi model đang chạy production khi chưa được duyệt. Trình tự:

1. Chạy bản Qwen3-4B *chưa fine-tune* trên môi trường thử nghiệm, giữ cùng chat template, `enable_thinking=false`, prompt, evidence và kiểm tra đầu ra như khi serve. Dùng một bộ câu hỏi có đáp án đối chiếu do người biên tập duyệt: đúng địa điểm/cổ vật, nhầm địa điểm/cổ vật, hỏi mơ hồ, thiếu bằng chứng, lời nhắc độc hại trong passage, quan hệ được và không được chứng minh. Đánh giá qua cả server, không chỉ hỏi model độc lập.
2. Chấm ít nhất: đúng/sai phạm vi, tỷ lệ trả lời có căn cứ theo từng mệnh đề, citation đúng, xử lý không đủ nguồn, JSON hợp lệ, chất lượng kể chuyện; đo độ trễ và ghi từng lỗi có câu hỏi + passage + kết quả mong muốn. Không cần đặt ngưỡng đạt tùy tiện trước khi có số liệu baseline.
3. Chỉ nếu lỗi lặp lại mới tạo dữ liệu fine-tune về **hành vi**, không nhồi kiến thức lịch sử vào model. Train/valid/test tách theo passage hoặc cổ vật để tránh trùng nội dung; huấn luyện chỉ sau khi duyệt dữ liệu và phần cứng.

**Đừng chạy script cũ nguyên trạng:** `pipelines/training/lora_config.yaml` đã cấu hình `Qwen/Qwen3-4B`, nhưng mặc định của `pipelines/training/train_hf.py` và `score_gold.py` trỏ tới `training/lora_config.yaml` (thư mục này không có trong checkout). `score_gold.py` còn dùng `apps/backend/core/prompt.py` và bộ gold QA/NER cũ, không đo đủ contract chat tour ở `apps/backend/ai/answering/conversation.py`. Kiểm tra và căn chỉnh đường dẫn, prompt, dữ liệu đánh giá trước; không báo số liệu cũ là hiệu năng P1/P2.

## Ngoài phạm vi tài liệu giao việc này

Chưa xây web fallback, networkx/graph quan hệ mới, nút điều hướng frontend, migration, cập nhật dữ liệu chung, chạy training hoặc deploy. Các việc đó cần phương án và phê duyệt riêng. Nếu P2 thiếu nguồn được xác minh, báo rõ thiếu gì và dừng ở mức hành vi an toàn thay vì dựng tư liệu giả.
