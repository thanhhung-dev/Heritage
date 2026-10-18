# Kế hoạch nâng cấp kiến trúc sau Schema v2

Ngày cập nhật: 2026-09-10.

Tài liệu này mô tả công việc tiếp theo từ `schema_v2.dbml`. Đây là kế hoạch triển khai, không phải xác nhận các thành phần dưới đây đã chạy. Không thay thế hoặc mặc định mở rộng phạm vi đã thống nhất trong proposal.

## 1. Những gì đã sửa

- Đổi `entity.embedding` từ `vector1024` thành `vector(1024)`.
- Thêm bảng `entity_alias`, loại alias, điểm confidence và tham chiếu nguồn.
- Thêm `source_document_id`, `source_passage_id` cho `entity` và `site`.
- Bắt buộc `site.entity_id`.
- Thêm unique `(scene_id, lod_level)` cho `model_asset`.
- Bắt buộc `citation.quote`.
- Ghi chú các ràng buộc SQL cần triển khai cho citation, chat và feedback.

Hiện tại, các thay đổi trên mới nằm trong DBML. Chưa tạo migration, chưa import dữ liệu, chưa kết nối chatbot với PostgreSQL. Các `note` và comment không tự tạo SQL CHECK. Cú pháp DBML và SQL xuất ra cần được kiểm tra bằng công cụ trước khi sử dụng.

## 2. Kiến trúc đích

Giữ backend FastAPI dạng modular monolith, không tách microservices ở giai đoạn này.

```text
Frontend
  -> FastAPI /api/chat
     -> Chuẩn hóa câu hỏi + xác định intent
     -> Entity resolution
        -> PostgreSQL: tên chuẩn, alias, dữ kiện có nguồn
     -> Chọn đường truy vấn
        -> Structured lookup: địa chỉ, tọa độ, niên đại đã xác minh
        -> BM25 + graph: nội dung lịch sử và quan hệ
     -> Kiểm tra bằng chứng
     -> Template hoặc LLM diễn đạt
     -> Response: câu trả lời + nguồn + gợi ý xác nhận tên

Admin được xác thực
  -> Kiểm tra dữ liệu và nguồn
  -> PostgreSQL
  -> Tái tạo search index / graph theo phiên bản

3D Viewer
  -> FastAPI: metadata site / scene / hotspot
  -> Object storage hoặc CDN: GLB / audio
```

PostgreSQL lưu dữ liệu chuẩn và trạng thái ứng dụng. BM25 và graph là các cấu trúc phục vụ truy vấn có thể tái tạo. Giữ llama.cpp cho sinh câu trả lời. Chưa cần Neo4j, vector database riêng, event bus hoặc agent framework.

## 3. P0: Chốt schema trước khi tạo migration

Các điểm sau vẫn còn trong file DBML hiện tại và cần xử lý, không nên coi schema đã hoàn chỉnh.

- [ ] Chọn `entity_alias` làm nơi quản lý alias duy nhất; bỏ `entity.aliases` để tránh hai bản dữ liệu lệch nhau. Nếu đã có dữ liệu thực tế thì chuyển dữ liệu trước khi bỏ cột.
- [ ] Thay unique toàn cục trên `normalized_alias` bằng unique `(entity_id, normalized_alias)` và index thường trên `normalized_alias`. Hai địa danh khác nhau có thể trùng tên; resolver phải trả nhiều ứng viên thay vì cấm lưu.
- [ ] Phân biệt tên chính thức, tên lịch sử và lỗi gọi nhầm. Không mặc định coi “Lăng An Định” là tên gọi hợp lệ của “Cung An Định”; lưu dạng gợi ý sửa lỗi đã được duyệt và yêu cầu xác nhận khi chưa chắc chắn.
- [ ] Xác định `entity.name` là tên chuẩn. Bỏ `site.name` nếu không cần tên hiển thị riêng, hoặc ghi rõ đây là tên hiển thị, không phải nguồn định danh thứ hai.
- [ ] Chốt quan hệ site/entity là một-một hay một-nhiều trước khi thêm unique. Kiểm tra entity của site có loại `place`.
- [ ] Bổ sung bản ghi vị trí có cấu trúc: entity, địa chỉ, đơn vị hành chính, tọa độ, nguồn, trạng thái duyệt và thời gian hiệu lực. Schema hiện tại chưa có dữ liệu đủ để trả lời chính xác câu hỏi “ở đâu”.
- [ ] Tách địa chỉ hiện tại và lịch sử bằng thời gian hiệu lực; không trộn tên phường cũ với địa chỉ hiện tại. Không lấy ví dụ địa chỉ trong hội thoại làm dữ liệu đã xác minh.
- [ ] Bảo đảm `source_passage_id` thuộc đúng `source_document_id`, hoặc chỉ lưu passage rồi suy ra document để tránh hai FK mâu thuẫn.
- [ ] Thêm `relation_evidence` nếu cần nhiều nguồn cho cùng quan hệ. Giữ unique bộ ba trong `relation`; nhiều nguồn nằm trong bảng evidence.
- [ ] Chốt cách biểu diễn năm và loại di sản: predicate `XÂY_NĂM`, `LÀ_LOẠI` hiện trỏ tới entity nhưng danh sách loại entity chưa có year/category. Dùng dữ kiện có kiểu hoặc mở rộng loại đích phù hợp.
- [ ] Chốt versioning của document và passage. Offset của passage phải tham chiếu đúng phiên bản raw text; không sửa raw text làm hỏng trích dẫn cũ. Tính bất biến cần được thực thi, không chỉ ghi chú.
- [ ] Chốt liên kết message/citation: dùng bảng nối có FK nếu cần truy vết; nếu giữ JSONB thì định nghĩa cấu trúc và kiểm tra ID tại application layer.
- [ ] Sửa mặc định JSONB `citations` thành biểu thức PostgreSQL hợp lệ, ví dụ `'[]'::jsonb`, rồi kiểm tra SQL xuất từ DBML.
- [ ] Chỉ bắt buộc nguồn cho câu trả lời khẳng định dữ kiện. User message, lời chào, yêu cầu làm rõ và từ chối hợp lệ không cần citation; thêm loại phản hồi nếu cần biểu diễn quy tắc này.
- [ ] Chọn embedding model trước khi cố định 1024 chiều. Nếu chưa dùng vector retrieval, hoãn cột và extension thay vì thêm phụ thuộc không sử dụng.

**Điều kiện hoàn thành:** schema parse được; SQL xuất ra được review; có quyết định rõ cho alias trùng tên, dữ kiện vị trí và provenance.

## 4. P1: PostgreSQL và migrations

- [ ] Thêm PostgreSQL vào `docker-compose.yml`, volume bền vững và healthcheck. Không công khai cổng database nếu không cần.
- [ ] Cấu hình `DATABASE_URL` bằng môi trường; không commit mật khẩu. Cập nhật `.env.docker.example` bằng giá trị mẫu.
- [ ] Thêm SQLAlchemy, driver PostgreSQL và Alembic theo cách quản lý dependency hiện tại của apps.backend.
- [ ] Tạo migration đầu tiên từ schema đã chốt; không dùng tự động tạo bảng để thay thế lịch sử migration.
- [ ] Thực thi CHECK cho role, loại entity/alias, confidence trong [0,1], rating trong {-1,1}, offset hợp lệ, thời lượng và kích thước không âm.
- [ ] Thực thi CHECK citation có đúng một nguồn; kiểm tra JSONB là array trước khi áp dụng quy tắc số lượng nguồn.
- [ ] Chọn chính sách xóa cho từng FK. Không cascade xóa evidence đang được dùng để kiểm chứng câu trả lời cũ; cân nhắc withdraw/version thay vì xóa cứng.
- [ ] Thêm index cho đường truy vấn thực tế: alias chuẩn hóa, passage theo document, graph theo subject/object, message theo session và thời gian.
- [ ] Viết bài kiểm tra database từ chối dữ liệu vi phạm CHECK, unique và FK.
- [ ] Kiểm tra migration trên database trống và quy trình backup/restore với database thử nghiệm.

**Điều kiện hoàn thành:** database khởi động được, dữ liệu tồn tại sau restart, migration áp dụng thành công và kiểm thử constraint chạy trên PostgreSQL thật.

## 5. P2: Import corpus và nguồn có cấu trúc

- [ ] Đọc lại `apps/backend/core/corpus.py`, `apps/backend/core/kg.py` và các script ingestion trước khi viết importer; tái sử dụng quy tắc chunking hiện có.
- [ ] Import document, passage, entity, alias và quan hệ bằng khóa nguồn ổn định; chạy lại không sinh bản ghi trùng.
- [ ] Lưu phiên bản corpus và ánh xạ ID cũ sang UUID để truy vết nguồn hiện tại.
- [ ] Kiểm tra quote/offset với đúng văn bản gốc; lưu URL lấy từ metadata nguồn, không để LLM tạo URL.
- [ ] Nhập và duyệt dữ kiện vị trí từ nguồn đáng tin, ghi ngày kiểm tra và thời gian hiệu lực khi có.
- [ ] Không tự gán confidence=1 cho mọi alias nhập vào; điểm matching không tương đương xác suất đúng đã hiệu chỉnh.
- [ ] Đối chiếu số lượng tài liệu/đoạn và kiểm tra các nguồn mồ côi sau import.
- [ ] Tái tạo BM25/graph theo phiên bản và chỉ chuyển sang index mới khi build thành công, tránh trộn database mới với cache cũ.

**Điều kiện hoàn thành:** import lặp lại không tạo trùng; mỗi dữ kiện dùng trả lời có nguồn truy vết được; index khớp phiên bản dữ liệu.

## 6. P3: Nâng cấp luồng chatbot

Các điểm tích hợp hiện có: `apps/backend/core/fuzzy_match.py`, `apps/backend/core/retriever.py`, `apps/backend/core/rag.py`, `apps/backend/api/chat.py`.

- [ ] Resolve theo thứ tự exact, normalized, alias rồi fuzzy; trả entity ID và danh sách ứng viên thay vì chỉ thay chuỗi tên.
- [ ] Dùng chính entity ID đã chọn xuyên suốt retrieval và generation. Không sửa tên ở đầu ra nhưng vẫn truy vấn theo tên cũ.
- [ ] Khi có nhiều ứng viên gần nhau, trả yêu cầu chọn; không tự sửa chỉ vì còn một ứng viên nếu confidence chưa đủ.
- [ ] Thêm intent router tối thiểu: vị trí, lịch sử, niên đại, làm rõ và ngoài phạm vi.
- [ ] Với câu hỏi vị trí, ưu tiên dữ kiện đã duyệt và template. Nếu thiếu dữ kiện, tìm đoạn có bằng chứng hoặc thông báo thiếu nguồn, không tự điền địa chỉ.
- [ ] Giữ BM25 + graph cho câu hỏi mô tả; đo hồi quy trước khi thay đổi các cổng từ chối hiện có.
- [ ] Chỉ gắn citation thực sự hỗ trợ dữ kiện được trả lời. Câu lịch sử về một nhân vật không tự động chứng minh địa chỉ của di tích.
- [ ] Giới hạn LLM diễn đạt từ evidence được chọn; kiểm tra có citation không chưa đủ chứng minh câu trả lời đúng.
- [ ] Giữ API và frontend đồng bộ khi thêm entity ID, intent hoặc loại phản hồi. Tận dụng các trường hiện có `corrected_from`, `corrected_to`, `needs_user_choice`, `suggestions`.

**Điều kiện hoàn thành:** câu hỏi đúng tên, không dấu và tên gọi nhầm đi tới cùng thực thể khi đủ căn cứ; trường hợp mơ hồ yêu cầu xác nhận; không có nguồn thì không khẳng định địa chỉ.

## 7. P4: Admin, bảo mật và quan sát

- [ ] Xác thực và phân quyền trước khi mở API ghi dữ liệu; chatbot không được tự sửa dữ kiện chuẩn.
- [ ] Thêm workflow draft/reviewed/published/withdrawn cho nội dung cần duyệt và ghi audit log.
- [ ] Thiết kế session có hết hạn, thu hồi và cookie an toàn nếu dùng cookie; một token hash không tự cung cấp đầy đủ vòng đời session.
- [ ] Xác định thời gian giữ/xóa chat, feedback và IP hash. Không dùng IP hash làm danh tính hoặc bằng chứng xác thực người dùng.
- [ ] Ghi thời gian retripipelines/evaluation/generation, intent, entity đã chọn, phiên bản corpus/model và lý do từ chối; tránh log token, mật khẩu hoặc dữ liệu cá nhân không cần thiết.

**Điều kiện hoàn thành:** đường ghi được bảo vệ, thay đổi có người chịu trách nhiệm và có thể điều tra câu trả lời sai theo phiên bản dữ liệu.

## 8. P5: Triển khai nội dung 3D sau khi lõi QA ổn định

- [ ] Chốt 3D có nằm trong phạm vi nâng cấp lần này không trước khi triển khai storage và viewer.
- [ ] Lưu RAW riêng tư; lưu GLB/audio đã xử lý ở object storage; PostgreSQL chỉ giữ metadata và khóa/URL phù hợp.
- [ ] Bổ sung trạng thái xử lý/publish, checksum, license và nguồn gốc asset; liên kết bản processed tới RAW nếu cần tái xử lý.
- [ ] Chốt uniqueness LOD theo biến thể: `(scene_id, lod_level)` hiện cấm proxy và bản render cùng cấp. Nếu cần cả hai, bổ sung variant/purpose vào khóa sau khi xác định quy tắc.
- [ ] Chuẩn hóa transform: 7 DoF dùng translation 3 chiều, rotation quaternion và scale đồng nhất dạng số; scale độc lập ba trục là mô hình khác. Kiểm tra quaternion hợp lệ và cùng hệ tọa độ giữa LOD/hotspot.
- [ ] Validate camera keyframe tham chiếu scene tồn tại và cùng site; JSONB không tự cung cấp FK cho scene ID bên trong.
- [ ] Kiểm tra thời gian transcript, thứ tự đoạn và sự đồng bộ với narration. Nếu cần nhiều ngôn ngữ, thay quan hệ narration một-một và gắn transcript vào đúng bản narration.
- [ ] Kiểm thử progressive loading, raycast proxy, hotspot, lỗi tải asset và khả năng dùng trên mobile.

**Điều kiện hoàn thành:** một site mẫu chạy xuyên suốt từ storage đến viewer, có nguồn/giấy phép và không phụ thuộc vào việc tất cả địa danh đều có mô hình 3D.

## 9. Kiểm thử và chuyển đổi

- [ ] Chạy bộ kiểm thử hiện có, đặc biệt `apps/backend/tests/test_retriever_regressions.py`, trước khi sửa luồng truy vấn để chốt baseline.
- [ ] Thêm test cho “Cung An Định ở đâu?”, “cung an dinh o dau”, “lăng an định ở đâu”, tên trùng, tên không tồn tại và nguồn không có địa chỉ.
- [ ] Thêm test địa chỉ lịch sử/hiện tại, passage không thuộc document, citation mồ côi, alias trùng giữa nhiều entity và import chạy hai lần.
- [ ] Kiểm tra lời chào, yêu cầu làm rõ và user message lưu được mà không có citation.
- [ ] Đánh giá retrieval và độ trung thực citation riêng biệt; lấy đúng tài liệu không có nghĩa là câu trả lời đã đúng.
- [ ] Chạy API/LLM integration trên môi trường thử nghiệm, kiểm tra frontend hiển thị chọn tên và nguồn đúng.
- [ ] Trước cutover, backup dữ liệu, chốt phiên bản ứng dụng/database/index và chuẩn bị phương án khôi phục đã thử nghiệm. Không dùng downgrade phá dữ liệu làm phương án rollback mặc định.

## 10. Thứ tự thực hiện đề xuất

1. Chốt các vấn đề schema P0, validate DBML và SQL.
2. PostgreSQL, migration và kiểm thử ràng buộc.
3. Import corpus cùng dữ kiện vị trí có nguồn.
4. Entity resolution, intent router và kiểm chứng nguồn.
5. Tích hợp chatbot/frontend và đo hồi quy.
6. Admin, bảo mật và vận hành trước khi mở sử dụng thực tế.
7. 3D theo phạm vi đã xác nhận.

Mốc đầu tiên nên nhắm tới: **câu hỏi vị trí trả về dữ kiện có nguồn từ đúng entity, xử lý được tên mơ hồ và không bịa khi thiếu bằng chứng**. Không cần hoàn thiện toàn bộ 3D hay thêm vector search để đạt mốc này.
