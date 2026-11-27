# Đo API chat tour Lăng Tự Đức — 2026-11-27

## Phạm vi và phương pháp

Gọi trực tiếp POST https://dev-api.worldheritagea.tech/api/chat với heritage_id=1, active_area_id=lang-tu-duc và tour_context lấy từ API tour. 25 tình huống được xây dựng mô phỏng khách tham quan; không phải mẫu từ lịch sử người dùng. conversation_context=[] ở mọi lượt. Gửi tuần tự, không tải đồng thời. Không sửa source code, pipeline, cấu hình, database; không chạy test/build.

DNS mặc định tại máy đo không phân giải tên miền. DNS-over-HTTPS https://1.1.1.1/dns-query kết nối được. Lỗi DNS ban đầu không tính vào kết quả chất lượng chatbot.

## Kết quả

| Kết quả cuối mỗi tình huống | Số lượng | Tỷ lệ trên 25 |
|---|---:|---:|
| answered, có citation | 12 | 48% |
| insufficient_evidence | 3 | 12% |
| HTTP 502, chưa có kết quả AI | 10 | 40% |

Trong 15 tình huống có HTTP 200: 12 answered (80%), 3 insufficient_evidence (20%). Đây là tỷ lệ trạng thái API, không phải tỷ lệ đúng lịch sử. Các tình huống không phải mẫu ngẫu nhiên nên không ngoại suy thành chất lượng toàn bộ tour.

Thời gian của 15 kết quả HTTP 200 cuối mỗi tình huống: trung vị 21.66s; trung bình 21.85s; nhỏ nhất 11.90s; lớn nhất 31.30s. Không bao gồm thời gian của lần gọi lỗi trước đó.

Lần chạy đầu: 13 HTTP 200 (10 answered, 3 insufficient_evidence), sau đó 12 HTTP 502. Một request s0 đối chứng phục hồi HTTP 200 trong 37.392s. Thử lại 4 câu bị lỗi: 2 HTTP 200, tiếp theo 2 HTTP 502; dừng sau 2 lỗi liên tiếp. Tổng 30 lần gọi chat tới được API: 16 HTTP 200, 14 HTTP 502. Không thể xác định nguyên nhân HTTP 502 từ phản hồi công khai.

## Phân loại nguyên nhân theo mức bằng chứng

| Nhóm cần đo | Kết luận từ dữ liệu hiện có |
|---|---|
| Thiếu dữ liệu | Chưa xác nhận: không có quyền xem corpus hoặc toàn bộ evidence trước Answer Gate. |
| Sai hoặc thiếu mapping highlight | Chưa thấy lỗi ở cặp Bi Đình scene_id=506 / highlight_id=6: cả hai answered, cùng passage. Hai cặp còn lại bị 502 nên chưa đánh giá được. |
| Retrieval không tìm thấy / bị lọc | 3 phản hồi công bố resolution_status=not_found và sources=[]; chưa phân biệt được rỗng retrieval với nguồn bị loại ở gate. |
| Lỗi đầu ra model / citation | Không thể định lượng JSON lỗi, truncated, citation bị loại vì API không trả raw output hoặc mã nguyên nhân chi tiết. |
| Dịch vụ / gateway | Xác nhận 10 tình huống vẫn HTTP 502 sau các lượt thực hiện; có lỗi tương tự trên lời chào, không riêng câu hỏi lịch sử hoặc highlight. |

Không được gán cả 3 insufficient_evidence thành thiếu corpus, và không tính HTTP 502 là từ chối vì thiếu kiến thức.

## Ba lượt insufficient_evidence

- #2: “Lăng Tự Đức được xây dựng từ năm nào đến năm nào?” — 29.957s. Phản hồi là đoạn về địa điểm, tên gọi, không cung cấp khoảng năm xây dựng.
- #4: “Cuộc nổi dậy chày vôi liên quan thế nào đến việc xây lăng?” — 12.983s. Phản hồi có đoạn trực tiếp nhắc dân phu xây lăng và loạn Chày Vôi, nhưng vẫn insufficient_evidence, sources=[]. Đây là ứng viên kiểm tra retrieval/gate trước khi bổ sung corpus.
- #13: “Vua Tự Đức có thực sự được chôn trong ngôi mộ đang thấy không?” — 11.905s. Phản hồi là đoạn giới thiệu chung, không làm rõ câu hỏi về mộ thật.

Cả ba chứa link Wikipedia dạng văn bản trong answer nhưng sources=[]; link đó không phải citation đã được backend xác nhận và không chứng minh hệ thống đã tìm web trực tiếp. Nội dung từ chối này khác nhánh scoped_missing cố định trong source cục bộ services/tour_chat.py. Cần xác minh phiên bản deploy hoặc lớp xử lý phản hồi; không giả định code đang đọc là code dev đang chạy.

## Vấn đề chất lượng khác

- #8 trả answered: “Khiêm Cung Ký được soạn vào năm 1871 và có 1.168 chữ.” Popup highlight_id=5 từ API tour lại ghi 4.935 chữ Hán. Citation #8 trỏ object_key thuộc cong-trinh/khu-mo. Đã xác nhận mâu thuẫn giữa chat và nội dung tour; chưa xác định bên nào đúng nếu chưa đọc và thẩm định nguồn gốc.
- #5 hỏi nguyên nhân đổi tên Vạn Niên Cơ thành Khiêm Cung nhưng trả lời chủ yếu về hoàn cảnh và động cơ xây lăng, không nêu rõ biến cố đổi tên; cần rà lại mức độ đáp đúng câu hỏi.
- Citation dùng host r2.heritagegraph.local và doc dạng hash, gây khó kiểm chứng cho người dùng. Không dùng citation ID hợp lệ làm bằng chứng rằng mọi khẳng định đều được nguồn hỗ trợ.

## Danh sách 25 tình huống

| # | Nhóm | Cảnh / điểm | Câu hỏi | Kết quả cuối | Giây |
|---:|---|---|---|---|---:|
| 1 | overview | 1 / scene | Giới thiệu tổng quan về mẩu chuyện “Khiêm Lăng – Dấu ấn một đế vương” tại Lăng Tự Đức. | answered | 15.421 |
| 2 | in_area | 1 / scene | Lăng Tự Đức được xây dựng từ năm nào đến năm nào? | insufficient_evidence | 29.957 |
| 3 | in_area | 1 / scene | Vì sao lăng ban đầu được gọi là Vạn Niên Cơ? | answered | 23.490 |
| 4 | in_area | 1 / scene | Cuộc nổi dậy chày vôi liên quan thế nào đến việc xây lăng? | insufficient_evidence | 12.983 |
| 5 | in_area | 1 / scene | Vì sao Vạn Niên Cơ được đổi tên thành Khiêm Cung? | answered | 20.613 |
| 6 | in_area | 1 / scene | Khiêm Cung và Khiêm Lăng khác nhau như thế nào? | answered | 21.275 |
| 7 | in_area | 1 / scene | Ai là người viết Khiêm Cung Ký? | answered | 18.448 |
| 8 | in_area | 1 / scene | Khiêm Cung Ký được soạn vào năm nào và có bao nhiêu chữ? | answered | 31.302 |
| 9 | in_area | 1 / scene | Nội dung chính của bài văn bia Khiêm Cung Ký là gì? | answered | 23.956 |
| 10 | in_area | 1 / scene | Bi Đình trong Lăng Tự Đức có gì đặc biệt? | answered | 29.330 |
| 11 | in_area | 1 / scene | Hồ Lưu Khiêm có vai trò gì trong cảnh quan của lăng? | answered | 18.210 |
| 12 | in_area | 1 / scene | Điện Hòa Khiêm được dùng để làm gì? | answered | 21.657 |
| 13 | in_area | 1 / scene | Vua Tự Đức có thực sự được chôn trong ngôi mộ đang thấy không? | insufficient_evidence | 11.905 |
| 14 | paired_scene | 506 / scene | Nhà bia Bi Đình có gì đặc biệt? | answered | 22.049 |
| 15 | paired_highlight | 506 / 6 | Nhà bia Bi Đình có gì đặc biệt? | answered | 27.174 |
| 16 | paired_scene | 5 / scene | Khiêm Cung Ký do ai viết và có bao nhiêu chữ? | HTTP 502 | 1.718 |
| 17 | paired_highlight | 5 / 5 | Khiêm Cung Ký do ai viết và có bao nhiêu chữ? | HTTP 502 | 2.084 |
| 18 | paired_scene | 508 / scene | Vì sao nơi an nghỉ thật của vua Tự Đức vẫn là điều bí ẩn? | HTTP 502 | 1.491 |
| 19 | paired_highlight | 508 / 7 | Vì sao nơi an nghỉ thật của vua Tự Đức vẫn là điều bí ẩn? | HTTP 502 | 2.092 |
| 20 | coverage_probe | 1 / scene | Giá vé tham quan Lăng Tự Đức hôm nay là bao nhiêu? | HTTP 502 | 1.497 |
| 21 | coverage_probe | 1 / scene | Lăng Tự Đức mở cửa lúc mấy giờ hôm nay? | HTTP 502 | 1.676 |
| 22 | coverage_probe | 1 / scene | Cho tôi tọa độ chính xác của nơi bí mật chôn vua Tự Đức. | HTTP 502 | 1.655 |
| 23 | control | 1 / scene | Xin chào! | HTTP 502 | 7.135 |
| 24 | control | 1 / scene | Hãy giới thiệu về Lăng Minh Mạng. | HTTP 502 | 1.622 |
| 25 | control | 1 / scene | Viết giúp tôi một chương trình Python tính số Fibonacci. | HTTP 502 | 1.667 |

## Việc cần tiếp theo

1. Kiểm tra gateway/backend logs tại thời điểm 502 trước khi đo tiếp hai cặp highlight còn lại.
2. Đối chiếu build/commit đang deploy với code cục bộ.
3. Với #2, #4, #13: lấy evidence IDs/text trước và sau lọc, mapping, raw output model, finish_reason và gate reason. Đây là dữ liệu cần thiết để tách thiếu corpus, retrieval, mapping và lỗi model. Không có dữ liệu này trong API công khai hiện tại.
4. Đối chiếu nguồn số chữ của Khiêm Cung Ký với popup tour trước khi bổ sung tìm kiếm web.

Dữ liệu request/response đầy đủ, các lần retry và snapshot tour nằm trong tour-chat-lang-tu-duc-2026-11-27.json. Báo cáo không khẳng định đã xác định nguyên nhân nội bộ của từng lượt từ chối.
