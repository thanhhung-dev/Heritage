---
id: SPEC-heritagegraph-v2
companions:
  - features.md
  - fr-catalog.md
  - metrics-targets.md
  - architecture-principles.md
  - schedule.md
sources:
  - ../../docs/Project Title (VI).md
---

> **Hợp đồng chuẩn.** SPEC này và các tệp trong `companions:` là hợp đồng đầy đủ, đã kiểm chứng bảo toàn, cho việc xây dựng, kiểm thử và xác nhận. Tài liệu nguồn liệt kê ở frontmatter chỉ phục vụ truy vết.

# HeritageGraph v2.0 — Trợ lý GraphRAG cá nhân hóa cho văn hóa Huế – Đà Nẵng

## Why

Hai thất bại của hệ thống thông tin văn hóa hiện hữu: (1) **khám phá không cá nhân hóa** — mọi cổng di sản trả cùng một danh sách cho mọi người, trong khi sở thích văn hóa vừa rất riêng vừa cắt ngang danh mục (người quan tâm diễn xướng cũng muốn trang phục, nhạc cụ, làng nghề, lễ hội — nằm rải rác ở các bài viết khác nhau); (2) **hiểu không dẫn tới hành động** — trả lời "cái này là gì?" rồi dừng, trong khi nhu cầu thật là lịch, chỗ gửi xe, cần mang gì, bảo tàng nào đang giữ cổ vật. Dự án giải quyết cả hai **mà vẫn giữ tính kiểm chứng**: gợi ý giải thích được bằng đường đi đồ thị thật (không dùng lọc cộng tác — không có nền người dùng và không giải thích được), bối cảnh thực tế là bản ghi có kiểu có nguồn (không để LLM ứng viên bịa chỗ gửi xe hay bịa triều đại). Đây là capstone CMU-SE 450, 13 tuần còn lại, một người phát triển, đã có baseline đo được (recall@1 30/30, Micro-F1 0.786, từ chối 0.917).

## Capabilities

- **CAP-1**
  - **intent:** Người dùng hỏi đáp tiếng Việt bằng văn bản về văn hóa Huế–Đà Nẵng và nhận câu trả lời trích nguồn bắt buộc dạng `[Nguồn: <câu nguyên văn> — <url>]`, hoặc lời từ chối tường minh khi bằng chứng không đủ (ba cổng từ chối cấu trúc).
  - **success:** recall@1 ≥ 95% trong phạm vi; trung thực trích nguồn ≥ 85%; độ phủ trích nguồn ≥ 90% trên câu trả lời được; độ chính xác từ chối ≥ 90%; một câu khẳng định bịa trên câu hỏi ngoài phạm vi tính là lỗi.

- **CAP-2**
  - **intent:** Hệ thống duy trì nền tri thức: kho ngữ liệu ≥ 80 tài liệu, ≥ 8/danh mục trên 6 danh mục văn hóa; đồ thị tất định có nguồn gốc từng đỉnh; ba tập bản ghi có cấu trúc (≥ 50 địa điểm kèm tọa độ, ≥ 20 sự kiện kèm loại lịch + ngày + phần lễ/hội, ≥ 35 cổ vật kèm niên đại/chất liệu/bảo tàng/vị trí).
  - **success:** Mọi trường bản ghi mang URL nguồn + câu nguồn; bản ghi thiếu nguồn bị từ chối kèm lỗi ở mức trường; đồ thị 1 thành phần liên thông, 0 tài liệu cô lập, dựng lại trong dưới 1 giây (baseline 510 đỉnh / 1135 cạnh / 0,23s).

- **CAP-3**
  - **intent:** Hệ thống cá nhân hóa khám phá: hồ sơ sở thích từ chọn tường minh (F05) + tương tác ngầm định có suy giảm theo thời gian; gợi ý cho điểm theo độ gần đồ thị với hạt giống + độ gần hồ sơ + thưởng xuyên danh mục + trừ mục đã xem, đa dạng hóa kết quả.
  - **success:** Mỗi gợi ý trả kèm đường đi đồ thị đã sinh ra nó (gợi ý không có đường đi là lỗi); precision@5 ≥ 70% với 2 người đánh giá kèm chỉ số đồng thuận; tỷ lệ xuyên miền ≥ 30% trong 5 gợi ý đầu khi hạt giống có danh mục được nối trong đồ thị; người dùng không có hồ sơ vẫn nhận gợi ý theo độ gần đồ thị (khởi động nguội an toàn).

- **CAP-4**
  - **intent:** Hệ thống tư vấn chủ động: phân loại ý định truy vấn thành 6 lớp (nghiên cứu, dự sự kiện, lên kế hoạch đi, tìm hiểu, so sánh, kiểm chứng) và kết xuất thẻ bối cảnh có kiểu phù hợp — lịch sự kiện, bản đồ địa điểm, thời tiết + danh mục chuẩn bị (sinh bằng luật tường minh trên dự báo, không bằng sinh văn bản), điểm quan sát, chỗ gửi xe gần nhất, cổ vật tương đương, nghề liên quan.
  - **success:** Macro-F1 ý định ≥ 85% trên 100 câu gán nhãn; **không một trường thẻ nào bị bịa** — mọi trường bằng đúng trường bản ghi nguồn hoặc phản hồi API, khẳng định tự động trên toàn bộ tập kiểm thử thẻ; API ngoài chết thì thẻ rơi về trạng thái không-có-dữ-liệu tường minh (ca kiểm thử riêng).

- **CAP-5**
  - **intent:** Hệ thống có tài khoản và quản trị: xác thực argon2id + cookie phiên HttpOnly; quản trị CRUD nội dung văn hóa và bản ghi có cấu trúc có kiểm tra nguồn; bảng điều khiển sức khỏe kho ngữ liệu + đồ thị + chỉ số; người dùng xuất và xóa dữ liệu cá nhân của mình.
  - **success:** Không có endpoint đọc/ghi dữ liệu cá nhân nào không xác thực; xác thực xuất hiện trước khi lưu bất kỳ dữ liệu cá nhân nào; mọi thay đổi quản trị ghi sổ kiểm toán kèm người thực hiện.

- **CAP-6**
  - **intent:** Người dùng tương tác qua giao diện dạng thẻ: chat có thẻ có kiểu, trang khám phá và chi tiết, khởi tạo sở thích, bản đồ Leaflet, MỘT sơ đồ bảo tàng SVG soạn thủ công kèm điểm nóng làm nổi vị trí cổ vật.
  - **success:** Văn bản thay thế cho mọi nội dung không phải chữ; điều hướng bàn phím cho chat và thẻ; phản hồi gợi ý/thẻ trong 2 giây không tính thời gian sinh mô hình; độ trễ đầu-cuối p95 ≤ 8 giây cho câu hỏi tiêu chuẩn, đo liên tục từ Tuần 3.

- **CAP-7**
  - **intent:** Hệ thống chạy được toàn bộ bộ đánh giá và kiểm thử: pytest + Playwright + CI, phép khẳng định không-bịa-trường, mọi chỉ số được tính và xuất ra tệp báo cáo tái lập được.
  - **success:** Mọi tệp báo cáo ghi model id, checkpoint bộ điều hợp, phiên bản prompt, phiên bản kho ngữ liệu, thống kê đồ thị, cấu hình đánh giá (NFR14); hai hành trình trình diễn (nghiên cứu cổ vật, dự lễ hội) hoàn chỉnh đầu-cuối cho người dùng đã xác thực có hồ sơ.

- **CAP-8**
  - **intent:** Hệ thống trích xuất thực thể bốn loại (người, địa điểm, sự kiện, thời gian) từ tài liệu dưới dạng JSON nghiêm ngặt, tất định, không gọi LLM lúc index.
  - **success:** Mọi tên trích ra là chuỗi con nguyên văn của tài liệu nguồn; Micro-F1 ≥ 0,75 (baseline 0,786, nhãn máy điền trước).

- **CAP-9**
  - **intent:** Hệ thống chạy trên nền tảng bền: PostgreSQL + SQLAlchemy + Alembic qua Docker Compose (thay trạng thái tệp + RAM hiện tại), Tailwind, các mô-đun có giao diện tách biệt (nạp dữ liệu, đồ thị, truy hồi, sinh, gợi ý, tư vấn, giao diện).
  - **success:** Thêm vùng, danh mục, sự kiện, địa điểm, cổ vật mới không cần sửa mã; thêm loại thẻ tư vấn mới chỉ cần đăng ký một bộ sinh (NFR15); Docker Compose dựng môi trường tái lập được.

- **CAP-10**
  - **intent:** Hệ thống chịu được đặc thù tiếng Việt: gõ không dấu, tên gọi khác, đơn vị hành chính đã đổi tên.
  - **success:** recall@1 giữ ≥ 95% trên câu không dấu và câu dùng tên gọi khác (baseline 30/30); bộ kiểm thử quan hệ hành chính đi kèm tệp tên gọi khác.

- **CAP-11**
  - **intent:** Hệ thống ghi nhận tương tác có đồng ý: sự kiện xem, thời gian dừng, nhấp thẻ, lưu, bỏ qua — kèm mốc thời gian và đỉnh đích; trọng số hồ sơ cập nhật có suy giảm.
  - **success:** Chỉ lưu dữ liệu cần cho gợi ý; hồ sơ và lịch sử tương tác trả về dạng tệp máy đọc được và xóa vĩnh viễn được khi yêu cầu (FR19); không ghi gì khi chưa có đồng ý có thông báo.

- **CAP-12**
  - **intent:** Mô hình ngôn ngữ cục bộ Qwen2.5-3B-Instruct-4bit + LoRA rank 16 trên 16 lớp cuối (MLX) phục vụ kể chuyện di sản, định dạng trích nguồn, từ chối, JSON thực thể.
  - **success:** LoRA dạy văn phong + trích nguồn + từ chối + đính chính giả định sai, không dạy dữ kiện; checkpoint chọn theo mất mát kiểm định (bước 200, 0,414 — không phải bước cuối); không gọi API bên ngoài nào để sinh văn bản.

- **CAP-13**
  - **intent:** Quản trị/biên tập rà soát và xác nhận kết quả trích xuất cùng dữ liệu bản ghi trước khi đưa vào sử dụng.
  - **success:** Thay đổi và người thực hiện ghi vào sổ kiểm toán; trạng thái rà soát lưu bền; báo cáo cuối nói rõ phần nào đã được rà soát ngoài.

- **CAP-14**
  - **intent:** Truy hồi lai không vector DB, không Neo4j: BM25 theo từ + BM25 theo n-gram không dấu hợp nhất bằng RRF, xếp hạng lại bằng lan truyền đồ thị; đồ thị dựng tất định trong RAM khi khởi động.
  - **success:** Không có LLM embedding, không trích xuất LLM, không chỉ mục vector, không cơ sở dữ liệu đồ thị — hai quyết định chệch có chủ ý so với GraphRAG tham chiếu, đã kiểm chứng bằng đo đạc (recall@1 30/30) và giữ làm định hướng.

- **CAP-15**
  - **intent:** Thẻ tư vấn suy giảm mềm khi dịch vụ ngoài không sẵn sàng: thời tiết, chỗ gửi xe, điểm quan tâm rơi về trạng thái không-có-dữ-liệu tường minh.
  - **success:** Không có giá trị nào bị đoán khi API chết; sự suy giảm này là một ca kiểm thử tường minh; lệnh gọi ngoài chạy song song chồng lên bước sinh để độ trễ ẩn trong thời gian sinh.

## Constraints

- **13 tuần còn lại trong 15 tuần, một người phát triển duy nhất.** Mọi năng lực mới được thêm bằng đánh đổi (Mục 16.2 loại 4 nhóm tính năng v1.0), không phình thêm kế hoạch; thứ tự cắt khi áp lực tiến độ được quyết trước (xem `architecture-principles.md`).
- **Nguyên tắc kiến trúc:** mô hình ngôn ngữ chỉ sinh phần kể chuyện di sản; mọi phát biểu thực tế có cấu trúc (ngày, tọa độ, thời tiết, chỗ gửi xe, thuộc tính cổ vật, gợi ý) kết xuất từ bản ghi có kiểu mang nguồn gốc, không bao giờ qua sinh văn bản. Lớp thẻ không đi qua lớp sinh.
- **Một máy Apple Silicon cho phát triển lẫn trình diễn** — cố định mô hình ở lớp 3B 4-bit, độ trễ sinh là số hạng chi phối trong p95 ≤ 8s; máy chủ không mở giao diện mạng công khai ở cấu hình demo.
- **Không bao giờ cắt:** ba cổng từ chối, trích nguồn bắt buộc, phép khẳng định không-bịa-trường, bộ đánh giá.
- **Nguồn bách khoa lệch danh mục** (nghệ thuật 4, lễ hội 2, làng nghề 2 — baseline) — mở rộng cân bằng danh mục là điều kiện tiên quyết cho gợi ý xuyên miền, xếp trước khi xây bộ gợi ý; bản ghi sự kiện/địa điểm/cổ vật không tồn tại sẵn, soạn thủ công, giới hạn 20 sự kiện / 50 địa điểm / 35 cổ vật / 1 sơ đồ bảo tàng.
- **Lễ hội Việt Nam theo âm lịch** — bảng quy đổi soạn thủ công cho các sự kiện thử nghiệm, không dùng thư viện âm lịch đa dụng (lệch ranh giới UTC+7).
- **API ngoài miễn phí không cần khóa (Open-Meteo, Overpass/Nominatim) nhưng có rate limit**; độ phủ OSM tại Việt Nam không đồng đều — đệm mọi phản hồi, kiểm tra độ phủ cho địa điểm trình diễn ngay đầu Tuần 7, suy giảm về điểm quan tâm soạn thủ công kèm nguồn ở nơi thiếu.
- **Đánh giá quy mô nhỏ là ràng buộc phương pháp:** 1 người phát triển, không nền người dùng — độ liên quan gợi ý và khả dụng chỉ báo cáo dạng mẫu nhỏ (SUS 6–8 người) kèm độ đồng thuận giữa 2 người đánh giá; nhãn vàng thực thể máy điền trước cần người rà soát ngoài.
- **Đo độ trễ liên tục từ Tuần 3** (khi DB + xác thực xuất hiện), không đợi giai đoạn kiểm thử cuối kỳ.
- **Xác thực xuất hiện trước dữ liệu cá nhân** — không có đường ghi nào không xác thực; ghi nhận tương tác cần đồng ý có thông báo trước.

## Non-goals

- Mô hình 3D, LiDAR, quét ảnh lập thể, bản sao số, tham quan ảo; GIS chuyên nghiệp; nhận dạng video; OCR quy mô lớn cho tài liệu scan.
- Dịch đa ngữ và bản địa hóa giao diện — chat tiếng Việt, giao diện tiếng Việt.
- Đặt vé, đặt tour, mọi giao dịch thương mại; dữ liệu đám đông; giao thông thời gian thực.
- Chứng nhận lịch sử chính thức cho nội dung — bản ghi chỉ có căn cứ trong giới hạn nguồn đã trích.
- Gợi ý bằng lọc cộng tác (đòi hỏi nền người dùng, không giải thích được).
- Ứng dụng di động gốc.
- Người dùng tải ảnh hoặc tài liệu qua giao diện chat — đầu vào chỉ văn bản.
- Thư viện ảnh + luồng tải ảnh, câu chuyện nhiều ảnh, nạp DOCX, chỉ mục vector riêng — 4 nhóm bị loại khỏi v1.0 để đánh đổi 4 năng lực mới (xem `architecture-principles.md` §Thay đổi phạm vi).
- Mở rộng vùng thứ ba (ví dụ Nam Bộ): cơ chế chuyển được nhưng không trình diễn được trong 13 tuần — crawl lại + gán danh mục + sinh lại tập đánh giá mất vài tuần không thêm cơ chế mới.

## Success signal

Hai hành trình trình diễn hoàn chỉnh đầu-cuối cho một người dùng đã xác thực có hồ sơ: **(A)** đọc về một cổ vật đá Chăm → nhận giải thích trích nguồn + sơ đồ bảo tàng làm nổi vị trí + cổ vật cùng thời kỳ + làng nghề liên quan + gợi ý xuyên danh mục kèm đường đi đồ thị; **(B)** hỏi về một lễ hội làng chài → nhận ý nghĩa trích nguồn + lịch năm nay + bản đồ + dự báo kèm danh mục chuẩn bị suy ra bằng luật + điểm quan sát + chỗ gửi xe — và khi tháo mạng, thẻ thời tiết ghi "không có dữ liệu" thay vì đoán. Mọi chỉ số ở `metrics-targets.md` được đo và báo cáo, bất kể đạt hay không: một mục tiêu không đạt nhưng được đo và giải thích là kết quả chấp nhận được; một mục tiêu không được đo thì không.

## Assumptions

- Nguồn bách khoa và nguồn chính thống vẫn truy cập công khai ở Tuần 4; sử dụng lại cho nguyên mẫu học thuật phi thương mại được phép kèm ghi công.
- Dữ kiện sự kiện/địa điểm/cổ vật lấy được từ ấn phẩm trung tâm bảo tồn, bảo tàng, cơ quan quản lý đô thị — mỗi dữ kiện có URL và câu nguồn trích dẫn được.
- API thời tiết và bản đồ miễn phí vẫn dùng được không cần khóa ở lưu lượng một buổi trình diễn.
- Máy trình diễn đủ tài nguyên chạy đồng thời truy hồi, đồ thị, cơ sở dữ liệu và mô hình cục bộ ở quy mô nhỏ.
- Người dùng có trình duyệt và kết nối mạng, chỉ gõ văn bản, không bao giờ tải tệp lên.
- Mục tiêu là chứng minh tính khả thi của luồng xử lý và độ tin cậy đo được, không phải triển khai hệ thống lưu trữ chính thức.
- Phần kể chuyện của AI là gợi ý cần biên tập viên xác nhận; bản ghi có cấu trúc chỉ có căn cứ trong giới hạn nguồn đã trích.
- Ghi nhận tương tác có đồng ý; người dùng có thể khám phá không cần hồ sơ.

## Open Questions

- Thay đổi phạm vi v2.0 đã chốt bằng văn bản với giảng viên hướng dẫn chưa? (hạng mục chặn Tuần 2)
- Email giảng viên và quyền sử dụng nguồn/ghi công chưa xác nhận — ai là đầu mối cố vấn chuyên môn (bảo tàng/trung tâm bảo tồn) rà soát bản ghi lễ hội + cổ vật?
- Baseline retrieval và phép so sánh base↔LoRA đã chốt ngày 08/09/2026; xem `pipelines/evaluation/baseline-summary.md`.
- Loại thực thể sự kiện không có nhãn vàng nào — "bốn loại" thực chất là ba loại tới khi rà soát và bổ sung nhãn; ai rà soát nhãn vàng ngoài trước báo cáo cuối?
