**International School**

**CAPSTONE PROJECT 1**

CMU-SE 450

**ĐỀ CƯƠNG DỰ ÁN**

**Ngày: 05/09/2026**

**Nền tảng Hybrid RAG + GraphRAG cá nhân hóa cho việc khám phá, tìm hiểu và lên kế hoạch trải nghiệm văn hóa địa phương**

**Thực hiện bởi: C1SE.50**

Dương Thanh Hùng – 29219043370

**Phê duyệt bởi:**

**ThS. Nguyễn Thị Thanh Tâm**

**Đại diện Hội đồng phản biện đề cương:**

Họ tên: Chữ ký: Ngày:

**Giảng viên hướng dẫn Capstone Project 1:**

Họ tên: **ThS. Nguyễn Thị Thanh Tâm** Chữ ký: Ngày:

**Đà Nẵng, tháng 9 năm 2026**

---

**THÔNG TIN DỰ ÁN**

| Trường | Giá trị |
| --- | --- |
| Tên dự án | Nền tảng Hybrid RAG + GraphRAG cá nhân hóa cho việc khám phá, tìm hiểu và lên kế hoạch trải nghiệm văn hóa địa phương |
| Tên viết tắt | CulturalMemoryGraph / CMG |
| Tên sản phẩm | **HeritageGraph** |
| Thời gian thực hiện | 27/08/2026 – 06/12/2026 (15 tuần) |
| Đơn vị | International School, CMU-SE 450 |
| Địa bàn / chủ đề thử nghiệm | Huế và Đà Nẵng — di tích, ẩm thực, danh thắng, nghệ thuật diễn xướng, lễ hội, làng nghề, cổ vật bảo tàng |
| Trạng thái | Đề cương dự án capstone |

---

## 1. Tên dự án

**Nền tảng Hybrid RAG + GraphRAG cá nhân hóa cho việc khám phá, tìm hiểu và lên kế hoạch trải nghiệm văn hóa địa phương**

Tên viết tắt: **CulturalMemoryGraph (CMG)**. Tên sản phẩm: **HeritageGraph**.

Mỗi thành phần của tên chỉ đúng một năng lực cụ thể của hệ thống:

| Thành phần tên | Năng lực |
| --- | --- |
| **Cá nhân hóa** | Hồ sơ sở thích riêng của từng người dùng chi phối việc xếp hạng, mở rộng và gợi ý. Hai người dùng nhập cùng một truy vấn nhận về hai tập kết quả khác nhau, mỗi kết quả có lý do riêng |
| **Hybrid RAG** | Truy hồi hợp nhất ba kênh bổ trợ nhau — truy hồi thưa theo từ khóa, truy hồi ngữ nghĩa theo vector, và truy hồi n-gram không phụ thuộc dấu — nhờ đó truy vấn viết chuẩn, truy vấn diễn giải lại và truy vấn gõ không dấu đều thành công |
| **GraphRAG** | Đồ thị tri thức gồm người, địa điểm, sự kiện, thời gian, nghề thủ công, cổ vật và tài liệu giúp neo truy hồi, xếp hạng lại ứng viên, và làm nền suy luận cho gợi ý xuyên miền |
| **Khám phá, tìm hiểu** | Hỏi đáp tiếng Việt có trích nguồn ở mức câu, giao diện thẻ tương tác, trang chi tiết thực thể kèm dòng thời gian, và một endpoint truy vết phơi ra vì sao mỗi đoạn được truy hồi |
| **Lên kế hoạch** | Khi phát hiện người dùng đang chuẩn bị tham dự một hoạt động văn hóa, hệ thống cung cấp bối cảnh thực tế cần thiết để thật sự đi được: lịch, địa điểm, thời tiết, cần mang gì, đứng ở đâu, gửi xe ở đâu |

## 2. Thành viên nhóm

| Họ tên | Mã sinh viên | Vai trò | Email |
| --- | --- | --- | --- |
| Dương Thanh Hùng | 29219043370 | Trưởng nhóm — phân tích yêu cầu, phát triển AI và truy hồi, kỹ thuật dữ liệu và tri thức, frontend, kiểm thử, tài liệu | *[điền trước khi nộp]* |

Đây là dự án một thành viên, nên các vai trò được định nghĩa tách biệt trong mẫu chuẩn được gộp thành một tập trách nhiệm duy nhất. Giảng viên hướng dẫn định hướng, phản hồi và rà soát tiến độ.

Hai hoạt động đánh giá cần một người đánh giá thứ hai từ bên ngoài, và Mục 11.4 định nghĩa bước đó: rà soát nhãn vàng thực thể, và đánh giá độ liên quan của gợi ý. Một điểm độ liên quan do chính người viết bộ gợi ý tự cho sẽ không phải bằng chứng, và dự án không coi nó là bằng chứng.

## 3. Giảng viên hướng dẫn

| Họ tên | Học vị / Đơn vị | Vai trò | Email |
| --- | --- | --- | --- |
| ThS. Nguyễn Thị Thanh Tâm | International School | Giảng viên hướng dẫn | *[điền trước khi nộp]* |
| *[sẽ mời]* | Bảo tàng hoặc trung tâm văn hóa | Cố vấn chuyên môn — rà soát nội dung di sản | *[điền]* |

Giảng viên hướng dẫn giúp xác định phạm vi, rà soát kiến trúc, đánh giá chất lượng dữ liệu, theo dõi tiến độ và phản biện kết quả. Một đầu mối chuyên môn có hiểu biết địa phương rà soát tính chính xác và việc ghi công của các bản ghi văn hóa: nhân viên Bảo tàng Điêu khắc Chăm hoặc Bảo tàng Cổ vật Cung đình Huế, đại diện Trung tâm Bảo tồn Di tích Cố đô Huế, hoặc giáo viên lịch sử.

## 4. Phát biểu vấn đề

### 4.1. Bối cảnh

Tư liệu văn hóa về Huế và Đà Nẵng thì nhiều, nhưng phẳng về mặt cấu trúc. Bài bách khoa, kỷ yếu lễ hội, nhãn hiện vật bảo tàng, địa chí và trang du lịch — mỗi nguồn mô tả một đối tượng tại một thời điểm. Người bắt đầu từ một điểm quan tâm — một loại hình diễn xướng, một món ăn, một pho tượng, một lễ hội, một nghề thủ công — chỉ nhận được đúng một bài viết, rồi phải tự mình tìm ra phần văn hóa liên quan.

Hai thất bại tách biệt sinh ra từ đó, và dự án giải quyết cả hai.

### 4.2. Thất bại thứ nhất — Việc khám phá không được cá nhân hóa

Công cụ tìm kiếm và cổng thông tin di sản trả về cùng một danh sách xếp hạng cho mọi người. Quan tâm đến nhã nhạc cung đình Huế và quan tâm đến điêu khắc đá Chăm đều cho ra cùng một khối "liên kết liên quan" chung chung, vì độ liên quan được tính từ độ tương đồng văn bản hoặc từ biên tập viên, không bao giờ tính từ người dùng.

Văn hóa là miền mà điều này thất bại nặng nhất, vì sở thích văn hóa vừa rất riêng vừa cắt ngang nhiều lĩnh vực. Người bị hút vào một loại hình diễn xướng truyền thống thường cũng mở lòng với trang phục, nhạc cụ, không gian diễn, làng nghề làm đạo cụ, và lễ hội nơi nó được trình diễn. Những đối tượng đó nằm ở các danh mục khác nhau và các tài liệu khác nhau, nên không công cụ nào nối chúng lại *cho đúng người đó*.

### 4.3. Thất bại thứ hai — Việc hiểu không dẫn tới hành động được

Các hệ thống thông tin văn hóa hiện có trả lời "cái này là gì?" rồi dừng. Nhu cầu thật của người dùng thường ở bước tiếp theo và gần như không bao giờ được nói ra.

Người nghiên cứu một cổ vật bảo tàng ngầm muốn biết bảo tàng nào đang giữ nó, ở đó còn gì cùng thời kỳ, và có món tương tự hay bản mô phỏng nào để xem hoặc mua. Người đọc về một lễ hội ngầm muốn biết năm nay diễn ra khi nào, đứng ở đâu để xem, hôm đó có mưa không. Mọi câu hỏi đó đều trả lời được từ dữ liệu. Không câu nào được một kho ngữ liệu văn hóa đơn thuần trả lời.

### 4.4. Vấn đề cốt lõi

Dự án giải quyết **sự thiếu vắng một nền tảng thông tin văn hóa biết thích ứng với từng người dùng và biết đoán trước nhu cầu thực tế nằm phía sau một truy vấn văn hóa, mà vẫn giữ được tính kiểm chứng.**

Cụm cuối cùng là thứ làm đây trở thành một bài toán ở tầm nghiên cứu, chứ không chỉ là phần mềm chưa ai làm. Hai cách hiển nhiên để thêm cá nhân hóa và tính chủ động đều thất bại:

- **Lọc cộng tác**, bộ gợi ý thương mại chuẩn, đòi hỏi một lượng người dùng lớn và cho ra đầu ra không giải thích được. Nó có thể nói *rằng* hai thứ liên quan nhưng không bao giờ nói *vì sao*. Trong bối cảnh di sản và giáo dục, đó là một lỗi, không phải một khiếm khuyết hình thức.
- **Để một mô hình ngôn ngữ đa dụng tự ứng biến** phần bối cảnh bổ sung sẽ đưa hiện tượng bịa đặt trở lại đúng vào chỗ mà người dùng dễ hành động theo câu trả lời nhất. Một mô hình sẵn sàng "nhiệt tình" bịa ra chỗ gửi xe hay giá vé cũng là mô hình sẽ bịa ra một triều đại.

Bài toán vì vậy là làm cho nền tảng cá nhân hóa và chủ động **mà không** phải trả một trong hai cái giá đó: gợi ý phải giải thích được từ cấu trúc đồ thị, và bối cảnh thực tế phải là dữ liệu có kiểu, có nguồn, không phải văn bản sinh ra.

Các chatbot đa dụng không giải được việc này. Không có kho ngữ liệu địa phương cụ thể, mô hình lẫn tên riêng tiếng Việt, trộn tỉnh thành, và phát biểu những thông tin không xuất hiện ở nguồn nào. Retrieval-Augmented Generation xử lý việc neo bằng chứng bằng cách đặt điều kiện cho bước sinh trên bộ nhớ ngoài đã truy hồi [1]. GraphRAG mở rộng thêm bằng cách kết hợp trích xuất văn bản, phân tích mạng và tóm tắt bằng LLM trên cấu trúc đồ thị [2], [3]. Dự án này dùng đồ thị cho một mục đích thứ hai ngoài việc neo bằng chứng: làm nền suy luận cho gợi ý xuyên miền giải thích được.

### 4.5. Tầm quan trọng của vấn đề

UNESCO ghi nhận rằng công nghệ số có thể mở rộng khả năng tiếp cận văn hóa và hỗ trợ tư liệu hóa, bảo vệ, quảng bá và kiểm kê di sản [4]. Tuy nhiên, tiếp cận không chỉ là có sẵn — nó còn là liên quan và dùng được. Một kho ngữ liệu không ai đi qua thì không tiếp cận được theo bất kỳ nghĩa có thực nào.

Điều hướng cá nhân hóa và giải thích được đặc biệt quan trọng với việc trao truyền văn hóa: nó biến một điểm tò mò đơn lẻ thành một đường đi qua các di sản liên quan, và đó chính là cách hiểu biết văn hóa tích lũy. Hỗ trợ lên kế hoạch đúng đắn thì quan trọng vì đó là bước mà quan tâm văn hóa trở thành tham dự văn hóa — khác biệt giữa đọc về một lễ hội và đi dự lễ hội đó.

### 4.6. Hướng giải quyết và nguyên tắc thiết kế trung tâm

Nền tảng được xây thành bốn lớp hợp tác trên một nền tri thức kiểm chứng được:

1. **Lớp trả lời có căn cứ** — truy hồi Hybrid RAG + GraphRAG, mô hình tiếng Việt , trích nguồn bắt buộc ở mức câu, và các cổng từ chối mang tính cấu trúc khiến hệ thống từ chối thay vì đoán.
2. **Lớp cá nhân hóa** — hồ sơ sở thích được **suy ra từ chính hành vi tìm kiếm và duyệt xem của người dùng, không có bảng khai sở thích nào phải điền**, cùng một bộ gợi ý cho điểm ứng viên theo độ gần đồ thị với chủ đề đang xem, độ gần đồ thị với hồ sơ, và một phần thưởng tường minh cho ứng viên thuộc danh mục văn hóa *khác* nhưng vẫn được nối bởi một đường đi thật. Mỗi gợi ý trả về kèm đường đi đã sinh ra nó, và hồ sơ suy ra được nhìn thấy và sửa được thay vì bị che.
3. **Lớp tư vấn chủ động** — nhận diện ý định của truy vấn, rồi một sổ đăng ký ánh xạ ý định sang các khối bối cảnh có kiểu: lịch, bản đồ địa điểm, thời tiết, danh mục cần chuẩn bị, điểm quan sát, chỗ gửi xe, cổ vật tương đương, nghề liên quan.
4. **Lớp trải nghiệm đa phương tiện** — mô hình 3D (.glb...) của địa điểm lưu trên Cloudflare R2, audio narration tiếng Việt và tiếng Anh lưu trên Azure Blob Storage Hoặc AWS, và một trình xem 3D nhúng trong trang chi tiết thực thể cho phép xoay, phóng to và nghe audio theo từng story. Lớp này tuân theo cùng yêu cầu về nguồn gốc như ba lớp trên: mỗi tài sản mang theo URL nguồn, người đóng góp, giấy phép và ngày tải lên.

Hai nguyên tắc chi phối biên giới giữa phần được sinh ra và phần dữ kiện, và được tham chiếu suốt tài liệu này:

> **Mô hình ngôn ngữ chỉ viết phần kể chuyện di sản. Mọi phát biểu thực tế hoặc có cấu trúc — ngày, tọa độ, thời tiết,  thuộc tính cổ vật, gợi ý — được kết xuất từ một bản ghi có kiểu mang theo nguồn gốc của chính nó, và không bao giờ đi qua bước sinh văn bản.**

> **Audio narration chỉ phát phần kể chuyện di sản. Mọi phát biểu thực tế trong script — tên triều đại, năm xây dựng, tọa độ, niên đại — phải truy về được một câu nguồn trong kho ngữ liệu, và điều này được kiểm tra tự động trước khi script được đưa vào bước tổng hợp giọng nói.**

Hai nguyên tắc này giữ được độ tin cậy của lớp trả lời trong khi thêm những năng lực mà nếu làm cách khác sẽ làm xói mòn nó, và chúng cho ra một tính chất kiểm chứng mang tính cấu trúc thay vì thống kê: không một trường nào của bất kỳ thẻ thực tế nào có thể bị bịa, và không một câu nào trong audio có thể khẳng định điều mà kho ngữ liệu không nói. Cả hai được khẳng định tự động trong bộ kiểm thử (NFR06, FR30).

## 5. Khảo sát / Các giải pháp hiện có

### 5.1. Retrieval-Augmented Generation, truy hồi lai và GraphRAG

Lewis và cộng sự kết hợp một mô hình ngôn ngữ tham số với bộ nhớ không tham số được truy hồi từ chỉ mục ngoài, cải thiện hỏi đáp đòi hỏi nhiều tri thức và cung cấp cơ sở truy hồi để kiểm chứng [1].

Các hệ RAG thực tế hiếm khi dựa vào một kênh truy hồi duy nhất. Truy hồi thưa theo từ khóa thuộc họ BM25 [8] chính xác với tên riêng, thuật ngữ ít gặp và cách diễn đạt đúng nguyên văn; truy hồi vector dày khái quát hóa được sang cách diễn giải lại và từ đồng nghĩa. Hợp nhất hai kênh — **Hybrid RAG** — là cách đã được thiết lập để có được cả hai hành vi, và reciprocal rank fusion [9] kết hợp các bảng xếp hạng có thang điểm không tương thích mà không cần chuẩn hóa. Tiếng Việt thêm một yêu cầu thứ ba mà không kênh nào trong hai kênh trên xử lý được: người dùng thường gõ không dấu, nên cần một kênh n-gram ký tự không phụ thuộc dấu để cùng một tài liệu được tìm thấy dù truy vấn viết là *"lăng Khải Định"* hay *"lang khai dinh"*.

GraphRAG của Microsoft Research kết hợp trích xuất văn bản, phân tích mạng và nhắc hoặc tóm tắt bằng LLM để suy luận trên cấu trúc của tập dữ liệu thay vì trên các đoạn rời rạc [2]; Edge và cộng sự trình bày chi tiết hướng tóm tắt cục bộ-đến-toàn cục theo truy vấn [3]. **GraphRAG** đóng góp điều mà không chỉ mục từ khóa hay chỉ mục vector nào biểu diễn được: rằng một di tích thuộc một phường cụ thể, rằng hai thực thể cùng xuất hiện qua nhiều tài liệu, rằng một cổ vật và một nghề thủ công thuộc cùng một thời kỳ. Đó chính là những quan hệ mà câu hỏi văn hóa thật sự dựa vào.

Nền tảng vì vậy kết hợp cả hai: **Hybrid RAG cung cấp các đoạn ứng viên, và GraphRAG neo, mở rộng và xếp hạng lại chúng.** Mục 12.3 đặc tả luồng này.

### 5.2. Hệ gợi ý và yêu cầu giải thích được

Gợi ý thương mại bị chi phối bởi lọc cộng tác và biểu diễn nhúng học được, hai thứ cần quy mô và cho ra đầu ra không minh bạch. Gợi ý giải thích được là một hướng nghiên cứu đã được công nhận, với lợi ích đã được ghi nhận về niềm tin của người dùng và chất lượng ra quyết định [11].

Nền tảng này dùng **gợi ý theo đường đi trên đồ thị**: ứng viên được cho điểm bằng lan truyền có trọng số trên đồ thị di sản, và đường lan truyền được trả về làm lời giải thích. Cách này hoạt động ngay từ phiên đầu tiên mà không cần nền người dùng, kiểm toán được, và trực tiếp hỗ trợ gợi ý xuyên miền, vì một số hạng thưởng cho ứng viên đến được bằng đường đi thật nhưng thuộc danh mục văn hóa khác. Việc xếp hạng lại theo độ đa dạng dùng công thức maximal marginal relevance [10] để phần đầu danh sách không thoái hóa thành năm ví dụ cùng một loại di tích.

### 5.3. Các nền tảng tương đương

**Google Arts & Culture** tổng hợp các bộ sưu tập đã số hóa và những câu chuyện theo địa điểm do bảo tàng khắp thế giới biên tập [5], [6]. Nền tảng này chia sẻ cùng mục tiêu ghép hình ảnh với bối cảnh tường thuật. Nó khác ở chỗ độ liên quan do biên tập viên quyết định, không có đồ thị thực thể–quan hệ phơi ra cho người dùng, không có hỏi đáp mở có trích nguồn trên một kho ngữ liệu địa phương cụ thể, và không có mô hình sở thích theo từng người.

**Các cổng du lịch và điểm đến** cung cấp thông tin hậu cần thực tế — giờ mở cửa, đường đi, đặt chỗ — nhưng đặt thương mại lên trước. Chúng không có đồ thị tri thức văn hóa, không trích nguồn, và không có hành vi từ chối; một dữ kiện thiếu được lấp bằng nội dung tiếp thị thay vì bằng một lời thừa nhận là không biết.

**Địa chí đã số hóa và trang di sản tĩnh** thì có thẩm quyền nhưng bất động: một tài liệu cho một đối tượng, không liên kết chéo, không có giao diện truy vấn nào ngoài tìm theo từ khóa.

**Các chatbot LLM đa dụng** trông như giải được mọi thứ và thực tế kiểm chứng được là không. Không có kho ngữ liệu địa phương, chúng lẫn tên riêng và tỉnh thành Việt Nam, và chúng không thể trích nguồn.

### 5.4. So sánh với các hướng tiếp cận hiện có

| Tiêu chí | Trang di sản tĩnh / địa chí | Chatbot LLM đa dụng | Google Arts & Culture | Cổng du lịch / đặt chỗ | **HeritageGraph** |
| --- | --- | --- | --- | --- | --- |
| Dữ liệu chính | Bài rời rạc và chú thích | Tri thức trong trọng số mô hình | Trưng bày bảo tàng đã biên tập | Danh sách thương mại | Kho ngữ liệu địa phương + đồ thị tri thức + bản ghi văn hóa có kiểu |
| Liên kết người–nơi–sự kiện–thời gian | Thường không có | Không đáng tin | Do biên tập viên tạo | Không có | Đồ thị tri thức có nguồn gốc trên từng đỉnh |
| Truy hồi | Chỉ từ khóa | Không có (tham số) | Duyệt theo mặt | Từ khóa và bộ lọc | **Hybrid RAG (từ khóa + vector + không dấu) hợp nhất với GraphRAG** |
| Đầu vào tiếng Việt không dấu | Thất bại | Chịu được nhưng không có căn cứ | Không áp dụng | Một phần | Kênh n-gram riêng |
| Cá nhân hóa | Không | Chỉ là bộ nhớ hội thoại | Rất ít | Nhắm mục tiêu theo ý định mua | Hồ sơ sở thích + cho điểm theo đường đi đồ thị |
| Giải thích được "vì sao cái này?" | Không | Không | Không | Không | **Có — trả về đường lan truyền** |
| Gợi ý xuyên miền | Không | Không kiểm chứng được | Trong phạm vi trưng bày đã biên tập | Không | **Có số hạng thưởng xuyên danh mục tường minh** |
| Trích nguồn ở mức đoạn | Thỉnh thoảng | Không bảo đảm | Chỉ ghi công ở mức trưng bày | Không | **Bắt buộc, có đo** |
| Từ chối khi thiếu bằng chứng | Không áp dụng | Hiếm | Không áp dụng | Không áp dụng | **Cổng từ chối cấu trúc, có đo** |
| Bối cảnh lên kế hoạch thực tế | Không | Không kiểm chứng được | Không | Có, ưu tiên thương mại | **Có, dữ liệu có kiểu và có nguồn** |
| Hoạt động không cần API AI bên ngoài | Có | Không | Không | Không | Có — phân tích và sinh văn bản chạy cục bộ |

### 5.5. Điểm khác biệt của dự án

HeritageGraph không tuyên bố thay thế các hệ thống bảo tồn chuyên nghiệp hay các nền tảng tổng hợp lớn. Đóng góp của nó là tổ hợp mà không đối tượng so sánh nào trong năm cái trên có được:

**Cá nhân hóa theo từng người dùng và bối cảnh thực tế chủ động, đặt trên một bộ máy trả lời kiểm chứng được, có trích nguồn và biết từ chối — với truy hồi hợp nhất Hybrid RAG và GraphRAG, mọi gợi ý giải thích được thành một đường đi trên đồ thị, và mọi phát biểu thực tế truy về được một bản ghi nguồn có kiểu.**

**Trải nghiệm đa phương tiện nâng cao cho văn hóa địa phương.** Nền tảng tận dụng mô hình 3D (.glb) mã nguồn mở hoặc dữ liệu công khai từ các dự án số hóa di sản cùng TTS tiếng Việt/tiếng Anh để tạo audio narration tự động, cho phép phủ nhiều địa điểm trong cùng thời gian và ngân sách. Lưu trữ trên Cloudflare R2 (mô hình 3D) và Azure Blob Storage (audio) giúp chi phí vận hành ở mức tối thiểu — R2 miễn phí 10 GB và Azure for Students cung cấp 5 GB Blob storage — đủ cho một nguyên mẫu học thuật. Mỗi file 3D và audio vẫn gắn với URL nguồn và bằng chứng nguyên văn trong kho ngữ liệu, nên tính kiểm chứng của nền tảng không bị xói mòn khi mở rộng sang trải nghiệm đa phương tiện.

## 6. Mục tiêu và Phạm vi

### 6.1. Mục tiêu tổng quát

Xây dựng và đánh giá một nền tảng AI trên web cho văn hóa Huế và Đà Nẵng, có khả năng trả lời câu hỏi tiếng Việt từ kho ngữ liệu địa phương đã tuyển chọn bằng Hybrid RAG kết hợp GraphRAG, kèm trích nguồn ở mức câu và từ chối tường minh; cá nhân hóa việc khám phá cho từng người dùng thông qua hồ sơ sở thích và một bộ gợi ý theo đường đi đồ thị giải thích được; và chủ động cung cấp bối cảnh thực tế có kiểu tương ứng với ý định của người dùng, để quan tâm văn hóa có thể trở thành tham dự văn hóa.

### 6.2. Mục tiêu cụ thể

**O1 — Nền tri thức văn hóa.** Xây kho ngữ liệu tối thiểu 80 tài liệu trên sáu danh mục văn hóa — di tích, ẩm thực, danh thắng, nghệ thuật diễn xướng, lễ hội, làng nghề — với tối thiểu 8 tài liệu mỗi danh mục, được chuẩn hóa thành các đoạn kèm định vị nguồn và tên gọi khác.

**O2 — Đồ thị tri thức.** Xây đồ thị tri thức liên kết tài liệu, thực thể, đơn vị hành chính, vùng, danh mục, năm, sự kiện, địa điểm và cổ vật, trong đó mọi đỉnh truy về được một chuỗi nguyên văn của tài liệu nguồn, với quan hệ có kiểu và có trọng số, và không quan hệ nào được khẳng định mà thiếu bằng chứng.

**O3 — Bản ghi văn hóa có cấu trúc.** Soạn bản ghi địa điểm kèm tọa độ, bản ghi sự kiện kèm loại lịch, ngày, đơn vị tổ chức và các phần lễ/hội, và bản ghi cổ vật kèm niên đại, chất liệu, bảo tàng đang giữ và phòng trưng bày — mỗi trường sự kiện mang theo URL nguồn và câu nguồn đã đọc ra nó.

**O4 — Truy hồi Hybrid RAG + GraphRAG.** Hiện thực truy hồi ba kênh — thưa theo từ khóa, ngữ nghĩa theo vector, và n-gram không phụ thuộc dấu — hợp nhất bằng reciprocal rank fusion, rồi neo, mở rộng và xếp hạng lại bằng lan truyền đồ thị, kèm một endpoint truy vết phơi ra mọi thành phần cho điểm để giải thích được.

**O5 — Trả lời có căn cứ.** Cung cấp hỏi đáp tiếng Việt với trích nguồn bắt buộc theo dạng `[Nguồn: <câu nguyên văn> — <url>]`, từ chối lịch sự khi bằng chứng không đủ, đính chính giả định sai ngay ở câu đầu, và trích xuất thực thể bốn loại dưới dạng JSON nghiêm ngặt.

**O6 — Cá nhân hóa.** Suy ra sở thích từ chính hành vi tìm kiếm và duyệt xem của người dùng có suy giảm theo thời gian, phơi hồ sơ suy ra được ra cho người dùng xem và sửa, xếp hạng và mở rộng theo từng người, trả về kèm mỗi gợi ý đường đi đồ thị biện minh cho nó, và đạt được một tỷ lệ xuyên miền đo được thay vì chỉ gợi ý trong cùng danh mục. Người dùng không bao giờ bị yêu cầu khai sở thích trước khi dùng nền tảng.

**O7 — Tư vấn chủ động.** Phân loại ý định truy vấn thành sáu lớp và kết xuất các khối bối cảnh có kiểu phù hợp ý định — lịch sự kiện, bản đồ địa điểm, thời tiết, danh mục cần chuẩn bị, điểm quan sát, chỗ gửi xe, cổ vật tương đương, nghề liên quan — với không một trường nào bị bịa, được khẳng định bằng kiểm thử tự động.

**O8 — Giao diện thẻ tương tác và trải nghiệm đa phương tiện.** Thay danh sách kết quả tìm kiếm thuần bằng khung chat dạng thẻ tương tác, trang chi tiết thực thể kiểu Tapestry kèm dòng thời gian và khung bản đồ, và một trình xem 3D có audio narration hai ngôn ngữ cho các địa điểm đã số hóa.

**O9 — Biên tập và quản trị.** Cung cấp cho người quản trị chức năng quản lý nội dung và bản ghi với kiểm tra nguồn tự động từ chối trường thiếu nguồn, trạng thái rà soát, sổ kiểm toán, và bảng theo dõi sức khỏe kho ngữ liệu và đồ thị.

**O10 — Riêng tư.** Xin sự đồng ý trước khi ghi nhận hành vi, chỉ lưu những gì bộ gợi ý cần, và cho người dùng xuất cũng như xóa vĩnh viễn dữ liệu cá nhân của mình.

**O11 — Đánh giá.** Đo và báo cáo recall truy hồi, F1 thực thể, độ trung thực và độ phủ trích nguồn, độ chính xác từ chối, độ chính xác ý định, precision@5 và nDCG@5 của gợi ý kèm độ đồng thuận giữa người đánh giá, tỷ lệ xuyên miền, độ đa dạng trong danh sách, độ đúng trường của thẻ, độ trễ p95 và khả dụng; đồng thời chứng minh việc thêm lớp cá nhân hóa và lớp tư vấn không làm suy giảm độ trung thực trích nguồn hay độ chính xác từ chối.

### 6.3. Trong phạm vi

Một cặp địa bàn thử nghiệm (Huế và Đà Nẵng) trên sáu danh mục văn hóa. Nạp kho ngữ liệu, chuẩn hóa, tách đoạn và trích tên gọi khác. Trích xuất tất định thực thể, quan hệ, đơn vị hành chính và thời gian kèm chuỗi bằng chứng. Dựng đồ thị tri thức, thống kê, kiểm tra đồ thị con và truy vết truy hồi. Hybrid RAG với ba kênh truy hồi được hợp nhất và xếp hạng lại bằng GraphRAG. Mô hình tiếng Việt cục bộ tinh chỉnh theo miền với trích nguồn, từ chối và đính chính giả định sai. Đăng ký, xác thực và quản lý phiên người dùng. Suy ra sở thích ngầm định từ hành vi có suy giảm theo thời gian, và một hồ sơ sở thích nhìn thấy được, sửa được. Bộ gợi ý theo đường đi đồ thị giải thích được với thưởng xuyên miền và xếp hạng lại theo đa dạng. Phân loại ý định sáu lớp. Các thẻ tư vấn có kiểu bao gồm thời tiết và điểm quan tâm từ API công khai miễn phí. Khung chat dạng thẻ tương tác, trang chi tiết thực thể kiểu Tapestry, dòng thời gian, khung bản đồ, và trình xem 3D kèm audio narration hai ngôn ngữ cho một số địa điểm đã số hóa. Quản lý nội dung và bản ghi có cấu trúc cho người quản trị với kiểm tra nguồn, trạng thái rà soát, sổ kiểm toán và bảng theo dõi sức khỏe. Xuất và xóa dữ liệu cá nhân. Bộ đánh giá, báo cáo đánh giá, bộ kiểm thử và tích hợp liên tục.

Người dùng cuối chỉ gửi văn bản. Họ không tải ảnh hay tài liệu qua giao diện chat.

### 6.4. Ngoài phạm vi

 Nhận dạng video và OCR quy mô lớn cho tài liệu scan. Dịch đa ngữ và bản địa hóa giao diện — audio narration có hai ngôn ngữ, nhưng giao diện và câu trả lời chat chỉ có tiếng Việt. Đặt vé hoặc đặt tour và mọi giao dịch thương mại. Dữ liệu đám đông, giao thông hoặc vận tải thời gian thực. Chứng nhận lịch sử chính thức cho nội dung. Gợi ý bằng lọc cộng tác đòi hỏi nền người dùng lớn. Ứng dụng di động gốc. **Đầu vào bằng giọng nói** — người dùng chỉ gõ văn bản; hệ thống có phát audio narration đã soạn trước (F12) nhưng không nhận lệnh thoại và không đọc thành tiếng câu trả lời chat sinh động. Số hóa 3D bằng quét thực địa — mô hình 3D lấy từ nguồn mở hoặc dữ liệu công khai, dự án không tự quét. Nhận dạng tự động nội dung ảnh — ảnh được quản lý qua metadata và chú thích đã xác nhận thay vì bằng thị giác máy tính.


## 7. Tính năng chính và Yêu cầu

### 7.1. Tính năng cốt lõi

Tính năng được nhóm theo tác nhân: Quản trị/Biên tập F01–F06, Người dùng F07–F12, và các trao đổi AI nội bộ F13–F14. Mỗi luồng yêu cầu có một luồng phản hồi tương ứng, cho **14 cặp yêu cầu/phản hồi** trong sơ đồ ngữ cảnh (Mục 12.2).

| Mã | Tính năng | Tác nhân | Yêu cầu → Phản hồi |
| --- | --- | --- | --- |
| F01 | Đăng nhập | Quản trị | Yêu cầu đăng nhập → Phản hồi đăng nhập kèm thông tin phiên |
| F02 | Quản lý nội dung văn hóa | Quản trị | CRUD trên tài liệu, tên gọi khác, gán danh mục và vùng → Kết quả CRUD, kèm kích hoạt dựng lại đồ thị |
| F03 | Quản lý bản ghi có cấu trúc | Quản trị | CRUD trên địa điểm kèm tọa độ, sự kiện kèm lịch và các phần, cổ vật kèm niên đại, chất liệu và phòng trưng bày, và tài sản đa phương tiện kèm giấy phép và nguồn gốc → Kết quả kiểm tra, từ chối mọi bản ghi có trường sự kiện thiếu nguồn |
| F04 | Rà soát kết quả trích xuất | Quản trị | Xác nhận hoặc sửa thực thể, quan hệ và tên gọi khác đã trích → Trạng thái cập nhật kèm bản ghi sổ kiểm toán |
| F05 | Bảng điều khiển quản trị | Quản trị | Yêu cầu bảng điều khiển → Dữ liệu tổng quan: số tài liệu theo danh mục, thống kê đồ thị, số trường thiếu nguồn, hàng chờ rà soát, chỉ số đánh giá mới nhất |
| F06 | Chạy bộ đánh giá | Quản trị | Yêu cầu đánh giá → Báo cáo chỉ số có ghi mô hình, checkpoint bộ điều hợp, phiên bản prompt, phiên bản kho ngữ liệu và cấu hình đánh giá |
| F07 | Đăng ký và quản lý tài khoản | Người dùng | Đăng ký hoặc cập nhật tài khoản → Xác nhận tài khoản. Trang quản lý tài khoản cũng hiển thị hồ sơ sở thích đã suy ra (mỗi mục kèm hành vi đã sinh ra nó), cho phép bỏ hoặc tắt một sở thích suy ra sai, xuất dữ liệu cá nhân dưới dạng tệp máy đọc được, và xóa vĩnh viễn dữ liệu |
| F08 | Tìm kiếm lai theo sở thích | Người dùng | Truy vấn từ khóa hoặc ngôn ngữ tự nhiên → Kết quả xếp hạng từ Hybrid RAG hợp nhất với GraphRAG và xếp hạng lại theo hồ sơ sở thích |
| F09 | Truy vấn ngôn ngữ tự nhiên | Người dùng | Câu hỏi văn hóa tự do bằng tiếng Việt → Câu trả lời kèm trích nguồn, hoặc phát biểu tường minh rằng bằng chứng hiện có không đủ |
| F10 | Bối cảnh chủ động | Người dùng | Ý định phát hiện được ở F08 hoặc F09 → Các thẻ tư vấn có kiểu: lịch sự kiện, bản đồ địa điểm, thời tiết và danh mục cần chuẩn bị, điểm quan sát tốt nhất, chỗ gửi xe gần nhất, cổ vật tương đương, nghề liên quan — mỗi thẻ kèm nguồn gốc |
| F11 | Trang chi tiết thực thể | Người dùng | Chọn một thực thể hoặc tài liệu → Nội dung chi tiết kiểu Tapestry: ảnh lớn bên trái, danh sách story bên phải có thể chọn, mỗi story kèm nội dung kể chuyện, audio, chip liên kết thực thể, dòng thời gian các năm liên quan, thực thể liên quan, địa điểm và sự kiện gắn với nó, và dải nội dung liên quan |
| F12 | Trải nghiệm đa phương tiện nâng cao | Người dùng | Từ trang chi tiết F11, chọn xem mô hình 3D (.glb) của địa điểm kèm audio narration tiếng Việt và tiếng Anh → Trình xem 3D nhúng cho phép xoay, phóng to, nghe audio, chuyển story và chuyển ngữ, kèm transcript đầy đủ. Mô hình 3D lưu trên Cloudflare R2; audio lưu trên Azure Blob Storage. Cả hai loại tệp được soạn, kiểm tra bằng chứng và tổng hợp ngoại tuyến trước đó, không sinh lúc chạy |
| F13 | Phân tích nội dung | Nội bộ | Văn bản tài liệu → Thực thể, quan hệ, đơn vị hành chính và năm đã trích kèm chuỗi bằng chứng, dùng để dựng đồ thị. Chạy khi F02 xảy ra |
| F14 | Sinh câu trả lời | Nội bộ | Bối cảnh đã tổ hợp và câu hỏi → Phần kể chuyện đã sinh kèm trích nguồn. Chạy khi F09 xảy ra |

**F13 và F14 là nội bộ và cục bộ.** F13 là trích xuất tất định, không gọi mô hình nào: một danh sách thực thể tuyển chọn, một từ vựng phân loại đóng và biểu thức chính quy, nên mọi tên trích ra là chuỗi con nguyên văn của nguồn và không thể bị bịa. F14 là một mô hình tinh chỉnh chạy cục bộ. Vì vậy không có dịch vụ AI bên ngoài nào trong kiến trúc, không có chi phí API, và văn bản kho ngữ liệu văn hóa không bao giờ rời khỏi máy.

**Khởi động nguội của bộ gợi ý và tìm kiếm cá nhân hóa.** Nền tảng có chủ đích **không có bảng khai sở thích khi bắt đầu**. Sở thích được suy ra hoàn toàn từ hành vi người dùng: tìm gì, mở thực thể nào, dừng bao lâu, nhấp lưu hay bỏ qua thẻ nào. Số hạng hạt giống của bộ gợi ý — độ gần đồ thị với đối tượng người dùng đang xem — hoạt động ngay từ tương tác đầu tiên, nên phiên đầu tiên đã hữu dụng. Số hạng hồ sơ chỉ bắt đầu góp gì khi có hành vi để học, và tăng dần trọng số khi bằng chứng tích lũy. Người dùng có thể bỏ hoặc tắt từng sở thích suy ra sai qua giao diện hồ sơ trong trang quản lý tài khoản F07.

**F10 là tính năng không được phép bịa.** Các thẻ của nó được kết xuất từ bản ghi có kiểu và API công khai miễn phí, không bao giờ do sinh văn bản tạo ra. Yếu tố kích hoạt là nhận diện ý định thay vì một cú nhấp tường minh của người dùng — chính điều đó làm nó chủ động: hệ thống suy ra nhu cầu mà người dùng chưa nói.

**Phụ thuộc.** F08 đến F12 phụ thuộc đồ thị do F13 dựng. F08, F09 và F11 phụ thuộc thêm vào hồ sơ sở thích ngầm định (được dựng nên từ các hành vi của người dùng). F10 và F12 phụ thuộc thêm vào bản ghi có cấu trúc từ F03. Thẻ thời tiết và chỗ gửi xe của F10 suy giảm về trạng thái không-có-dữ-liệu tường minh khi không gọi được dịch vụ ngoài, và F12 suy giảm về nội dung văn bản khi kho tài sản không truy cập được; cả hai sự suy giảm đó đều là ca kiểm thử.

**Bỏ các tính năng sau so với bản gốc.** Bốn tính năng của bản trước được lược bỏ để giữ phạm vi khả thi trong 15 tuần với một người phát triển, và mỗi tính năng bị bỏ đều có năng lực thay thế thay vì mất hẳn:

| Tính năng bản gốc | Xử lý | Năng lực thay thế |
| --- | --- | --- |
| Xem và điều chỉnh hồ sơ sở thích | Gộp vào F07 | Một mục trong giao diện hồ sơ ở trang quản lý tài khoản, đặc tả ở FR25 |
| Khám phá đồ thị | Bỏ | Quan hệ giữa các thực thể hiện ra qua chip liên kết trong story F11 và qua đường đi đồ thị trả về kèm mỗi gợi ý (FR09); việc kiểm tra ở mức kỹ thuật dùng endpoint truy vết (FR24) |
| Sơ đồ bảo tàng có điểm nóng cổ vật | Bỏ | Vị trí cổ vật được nêu bằng tên bảo tàng và phòng trưng bày trong bản ghi cổ vật F03, hiển thị ở story F11 và thẻ tư vấn F10 (FR22); trải nghiệm không gian được đáp ứng bằng mô hình 3D của F12 |
| Xuất và xóa dữ liệu cá nhân | Gộp vào F07 | Hai hành động trong trang quản lý tài khoản, đặc tả ở FR25 |

Việc gộp thay vì bỏ hẳn hai tính năng về dữ liệu cá nhân là có chủ đích: chúng là nghĩa vụ về riêng trước sau khi hành vi được ghi nhận (NFR12), nên chúng không thể bị cắt, chỉ có thể được đặt ở chỗ khác.

### 7.2. Yêu cầu chức năng

| Mã | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR01 | Người dùng có thể đăng ký, xác thực và quản lý tài khoản | Mật khẩu chỉ lưu dưới dạng băm argon2id; thông tin phiên phát hành qua cookie HttpOnly; các endpoint được bảo vệ từ chối yêu cầu chưa xác thực |
| FR02 | Quản trị có thể thêm hoặc sửa tài liệu kho ngữ liệu | Tài liệu được chuẩn hóa, tách thành đoạn kèm định vị nguồn, và đồ thị được dựng lại với các đỉnh mới liên kết về nguồn |
| FR03 | Quản trị có thể thêm hoặc sửa bản ghi địa điểm, sự kiện, cổ vật và tài sản đa phương tiện | Bản ghi chỉ được lưu nếu mọi trường sự kiện đều có URL nguồn và câu nguồn; trường thiếu nguồn bị từ chối kèm lỗi ở mức trường |
| FR04 | Hệ thống trích xuất thực thể, quan hệ, đơn vị hành chính và năm từ tài liệu | Đầu ra khớp lược đồ bốn loại, lưu chuỗi bằng chứng, và mọi tên trích ra là chuỗi con nguyên văn của nguồn |
| FR05 | Hệ thống dựng và cập nhật đồ thị tri thức | Đỉnh và cạnh được tạo, gán kiểu, gán trọng số và liên kết về tài liệu nguồn; thống kê được báo cáo; không quan hệ nào được tạo mà thiếu chuỗi nguồn |
| FR06 | Quản trị có thể xác nhận hoặc sửa kết quả trích xuất | Thay đổi và người thực hiện được ghi vào sổ kiểm toán kèm giá trị trước và sau |
| FR07 | Hệ thống suy ra hồ sơ sở thích mà không yêu cầu người dùng khai | Nền tảng dùng được đầy đủ trước khi có bất kỳ hồ sơ nào; sau vài lần tìm kiếm hoặc xem đầu tiên của một người dùng, hồ sơ chứa các sở thích có trọng số suy ra từ chính những hành động đó |
| FR08 | Hệ thống ghi nhận tương tác ngầm định, và người dùng xem cũng như sửa được kết quả suy ra | Sự kiện xem, thời gian dừng, nhấp thẻ, lưu và bỏ qua được ghi kèm mốc thời gian và đỉnh đích; trọng số hồ sơ cập nhật có suy giảm theo thời gian; người dùng thấy được từng sở thích suy ra kèm hành động đã sinh ra nó, và có thể bỏ hoặc tắt nó |
| FR09 | Hệ thống trả về gợi ý cá nhân hóa | Với một chủ đề và một hồ sơ, trả về danh sách xếp hạng trong đó **mỗi mục kèm đường đi đồ thị đã sinh ra nó** |
| FR10 | Gợi ý bao gồm mục xuyên danh mục | Với hạt giống có danh mục được nối trong đồ thị, tối thiểu một trong năm gợi ý đầu thuộc danh mục văn hóa khác |
| FR11 | Gợi ý có độ đa dạng | Năm mục đầu chứa không quá ba mục cùng danh mục, trừ khi số danh mục tiếp cận được ít hơn |
| FR12 | Tìm kiếm lai truy hồi được đoạn liên quan | Với truy vấn trong phạm vi, tài liệu đúng được xếp hạng nhất, bất kể truy vấn viết có dấu, không dấu, bằng tên gọi khác, hay diễn giải lại; đóng góp của từng kênh được đo riêng và báo cáo dưới dạng bảng đo tách kênh |
| FR13 | Kết quả tìm kiếm được xếp hạng lại theo hồ sơ sở thích | Hai người dùng có hồ sơ khác nhau nhận thứ tự khác nhau cho cùng truy vấn, và sự khác biệt về thứ tự truy nguyên được về trọng số hồ sơ |
| FR14 | Người dùng có thể gửi câu hỏi tiếng Việt chỉ bằng văn bản | Giao diện chat chỉ nhận văn bản; câu trả lời sinh ra chỉ từ bối cảnh đã truy hồi |
| FR15 | Câu trả lời có trích nguồn hoặc phát biểu thiếu bằng chứng | Không sinh ra câu trả lời khẳng định nào mà không có câu nguồn được trích từ tài liệu đã truy hồi |
| FR16 | Hệ thống đính chính giả định sai | Khi câu hỏi chứa giả định trái với nguồn, phần đính chính xuất hiện ngay ở câu đầu của câu trả lời |
| FR17 | Hệ thống phân loại ý định truy vấn | Truy vấn được gán vào một trong sáu lớp ý định; lớp được gán được ghi lại và kiểm tra được |
| FR18 | Hệ thống trả thẻ tư vấn phù hợp ý định | Thẻ khớp sổ đăng ký ý định–bộ sinh; **mọi trường của thẻ bằng đúng trường tương ứng của bản ghi nguồn hoặc phản hồi API, không có trường nào do sinh ra** |
| FR19 | Hệ thống cung cấp lịch sự kiện và chi tiết địa điểm | Với sự kiện có trong nền tri thức, trả về tên, loại lịch và ngày, địa điểm kèm tọa độ, đơn vị tổ chức, và các phần lễ và hội |
| FR20 | Hệ thống cung cấp thời tiết và danh mục chuẩn bị cho sự kiện có ngày | Dự báo lấy từ API thời tiết công khai theo tọa độ địa điểm; danh mục chuẩn bị sinh bằng luật tường minh trên dự báo, không bằng sinh văn bản |
| FR21 | Hệ thống cung cấp điểm quan tâm gần địa điểm | Bãi xe, điểm quan sát và cửa hàng nghề hoặc quà gần một địa điểm được trả về kèm nguồn và thời điểm lấy dữ liệu; dịch vụ không sẵn sàng cho ra trạng thái không-có-dữ-liệu tường minh |
| FR22 | Hệ thống cung cấp thông tin địa điểm và lịch mở cửa trong thẻ tư vấn của F10 | Với sự kiện hoặc cổ vật có địa điểm gắn với, F10 trả thẻ kèm tên địa điểm, địa chỉ, giờ mở cửa, giá vé từ bản ghi có cấu trúc F03; với cổ vật, thẻ nêu thêm bảo tàng đang giữ và phòng trưng bày |
| FR23 | Người dùng có thể xem trang chi tiết thực thể kiểu Tapestry | Trang hiển thị ảnh lớn bên trái, danh sách story bên phải có chọn được, mỗi story kèm nội dung kể chuyện, audio, chip liên kết thực thể, dòng thời gian các năm liên quan, thực thể liên quan, địa điểm và sự kiện gắn với nó, và dải nội dung liên quan |
| FR24 | Người dùng có thể kiểm tra vì sao một đoạn được truy hồi | Vết truy hồi phơi ra hạt giống đồ thị, hạng theo từng kênh, độ gần đồ thị, các thành phần cho điểm, và kết quả của từng cổng từ chối |
| FR25 | Người dùng có thể quản lý hồ sơ sở thích và dữ liệu cá nhân trong F07 | Trong trang quản lý tài khoản F07, hồ sơ sở thích hiển thị kèm hành vi đã sinh ra nó và có thể bỏ hoặc tắt; hồ sơ và lịch sử tương tác có thể xuất dưới dạng tệp máy đọc được hoặc xóa vĩnh viễn khi yêu cầu |
| FR26 | Quản trị có thể xem sức khỏe kho ngữ liệu và đồ thị | Số tài liệu theo danh mục, thống kê đồ thị, số trường thiếu nguồn, hàng chờ rà soát và chỉ số mới nhất được hiển thị |
| FR27 | Hệ thống chạy được toàn bộ bộ đánh giá | Mọi chỉ số ở Mục 15.3 được tính và xuất ra báo cáo có ghi mô hình, checkpoint bộ điều hợp, phiên bản prompt, phiên bản kho ngữ liệu và cấu hình đánh giá |
| FR28 | Người dùng có thể xem trải nghiệm 3D kèm audio narration | Từ F11, mô hình 3D (.glb) tải từ Cloudflare R2 được nhúng qua Three.js; audio narration tiếng Việt và tiếng Anh tải từ Azure Blob Storage; người dùng có thể xoay, phóng to, chuyển story và chuyển ngữ; mỗi tệp audio có transcript đầy đủ hiển thị được |
| FR29 | Mỗi tài sản đa phương tiện có nguồn gốc đầy đủ | Mỗi bản ghi tài sản lưu khóa đối tượng trong kho, người đóng góp, ngày tải lên, giấy phép và URL nguồn gốc; bản ghi thiếu bất kỳ trường nào trong số đó bị từ chối tại biên endpoint |
| FR30 | Script audio phải có bằng chứng nguyên văn trong kho ngữ liệu | Mỗi câu khẳng định trong transcript phải truy về được một câu nguồn trong kho ngữ liệu hoặc được đánh dấu rõ là lời dẫn dắt biên tập; kiểm tra tự động chạy trước bước tổng hợp giọng nói và chặn việc tổng hợp nếu không đạt |

### 7.3. Yêu cầu phi chức năng

| Mã | Nhóm | Yêu cầu |
| --- | --- | --- |
| NFR01 | Hiệu năng | Độ trễ đầu-cuối p95 cho câu hỏi tiêu chuẩn không vượt 8 giây trong môi trường demo, được đo liên tục trong suốt quá trình phát triển thay vì đo ở cuối kỳ |
| NFR02 | Hiệu năng | Phản hồi gợi ý và thẻ tư vấn trong 2 giây không tính thời gian sinh của mô hình; các lệnh gọi API bên ngoài chạy song song với bước sinh để độ trễ của chúng bị ẩn đi |
| NFR03 | Hiệu năng | Trang chi tiết thực thể hiển thị trong 3 giây nhờ dữ liệu đồ thị đã đệm và ảnh thu nhỏ đã tối ưu |
| NFR04 | Độ chính xác | recall@1 truy hồi trên tập câu hỏi trong phạm vi đạt tối thiểu 95%, kể cả truy vấn không dấu, truy vấn dùng tên gọi khác và truy vấn diễn giải lại; recall trên riêng tập diễn giải lại được báo cáo tách ra vì đó là tập mà kênh ngữ nghĩa tồn tại để giải quyết |
| NFR05 | Độ tin cậy | Độ trung thực trích nguồn tối thiểu 85%; độ phủ trích nguồn trên các câu trả lời được tối thiểu 90% |
| NFR06 | An toàn | **Không một trường bịa nào trong thẻ tư vấn**, được khẳng định tự động trên toàn bộ tập kiểm thử thẻ |
| NFR07 | An toàn | Độ chính xác từ chối tối thiểu 90%; một câu trả lời khẳng định bịa đặt trên câu hỏi ngoài phạm vi tính là lỗi. Chỉ số này được báo cáo cùng NFR04 vì hai chỉ số đánh đổi lẫn nhau qua ngưỡng của cổng ngữ nghĩa (Mục 12.3, Bước 7) |
| NFR08 | Giải thích được | Mọi gợi ý phơi ra **đường đi đồ thị dạng text hoặc JSON qua tooltip** khi người dùng di chuột vào, và mọi quyết định truy hồi kiểm tra được qua endpoint truy vết |
| NFR09 | Khả dụng | Người truy cập lần đầu đặt được câu hỏi và nhận được gợi ý liên quan ngay lập tức, không có bước thiết lập, không có bảng khai sở thích và không cần hướng dẫn viết |
| NFR10 | Tiếp cận | Có văn bản thay thế cho nội dung không phải chữ; độ tương phản màu đủ; chat, thẻ và bản đồ điều hướng được bằng bàn phím; bản ghi hội thoại được công nghệ trợ giúp đọc ra; mỗi tệp audio có transcript văn bản và mỗi mô hình 3D có mô tả văn bản, theo WCAG 2.1 mức AA ở những phần áp dụng được [20] |
| NFR11 | Bảo mật | Xác thực trên mọi endpoint đọc hoặc ghi dữ liệu cá nhân; kiểm tra đầu vào; giới hạn loại và kích thước tệp; không có đường ghi nào không xác thực; máy chủ không mở giao diện mạng công khai trong cấu hình demo |
| NFR12 | Riêng tư | Ghi nhận hành vi cần sự đồng ý có thông báo; chỉ lưu dữ liệu cần cho gợi ý; hỗ trợ xuất và xóa |
| NFR13 | Nguồn gốc | Mọi phát biểu thực tế hiển thị đều truy về được một nguồn: một câu trong kho ngữ liệu, một trường bản ghi có cấu trúc kèm nguồn riêng của nó, hoặc một API bên ngoài có tên kèm mốc thời gian lấy dữ liệu |
| NFR14 | Toàn vẹn dữ liệu | Bản ghi có cấu trúc không thể lưu được nếu thiếu URL nguồn hoặc câu nguồn; ràng buộc này được áp ở mức cơ sở dữ liệu, không chỉ ở tầng ứng dụng |
| NFR15 | Bảo trì | Nạp dữ liệu, đồ thị, truy hồi, sinh, gợi ý, tư vấn và giao diện vẫn là các mô-đun có giao diện tách biệt |
| NFR16 | Tái lập | Định danh mô hình, checkpoint bộ điều hợp, phiên bản prompt, phiên bản kho ngữ liệu, thống kê đồ thị và cấu hình đánh giá được ghi trong mọi tệp báo cáo |
| NFR17 | Mở rộng | Thêm một vùng, danh mục, sự kiện, địa điểm hay cổ vật mới không cần sửa mã; thêm một loại thẻ tư vấn mới chỉ cần đăng ký một bộ sinh |
| NFR18 | Khả chuyển | Nền tảng chạy hoàn toàn trên một máy, không cần dịch vụ AI bên ngoài và không cần khóa API |
| NFR19 | Hiệu năng đa phương tiện | Mô hình 3D .glb tải về và hiển thị trong 3 giây trên kết nối 4G; audio narration bắt đầu phát trong 1 giây sau khi người dùng chọn story; tổng kích thước mỗi mô hình 3D không vượt 30 MB nhờ nén Draco/Meshopt. Vì audio được tổng hợp trước, ngân sách này không bao gồm thời gian tổng hợp giọng nói |
| NFR20 | Khả dụng ngoại tuyến | Khi mất kết nối Cloudflare R2 hoặc Azure, trang chi tiết F11 vẫn hiển thị đầy đủ nội dung văn bản, transcript và chip liên kết; chỉ phần 3D và trình phát audio hiển thị thông báo "tài sản tạm thời không khả dụng" thay vì để trang trắng |

## 8. Ràng buộc và Giả định

### 8.1. Ràng buộc

| Nhóm | Mô tả |
| --- | --- |
| Nhân lực | Một người phát triển, nên không có luồng công việc song song và không có rà soát mã nội bộ; hai hoạt động đánh giá cần một người đánh giá thứ hai 
| Dữ liệu | Nguồn bách khoa không đều theo danh mục: di tích được tư liệu hóa sâu trong khi nghệ thuật diễn xướng, làng nghề và lễ hội thì mỏng, nên cân bằng kho ngữ liệu là việc được xếp lịch chứ không phải một giả định |
| Dữ liệu | Dữ kiện sự kiện, địa điểm và cổ vật không tồn tại ở dạng máy đọc được trong các nguồn và phải soạn thủ công kèm trích nguồn |
| Ngôn ngữ | Tên riêng, tên gọi khác, dấu và cách gõ không dấu tiếng Việt không nhất quán, và tên đơn vị hành chính đã đổi trong các lần sắp xếp gần đây |
| Dữ liệu ngoài | API thời tiết và điểm quan tâm miễn phí, không cần khóa nhưng có giới hạn tần suất, và độ phủ điểm quan tâm do cộng đồng bản đồ tình nguyện tại Việt Nam không đồng đều |
| Đa phương tiện | Mô hình 3D của di sản Việt Nam có sẵn dưới giấy phép mở là rất ít, nên số địa điểm có trải nghiệm 3D bị giới hạn ở những gì tìm được và ghi công được, chứ không phải ở toàn bộ kho ngữ liệu |
| Đa phương tiện | Gói miễn phí của Cloudflare R2 và Azure for Students giới hạn dung lượng, nên tổng kích thước tài sản là một ràng buộc thiết kế chứ không phải một chi tiết vận hành |
| Lịch | Ngày lễ hội Việt Nam cho theo âm lịch, và các thư viện âm lịch đa dụng theo lịch Trung Quốc nên có thể lệch một ngày ở ranh giới UTC+7 |
| Đánh giá | Với một người phát triển và không có nền người dùng, độ liên quan của gợi ý và văn phong kể chuyện không thể đo ở quy mô thống kê; chúng được báo cáo dưới dạng đánh giá mẫu nhỏ kèm chỉ số đồng thuận và được ghi rõ là như vậy |
| Quyền | Các nguồn được sử dụng kèm ghi công cho một nguyên mẫu học thuật phi thương mại, và nội dung không ghi công được thì không dùng |

### 8.2. Giả định

- Các nguồn bách khoa và nguồn chính thống về văn hóa Huế và Đà Nẵng vẫn truy cập công khai được, và việc sử dụng lại cho một nguyên mẫu học thuật phi thương mại là được phép kèm ghi công.
- Dữ kiện về sự kiện, địa điểm và cổ vật có thể lấy từ ấn phẩm của trung tâm bảo tồn, bảo tàng và cơ quan quản lý đô thị, mỗi dữ kiện ghi kèm URL và câu nguồn trích dẫn được.
- Các API thời tiết và bản đồ công khai miễn phí vẫn dùng được không cần khóa ở lưu lượng của một buổi trình diễn.
- Máy trình diễn đủ tài nguyên để chạy đồng thời truy hồi, đồ thị tri thức, cơ sở dữ liệu và mô hình ngôn ngữ cục bộ ở quy mô nhỏ.
- Người dùng có trình duyệt và kết nối mạng, và họ chỉ gõ văn bản mà không tải tệp lên.
- Có thể tìm được mô hình 3D dùng lại được kèm giấy phép cho phép ghi công cho một số địa điểm trong địa bàn thử nghiệm, và nếu không tìm được cho một địa điểm nào thì địa điểm đó vẫn hiển thị đầy đủ mà không có phần 3D.
- Mục tiêu là chứng minh tính khả thi của luồng xử lý và độ tin cậy đo được, không phải triển khai một hệ thống lưu trữ quy mô quốc gia.
- Phần kể chuyện của AI là gợi ý cần biên tập viên xác nhận, và bản ghi có cấu trúc chỉ có căn cứ trong giới hạn nguồn đã trích của nó.
- Việc ghi nhận hành vi có sự đồng ý, và người dùng có thể khám phá mà không cần hồ sơ, khi đó gợi ý chỉ dựa vào độ gần đồ thị với chủ đề đang xem.
- Có thể mời được một cố vấn chuyên môn để rà soát tính chính xác của các bản ghi lễ hội và cổ vật soạn thủ công.
- Ảnh được quản lý qua metadata và chú thích đã xác nhận thay vì bằng nhận dạng tự động nội dung ảnh.

## 9. Đối tượng người dùng / Các bên liên quan

| Nhóm | Nhu cầu | Nền tảng giúp thế nào |
| --- | --- | --- |
| Học sinh, sinh viên, người trẻ | Tìm hiểu văn hóa nhanh và trực quan, theo tò mò của chính mình chứ không theo một giáo trình cố định | Sở thích được suy ra từ chính hành vi duyệt xem của họ, gợi ý xuyên miền kèm lý do nhìn thấy được, câu trả lời có trích nguồn, khám phá dòng thời gian, và trải nghiệm 3D kèm audio cho các địa điểm đã số hóa |
| Khách du lịch trong nước và khách quan tâm văn hóa | Quyết định xem gì, và biết làm sao để thật sự đi dự được | Lịch sự kiện kèm quy đổi lịch, bản đồ địa điểm, thẻ thời tiết và chuẩn bị, thẻ điểm quan sát và chỗ gửi xe |
| Giáo viên | Tư liệu trực quan, có nguồn, dùng được trong bài học và hoạt động ngoại khóa | Duyệt theo danh mục và vùng, trang chi tiết thực thể có trích nguồn dùng được làm tài liệu tham khảo, trích xuất thực thể trên đoạn được cung cấp, audio narration hai ngôn ngữ kèm transcript dùng được trong lớp |

## 10. Công nghệ sử dụng

| Lớp | Thành phần | Công nghệ | Mục đích |
| --- | --- | --- | --- |
| Frontend | Framework | Next.js 14 App Router, React 18, TypeScript | Chat dạng thẻ, khám phá, trang xem hồ sơ sở thích, trang chi tiết, giao diện quản trị |
| Frontend | Giao diện | Antd | Hệ thống thiết kế cho thẻ, kiểu chữ và bố cục co giãn |
| Frontend | Bản đồ | Leaflet với tile OpenStreetMap | Hiển thị bản đồ địa điểm |
| Frontend | Trình xem 3D | Three.js với `<model-viewer>` và nén Draco/Meshopt | Hiển thị mô hình .glb của địa điểm, xoay và phóng to |
| Backend | Framework API | Python, FastAPI, Pydantic v2 | REST API, điều phối, kiểm tra dữ liệu, đặc tả OpenAPI |
| Backend | Máy chủ | Uvicorn | Máy chủ ASGI với threadpool để đẩy bước sinh chặn ra khỏi event loop |
| Dữ liệu | Cơ sở dữ liệu quan hệ | PostgreSQL 16 với SQLAlchemy và Alembic | Người dùng, hồ sơ sở thích, sự kiện tương tác, địa điểm, sự kiện, cổ vật, điểm quan tâm, tài sản đa phương tiện, log gợi ý, sổ kiểm toán |
| Dữ liệu | Kho vector | Tiện ích mở rộng pgvector [21] | Vector nhúng của đoạn cho kênh truy hồi ngữ nghĩa |
| Dữ liệu | Đồ thị tri thức | NetworkX, dựng tất định trong RAM khi khởi động | Thực thể, tài liệu, vùng, danh mục, đơn vị hành chính, năm, nguồn gốc |
| Dữ liệu | Kho ngữ liệu | Tệp văn bản đã chuẩn hóa kèm chỉ mục và từ điển tên gọi khác | Tài liệu nguồn có định vị ở mức đoạn |
| Dữ liệu | Kho tài sản 3D | Cloudflare R2, gói miễn phí 10 GB [23] | Mô hình .glb, phân phát qua CDN không tính phí truyền ra |
| Dữ liệu | Kho tài sản audio | Azure Blob Storage, Azure for Students [24] | Tệp audio narration hai ngôn ngữ kèm transcript |
| Truy hồi | Thưa theo từ khóa | BM25 trên token từ | Chính xác với tên riêng, thuật ngữ ít gặp và cách diễn đạt nguyên văn |
| Truy hồi | Không phụ thuộc dấu | BM25 trên n-gram ký tự 4 đã bỏ dấu | Gõ tiếng Việt không dấu và chịu được sai chính tả |
| Truy hồi | Ngữ nghĩa dày | Mô hình nhúng câu đa ngữ [22] với tìm kiếm tương đồng qua pgvector | Khớp cách diễn giải lại và từ đồng nghĩa |
| Truy hồi | Hợp nhất | Reciprocal rank fusion [9] | Kết hợp các bảng xếp hạng có thang điểm không tương thích mà không cần chuẩn hóa |
| Truy hồi | Xếp hạng lại bằng đồ thị | Lan truyền có trọng số hai bước với giảm chấn ở đỉnh trung tâm | Neo, mở rộng và xếp hạng lại theo quan hệ |
| AI | Mô hình ngôn ngữ | Qwen2.5-3B-Instruct lượng tử hóa 4-bit [17] với bộ điều hợp LoRA, phục vụ cục bộ qua MLX [18] | Kể chuyện di sản tiếng Việt, định dạng trích nguồn, từ chối, đính chính giả định sai, JSON thực thể |
| AI | Tinh chỉnh | LoRA [7] qua MLX, bộ điều hợp hạng thấp trên các lớp trên với che mất mát ở phần prompt | Dạy văn phong, định dạng trích nguồn và hành vi từ chối thay vì dạy dữ kiện |
| AI | Trích xuất | Danh sách thực thể tuyển chọn, từ vựng phân loại đóng, biểu thức chính quy | Trích xuất thực thể, đơn vị hành chính và năm một cách tất định, không bịa |
| AI | Phân loại ý định | Dựa trên luật và từ vựng trên văn bản đã bỏ dấu, sáu lớp | Chọn bộ sinh thẻ tư vấn; kiểm toán được và rẻ |
| AI | Gợi ý | Lan truyền đồ thị với độ gần hồ sơ, thưởng xuyên danh mục và đa dạng maximal marginal relevance [10] | Gợi ý cá nhân hóa, giải thích được |
| AI | Tổng hợp giọng nói | Edge TTS giọng tiếng Việt và tiếng Anh, chạy ngoại tuyến một lần khi soạn nội dung [25] | Audio narration cho story, sinh trước chứ không sinh lúc chạy |
| Ngoài | Thời tiết | Open-Meteo, không cần khóa [12] | Xác suất mưa và nhiệt độ theo giờ cho lời khuyên chuẩn bị |
| Ngoài | Điểm quan tâm | Overpass trên OpenStreetMap [13] | Bãi xe, điểm quan sát, cửa hàng nghề và quà gần địa điểm |
| Ngoài | Mã hóa địa lý | Nominatim [14] có đệm một lần, và tọa độ Wikidata [15] | Tọa độ địa điểm |
| Bảo mật | Băm mật khẩu | argon2id [19] | Lưu trữ thông tin đăng nhập |
| Bảo mật | Phiên | JWT trong cookie HttpOnly, SameSite | Phiên đã xác thực mà không phơi token cho script |
| Chất lượng | Kiểm thử | pytest, Playwright | Kiểm thử đơn vị, tích hợp, API và đầu-cuối gồm phép khẳng định không-bịa-trường |
| Chất lượng | CI/CD | Git, GitHub, GitHub Actions, Docker Compose | Quản lý phiên bản, kiểm tra tự động, môi trường tái lập được |
| Chất lượng | Tài liệu | Markdown, Mermaid, OpenAPI | Yêu cầu, kiến trúc, API và báo cáo đánh giá |

Bốn quyết định công nghệ cần được biện minh tường minh, vì mỗi quyết định đều lệch khỏi lựa chọn mặc định.

**Ba kênh truy hồi thay vì một.** Truy vấn văn hóa tiếng Việt đến ở ba dạng: tên riêng chính xác, phiên âm không dấu, và diễn giải lại. Truy hồi thưa theo từ khóa xử lý được dạng thứ nhất và thất bại ở dạng thứ ba; truy hồi vector xử lý được dạng thứ ba và yếu hơn với tên riêng ít gặp; không kênh nào xử lý được dạng thứ hai, vì bỏ dấu phá hủy chính những token mà chỉ mục ở mức từ dựa vào. Hợp nhất cả ba là lý do nền tảng trả lời được cùng một câu hỏi dù người dùng viết *"lăng Khải Định ở đâu"*, *"lang khai dinh o dau"*, hay *"vua Khải Định được chôn ở chỗ nào"*.

**PostgreSQL với pgvector thay vì một cơ sở dữ liệu vector chuyên dụng.** Kho ngữ liệu ở quy mô hàng trăm đoạn, và nền tảng đã cần một cơ sở dữ liệu quan hệ cho người dùng, hồ sơ, sự kiện, địa điểm và cổ vật. Thêm một kho dữ liệu thứ hai chỉ để chứa vector nhúng ở quy mô này sẽ thêm chi phí vận hành mà không thêm năng lực, và nó xé nguồn gốc dữ liệu ra hai hệ thống.

**Mô hình cục bộ thay vì API AI bên ngoài.** Điều này loại bỏ chi phí API, loại bỏ phụ thuộc vào nhà cung cấp bên ngoài, và giữ văn bản kho ngữ liệu văn hóa ở lại trên máy — điều này quan trọng vì một phần tư liệu văn hóa thuộc về cộng đồng và cách xử lý nó là một câu hỏi về quản trị, không chỉ về kỹ thuật.

**Audio sinh trước thay vì tổng hợp giọng nói lúc chạy.** Script narration được kiểm tra bằng chứng (FR30) rồi mới tổng hợp thành tệp audio một lần khi soạn nội dung, và tệp được lưu như một tài sản bất biến. Nếu tổng hợp lúc chạy, một script chưa qua kiểm tra có thể được phát ra cho người dùng, và cùng một story sẽ đọc khác nhau giữa hai lần nghe. Sinh trước cũng loại bỏ độ trễ tổng hợp khỏi ngân sách thời gian của NFR19 và giữ toàn bộ đường sinh giọng nói ngoài đường xử lý yêu cầu.

## 11. Phương pháp và Kế hoạch phát triển

### 11.1. Phương pháp phát triển

Dự án dùng Agile với vòng lặp ngắn một tuần và một buổi trình diễn cho giảng viên hướng dẫn mỗi vòng, gồm lập kế hoạch, phát triển, kiểm thử và tổng kết, theo tinh thần của Scrum nhưng lược bỏ các vai trò không áp dụng được cho một nhóm một người [16]. Vòng ngắn là phù hợp vì chất lượng trích xuất, chất lượng truy hồi, độ liên quan của gợi ý và tính hữu dụng của tư vấn chỉ có thể đánh giá trên dữ liệu thật và tương tác thật; chúng không thể đặc tả chính xác từ trước.

### 11.2. Hai quy tắc trình tự

**Việc rủi ro cao làm trước.** Cân bằng danh mục kho ngữ liệu và các bản ghi có cấu trúc soạn thủ công mà mọi thẻ tư vấn phụ thuộc vào được xếp sớm, và thời gian phản hồi đầu-cuối được đo ngay từ khi cơ sở dữ liệu và xác thực xuất hiện thay vì trong giai đoạn kiểm thử, vì một vấn đề về độ trễ phát hiện ở hai tuần cuối thì không thể sửa được ở tầng kiến trúc.

**Không lớp nào được xây trên một lớp chưa đo.** Truy hồi được đo trước khi tinh chỉnh bước sinh; bước sinh được đo trước khi thêm cá nhân hóa; độ tin cậy được đo lại sau khi lớp tư vấn xuất hiện. Đây là điều làm cho tuyên bố không-suy-giảm của mục tiêu O11 trở nên khả thi.

### 11.3. Kế hoạch phát triển

| Giai đoạn | Tuần | Nội dung chính | Kết quả |
| --- | --- | --- | --- |
| Khởi động | 1–2 | Phân tích vấn đề, khảo sát nguồn, chọn địa bàn và chủ đề, yêu cầu, lược đồ dữ liệu, wireframe, phương pháp đánh giá | Đề cương, SRS, từ điển dữ liệu, wireframe, kế hoạch đánh giá |
| Sprint 1 — Nền tảng | 3 | PostgreSQL với migration và Docker Compose; mô hình dữ liệu; đăng ký, đăng nhập và quản lý phiên; ghi nhận tương tác có đồng ý; xuất và xóa dữ liệu cá nhân; hệ thống thiết kế; đo độ trễ lần đầu | Tài khoản, lưu bền, ghi log sự kiện, baseline độ trễ |
| Sprint 2 — Nền tri thức | 4 | Mở rộng kho ngữ liệu tới mức cân bằng danh mục đầy đủ; trích tên gọi khác; soạn bản ghi địa điểm, sự kiện và cổ vật kèm kiểm tra nguồn; dựng lại đồ thị; sinh lại tập vàng đánh giá; **thêm bộ câu hỏi diễn giải lại vào tập đánh giá và đo baseline hai kênh trên bộ đó**; đo lại truy hồi | Kho ngữ liệu hoàn chỉnh, đồ thị tri thức, ba tập bản ghi có cấu trúc, tập đánh giá đã làm mới kèm baseline diễn giải lại |
| Sprint 3 — Truy hồi và trả lời | 5 | Kênh nhúng dày với pgvector; hợp nhất ba kênh; xếp hạng lại bằng đồ thị; các cổng từ chối kèm **hiệu chỉnh ngưỡng tương đồng ngữ nghĩa trên tập ngoài phạm vi**; endpoint truy vết; kiểm tra trích nguồn; **đo tách kênh** và đo chất lượng truy hồi và trả lời | Luồng Hybrid RAG + GraphRAG với recall, trích nguồn và từ chối đã đo, kèm bảng đo tách kênh |
| Sprint 4 — Cá nhân hóa | 6–7 | Suy ra sở thích ngầm định có suy giảm theo thời gian; trang xem và điều chỉnh hồ sơ; độ gần đồ thị, độ gần hồ sơ, thưởng xuyên danh mục, xếp hạng lại theo đa dạng; endpoint gợi ý trả về đường đi giải thích; ghi log gợi ý; trang khám phá và chi tiết có dải nội dung liên quan | Khám phá và tìm kiếm cá nhân hóa, gợi ý giải thích được |
| Sprint 5 — Tư vấn chủ động | 8–9 | Bộ phân loại ý định sáu lớp kèm tập câu hỏi gán nhãn; sổ đăng ký ý định–thẻ; tích hợp thời tiết; tích hợp điểm quan tâm có đệm; luật danh mục chuẩn bị; gọi API ngoài song song chồng lên bước sinh; suy giảm mềm; **đo lại độ trung thực trích nguồn và độ chính xác từ chối để chứng minh không suy giảm** | Thẻ tư vấn có kiểu cho ý định nghiên cứu, tham dự và lên kế hoạch đi, kèm số đo trước–sau |
| Sprint 6 — Giao diện và đa phương tiện | 10 | Sổ đăng ký bộ kết xuất thẻ; trang chi tiết thực thể kiểu Tapestry (ảnh lớn, danh sách story, chip liên kết); dòng thời gian; khung bản đồ; **thu thập và nén mô hình 3D, dựng pipeline kiểm tra bằng chứng cho script rồi tổng hợp audio hai ngôn ngữ, tải lên R2 và Azure Blob, nhúng trình xem Three.js kèm audio player và transcript**; bảng điều khiển và giao diện rà soát cho quản trị; rà soát khả năng tiếp cận | Giao diện thẻ tương tác hoàn chỉnh kèm trải nghiệm 3D và audio |
| Sprint 7 — Hành trình | 11 | Hoàn thiện hành trình nghiên cứu đầu-cuối (cổ vật → bảo tàng đang giữ → cổ vật cùng thời kỳ → làng nghề liên quan) và hành trình tham dự (lễ hội → lịch → địa điểm → thời tiết → chuẩn bị → điểm quan sát → chỗ gửi xe); đệm cho trượt tiến độ | Hai hành trình trình diễn hoàn chỉnh |
| Kiểm thử | 12–13 | Bộ kiểm thử đơn vị, tích hợp, API và đầu-cuối cùng CI; phép khẳng định không-bịa-trường; toàn bộ chỉ số gồm độ chính xác ý định và precision gợi ý với người đánh giá thứ hai; nghiên cứu người dùng; khắc phục hiệu năng | Báo cáo kiểm thử và báo cáo đánh giá |
| Kết thúc | 14–15 | Tài liệu kiến trúc, API và lược đồ; rà soát riêng tư và đạo đức; video trình diễn, slide và hướng dẫn sử dụng; báo cáo cuối | Bản chấp nhận cuối cùng và báo cáo |

### 11.4. Chất lượng, Rà soát và Quản lý phiên bản

Mã nguồn được quản lý bằng Git. Mọi thay đổi về luật dựng đồ thị, prompt, mô hình, checkpoint bộ điều hợp, kho ngữ liệu hoặc lược đồ cơ sở dữ liệu đều được ghi vào changelog, vì mỗi thay đổi đó làm mất hiệu lực các chỉ số đã báo cáo trước đó. Tích hợp liên tục chạy lint và bộ kiểm thử trước khi hợp nhất, và pull request được dùng cho các mô-đun truy hồi, gợi ý và tư vấn.

Vì không có người phát triển thứ hai, hai hoạt động đánh giá dùng người đánh giá bên ngoài. **Nhãn vàng thực thể** sinh tự động từ đồ thị tất định được đánh dấu là do máy điền trước và cần người rà soát trước báo cáo cuối, và báo cáo phải nói rõ phần nào đã được rà soát; ở trạng thái đó chúng đo được việc mô hình có học được tập luật trích xuất hay không thay vì việc trích xuất có đúng hay không. **Độ liên quan của gợi ý** được hai người đánh giá trên cùng một tập hạt giống, và độ đồng thuận giữa hai người được báo cáo cùng với precision.

Với nội dung văn hóa, mọi trường có cấu trúc đều ghi URL nguồn và câu nguồn, và trạng thái rà soát của biên tập viên được lưu lại. Với các thành phần AI, mọi tệp báo cáo ghi định danh mô hình, checkpoint bộ điều hợp, phiên bản prompt, phiên bản kho ngữ liệu và cấu hình đánh giá.

## 12. Tổng quan kiến trúc hệ thống

### 12.1. Mô tả kiến trúc

Kiến trúc gồm bảy lớp.

**1. Lớp trình bày.** Chat dạng thẻ, khám phá cá nhân hóa, trang chi tiết thực thể kiểu Tapestry (ảnh lớn, danh sách story, trình xem 3D, audio player kèm transcript, chip liên kết), dòng thời gian, khung bản đồ, khung trích nguồn, tooltip đường đi đồ thị cho gợi ý, trang xem hồ sơ sở thích, và giao diện quản lý nội dung và rà soát cho người quản trị.

**2. Lớp ứng dụng và API.** Xác thực và quản lý phiên, điều phối chat, tìm kiếm lai, gợi ý, tư vấn, kiểm tra và truy vết đồ thị, quản lý nội dung, bản ghi có cấu trúc và tài sản đa phương tiện kèm kiểm tra dữ liệu, bảng điều khiển, đánh giá, và xuất cũng như xóa dữ liệu cá nhân.

**3. Lớp nạp dữ liệu.** Phân giải và tải nguồn có đệm và thử lại, chuẩn hóa văn bản, tách đoạn theo mục kèm định vị nguồn, trích tên gọi khác từ trang chuyển hướng và từ mẫu câu mở đầu, loại bỏ trang trùng nội dung cũng như trang định hướng, và nạp tài sản đa phương tiện gồm nén mô hình 3D, kiểm tra bằng chứng cho script narration và tổng hợp giọng nói ngoại tuyến.

**4. Lớp xử lý tri thức.** Trích xuất thực thể tất định với danh sách tuyển chọn và từ vựng phân loại đóng, nhận diện đơn vị hành chính, trích xuất thời gian, nhúng vector cho đoạn phục vụ kênh ngữ nghĩa, liên kết thực thể qua từ điển tên gọi khác, và dựng đồ thị tri thức với quan hệ có kiểu, có trọng số và liên kết về nguồn.

**5. Lớp lưu trữ.** Tệp kho ngữ liệu kèm định vị đoạn, đồ thị tri thức trong RAM, vector nhúng của đoạn trong pgvector, PostgreSQL cho người dùng, hồ sơ sở thích, sự kiện tương tác, địa điểm, sự kiện kèm các phần, cổ vật, điểm quan tâm, siêu dữ liệu tài sản đa phương tiện, log gợi ý và sổ kiểm toán, cùng kho đối tượng bên ngoài cho tệp 3D và audio.

**6. Lớp điều phối AI.** Phân tích truy vấn gồm phạm vi vùng và danh mục, ý định, và sự phân biệt giữa chủ thể của câu hỏi với giả định mà nó chứa; truy hồi Hybrid RAG ba kênh; neo, lan truyền và xếp hạng lại bằng đồ thị; tổ hợp bối cảnh; các cổng từ chối; sinh văn bản cục bộ; và kiểm tra trích nguồn.

**7. Lớp cá nhân hóa và tư vấn.** Duy trì hồ sơ có suy giảm theo thời gian, gợi ý theo đường đi đồ thị với thưởng xuyên danh mục và xếp hạng lại theo đa dạng, phân loại ý định sáu lớp, và sổ đăng ký ý định–bộ sinh thẻ kèm bộ điều hợp bên ngoài cho thời tiết và điểm quan tâm.

Nguyên tắc thiết kế ở Mục 4.6 được bảo đảm ngay tại biên giữa lớp 6 và lớp 7: lớp 6 sinh ra văn bản kể chuyện, lớp 7 sinh ra đối tượng thẻ có kiểu, và đối tượng thẻ không bao giờ đi qua lớp 6.

### 12.2. Sơ đồ ngữ cảnh hệ thống

*Hình 1. Sơ đồ ngữ cảnh hệ thống (Mức 0)*

```
                    ┌───────────────────────────────┐
                    │      Quản trị / Biên tập      │
                    └───────────────┬───────────────┘
        F01 Yêu cầu đăng nhập       │ → Phản hồi đăng nhập kèm phiên
        F02 Quản lý nội dung        │ → Kết quả CRUD + dựng lại đồ thị
        F03 Quản lý bản ghi         │ → Kết quả kiểm tra nguồn
        F04 Rà soát trích xuất      │ → Trạng thái cập nhật + sổ kiểm toán
        F05 Yêu cầu bảng điều khiển │ → Dữ liệu tổng quan
        F06 Yêu cầu đánh giá        │ → Báo cáo chỉ số
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                   H e r i t a g e G r a p h                          │
│                                                                      │
│  F13 Phân tích nội dung ─┐ trích xuất tất định, không gọi mô hình    │
│  F14 Sinh câu trả lời   ─┴─ mô hình tinh chỉnh chạy cục bộ           │
│                                                                      │
│  Các kho nội bộ (cơ sở dữ liệu quan hệ, chỉ mục vector, đồ thị       │
│  tri thức) nằm bên trong biên này và chỉ xuất hiện ở phân rã Mức 1.  │
│                                                                      │
└──────┬────────────────────────┬──────────────────────┬───────────────┘
       │                        │                      │
       │                        │ Yêu cầu dự báo       │ Yêu cầu tệp .glb
       │                        │  → Phản hồi dự báo   │  → Tệp mô hình 3D
       │                        │ Yêu cầu điểm quan tâm│ Yêu cầu tệp audio
       │                        │  → Phản hồi điểm QT  │  → Audio + transcript
       │                        ▼                      ▼
       │            ┌───────────────────────┐ ┌──────────────────────┐
       │            │  Dịch vụ dữ liệu      │ │  Kho tài sản đa      │
       │            │  bên ngoài            │ │  phương tiện         │
       │            │  (thời tiết, bản đồ,  │ │  (Cloudflare R2,     │
       │            │   mã hóa địa lý)      │ │   Azure Blob)        │
       │            └───────────────────────┘ └──────────────────────┘
       │
       │ F07 Đăng ký / quản lý tài khoản → Xác nhận + hồ sơ sở thích
       │ F08 Tìm kiếm lai theo sở thích  → Kết quả xếp hạng cá nhân hóa
       │ F09 Truy vấn ngôn ngữ tự nhiên  → Câu trả lời + trích nguồn,
       │                                   hoặc phát biểu thiếu bằng chứng
       │ F10 Bối cảnh chủ động           → Thẻ tư vấn có kiểu
       │ F11 Yêu cầu chi tiết thực thể   → Chi tiết Tapestry + story
       │ F12 Yêu cầu trải nghiệm 3D      → Trình xem 3D + audio narration
       ▼
┌───────────────────────────────┐
│         Người dùng            │
└───────────────────────────────┘
```

Sơ đồ ngữ cảnh thể hiện HeritageGraph là một tiến trình duy nhất trao đổi dữ liệu với bốn thực thể ngoài: **Quản trị/Biên tập**, **Người dùng**, **Dịch vụ dữ liệu bên ngoài** cho thời tiết, bản đồ và mã hóa địa lý, và **Kho tài sản đa phương tiện** cho tệp 3D và audio. Các thành phần nội bộ — cơ sở dữ liệu quan hệ, chỉ mục vector và đồ thị tri thức — có chủ đích không được vẽ ở mức này vì chúng nằm bên trong biên hệ thống; chúng xuất hiện ở phân rã Mức 1. Mỗi luồng yêu cầu của tác nhân người có một luồng phản hồi tương ứng, tạo thành tổng cộng **14 cặp yêu cầu/phản hồi** tương ứng F01–F14 ở Mục 7.1; các luồng đi tới hai dịch vụ ngoài là luồng phụ trợ của F10 và F12, không được đếm thêm.

Ba tính chất của sơ đồ này cần được nêu rõ ở hội đồng.

**Không có dịch vụ AI bên ngoài nào.** Phân tích nội dung là trích xuất tất định không gọi mô hình, và sinh câu trả lời chạy trên một mô hình tinh chỉnh cục bộ. Vì vậy văn bản kho ngữ liệu văn hóa không bao giờ rời khỏi hệ thống, và các yêu cầu gửi ra ngoài duy nhất chỉ mang theo một tọa độ, một tên địa danh, một ngày, hoặc một khóa tệp tài sản. Đây là một tính chất về quản trị dữ liệu, không chỉ là một quyết định về chi phí.

**Kho tài sản là hạ tầng phân phát, không phải nhà cung cấp AI.** R2 và Azure Blob chỉ giữ tệp nhị phân bất biến đã được kiểm tra bằng chứng và tổng hợp ngoại tuyến trước đó (Mục 10, "Audio sinh trước"). Không có nội dung nào được sinh ra ở phía chúng, và khi chúng không truy cập được thì trang chi tiết vẫn hiển thị đầy đủ phần văn bản (NFR20).

**Cá nhân hóa nhìn thấy được ở Mức 0 thay vì bị ẩn trong một bước xếp hạng.** Hồ sơ sở thích là dữ liệu được suy ra ngầm từ hành vi của Người dùng và được đọc lại qua đầu ra đã xếp hạng của F08, F09 và F11, đồng thời có thể xem và điều chỉnh trong trang quản lý tài khoản F07. Vì vậy sự thích ứng theo từng người là một phần hành vi bên ngoài của hệ thống, không phải một chi tiết hiện thực nội bộ.

### 12.3. Luồng truy hồi: Hybrid RAG + GraphRAG

Luồng truy hồi là phần lõi kỹ thuật của nền tảng, nên được đặc tả ở đây theo đúng thứ tự thực thi.

**Bước 1 — Dựng chỉ mục, một lần khi khởi động.** Tài liệu được tách thành đoạn với tiêu đề mục được gán trọng số cao hơn phần thân. Ba chỉ mục được dựng trên cùng một tập đoạn: một chỉ mục BM25 trên token từ, một chỉ mục BM25 trên n-gram ký tự 4 đã bỏ dấu, và một chỉ mục vector nhúng trong pgvector. Đồ thị tri thức được dựng trong cùng lượt đi từ danh sách thực thể tuyển chọn, từ vựng phân loại đóng, nhận diện đơn vị hành chính và trích xuất thời gian, với mọi đỉnh liên kết về chuỗi nguồn đã sinh ra nó.

**Bước 2 — Phân tích truy vấn.** Truy vấn được phân tích theo ba trục: phạm vi vùng và danh mục; ý định, thuộc một trong sáu lớp nghiên cứu, dự sự kiện, lên kế hoạch đi, tìm hiểu, so sánh hoặc kiểm chứng; và sự tách biệt giữa chủ thể của câu hỏi với giả định mà nó chứa, để một câu dạng *"X ở Y đúng không"* được trả lời về X thay vì về Y.

**Bước 3 — Truy hồi ba kênh, Hybrid RAG.** Mỗi kênh xếp hạng đoạn độc lập. Kênh từ chính xác với tên riêng, kênh n-gram hấp thụ việc thiếu dấu và biến thể chính tả, và kênh vector khớp cách diễn giải lại và từ đồng nghĩa. Ba bảng xếp hạng được kết hợp bằng reciprocal rank fusion [9], phương pháp không cần chuẩn hóa điểm vì nó dùng vị trí hạng thay vì độ lớn của điểm.

**Bước 4 — Neo đồ thị, GraphRAG.** Nhãn thực thể và tên gọi khác được khớp với truy vấn, ưu tiên khớp dài nhất, cho ra các hạt giống đồ thị. Việc truy vấn có neo được vào một thực thể, tài liệu, vùng hay danh mục đã biết hay không được ghi lại, vì đó là tín hiệu chính phân biệt câu hỏi trong phạm vi với câu hỏi ngoài phạm vi.

**Bước 5 — Lan truyền đồ thị.** Từ các hạt giống, độ gần lan truyền hai bước trên các quan hệ có kiểu, có trọng số, kèm suy giảm và kèm giảm chấn ở các đỉnh trung tâm để một đỉnh danh mục rộng không tràn ngập tập kết quả. Đây là điều làm nổi lên những tài liệu chia sẻ cùng đơn vị hành chính, cùng thời kỳ hoặc cùng được nhắc chung với chủ thể truy vấn, dù chúng chia sẻ rất ít từ vựng với nó.

**Bước 6 — Hợp nhất và cho điểm hai tầng.** Đoạn ứng viên nhận một điểm ở mức đoạn từ bằng chứng từ khóa và vector cộng phần thưởng theo tiêu đề phù hợp ý định, và một điểm ở mức tài liệu cộng thêm độ gần đồ thị và phần thưởng khi truy vấn gọi đúng tên tài liệu. Điểm tài liệu chọn tài liệu nào trả lời, và điểm đoạn chọn đoạn nào trong tài liệu đó — việc tách hai điểm ngăn nhiễu từ vựng quyết định thứ tự giữa các đoạn gần giống nhau của tài liệu đúng.

**Bước 7 — Các cổng từ chối.** Trước khi sinh bất kỳ câu trả lời nào, bằng chứng đã truy hồi phải vượt các cổng cấu trúc: truy vấn phải neo được vào một đỉnh đồ thị đã biết; một tên riêng được gọi phải có bằng chứng hỗ trợ trong đoạn đã truy hồi thay vì chỉ trong một đoạn tương tự; các đơn vị hành chính được gọi trong truy vấn phải là những đơn vị mà kho ngữ liệu biết; và đoạn tốt nhất phải vượt **hoặc** ngưỡng độ phủ từ vựng **hoặc** ngưỡng độ tương đồng ngữ nghĩa. Nếu một cổng nào không đạt, bối cảnh để rỗng và mô hình sinh ra một lời từ chối tường minh — hành vi mà nó đã được tinh chỉnh để sinh ra, nên việc từ chối nằm trong trọng số mô hình chứ không chỉ nằm trong một câu điều kiện.

Cổng cuối cùng là chỗ mà kênh vector đòi một thay đổi thiết kế, và đây là điểm cần nêu rõ vì bỏ qua nó sẽ làm kênh vector trở nên vô dụng. Một cổng chỉ đo độ phủ **từ vựng** sẽ loại đúng những đoạn mà kênh vector tồn tại để tìm ra: đoạn diễn đạt cùng một ý bằng từ khác thì theo định nghĩa có độ phủ từ vựng thấp. Vì vậy cổng phải là một phép tuyển giữa hai loại bằng chứng, không phải một phép hợp. Đánh đổi đi kèm cũng phải được nêu: độ tương đồng cosine không bao giờ tiến về không, kể cả với đoạn không liên quan, nên một ngưỡng ngữ nghĩa đặt quá thấp sẽ nhận cả câu hỏi ngoài phạm vi và làm giảm độ chính xác từ chối. Ngưỡng vì vậy được hiệu chỉnh trên tập câu hỏi ngoài phạm vi trước khi được chốt, và cả hai chỉ số — recall trên câu diễn giải lại (NFR04) và độ chính xác từ chối (NFR07) — được báo cáo cùng nhau để đánh đổi hiện ra thành số thay vì bị ẩn đi.

**Bước 8 — Tổ hợp bối cảnh và sinh văn bản.** Các đoạn đã chọn được tổ hợp trong một ngân sách ký tự, kèm thay thế theo ý định để câu hỏi về vị trí nhận được đoạn có nêu tên tỉnh và câu hỏi hành chính nhận được đoạn có nêu tên phường. Bối cảnh đã tổ hợp và câu hỏi được gửi tới mô hình tinh chỉnh cục bộ, mô hình này sinh ra phần kể chuyện kết thúc bằng một trích nguồn dẫn nguyên văn một câu nguồn kèm URL của nó.

**Bước 9 — Kiểm tra trích nguồn và truy vết.** Trích nguồn được sinh ra được đối chiếu với bối cảnh đã truy hồi. Toàn bộ quyết định — hạt giống đồ thị, hạng theo từng kênh, độ gần đồ thị, các thành phần cho điểm, kết quả từng cổng — có thể xem qua endpoint truy vết, nên mọi câu trả lời đều kiểm toán được sau khi đã sinh ra.

### 12.4. Luồng xử lý chính

**Nạp nội dung.** Biên tập viên thêm một tài liệu; hệ thống chuẩn hóa, tách thành đoạn kèm định vị nguồn, trích xuất thực thể, đơn vị hành chính và năm một cách tất định kèm chuỗi bằng chứng, tính vector nhúng cho đoạn, và dựng lại đồ thị với các đỉnh mới liên kết về nguồn. Biên tập viên thêm một bản ghi địa điểm, sự kiện hoặc cổ vật; hệ thống kiểm tra rằng mọi trường sự kiện đều có URL nguồn và câu nguồn, từ chối bản ghi nếu không, lưu bền nó, và liên kết nó với đỉnh đồ thị tương ứng.

**Nạp tài sản đa phương tiện.** Biên tập viên thêm một mô hình 3D; hệ thống kiểm tra giấy phép và URL nguồn, nén hình học, tải lên kho đối tượng và ghi bản ghi siêu dữ liệu. Biên tập viên soạn một script narration; hệ thống đối chiếu từng câu khẳng định với kho ngữ liệu, từ chối script nếu có câu không truy được về nguồn và không được đánh dấu là lời dẫn dắt biên tập, rồi mới tổng hợp giọng nói cho hai ngôn ngữ, lưu tệp cùng transcript, và liên kết chúng với story tương ứng. Không có bước nào trong luồng này chạy lúc người dùng gửi yêu cầu.

**Hỏi đáp.** Luồng ở Mục 12.3 chạy, cho ra hoặc phần kể chuyện kèm trích nguồn, hoặc một phát biểu tường minh rằng bằng chứng hiện có không đủ.

**Cá nhân hóa.** Song song với việc trả lời, chủ thể của câu hỏi trở thành hạt giống gợi ý. Ứng viên được cho điểm theo độ gần đồ thị với hạt giống, độ gần đồ thị với hồ sơ sở thích, một phần thưởng cho việc thuộc danh mục văn hóa khác nhưng vẫn được nối bởi đường đi thật, và một phần trừ cho các mục đã xem. Danh sách xếp hạng sau đó được đa dạng hóa. Mỗi mục trả về kèm đường đi đồ thị đã sinh ra nó, để giao diện có thể nói rõ vì sao nó được gợi ý.

**Tư vấn chủ động.** Ý định phát hiện được chọn ra các bộ sinh thẻ từ sổ đăng ký. Bộ sinh đọc bản ghi có kiểu và, khi cần, gọi dịch vụ ngoài với tọa độ địa điểm và ngày sự kiện. Các lệnh gọi ra ngoài được phát song song với bước sinh của mô hình để độ trễ của chúng bị hấp thụ. Lời khuyên chuẩn bị được sinh bằng luật tường minh trên dự báo. Mọi thẻ mang theo nguồn gốc và thời điểm lấy dữ liệu, và một dịch vụ không gọi được sẽ cho ra trạng thái không-có-dữ-liệu tường minh thay vì một giá trị bịa.

### 12.5. Ví dụ tình huống người dùng

Cả hai tình huống có chủ đích dùng điểm vào không phải một di tích, vì tiền đề của nền tảng là điểm vào có thể là bất kỳ loại đối tượng văn hóa nào: một cổ vật, một món ăn, một loại hình diễn xướng, một nghề thủ công, hay một lễ hội.

**Tình huống A — nghiên cứu một cổ vật.** Người dùng hỏi về một tác phẩm điêu khắc đá thời Champa. Lớp trả lời giải thích đối tượng từ kho ngữ liệu và trích dẫn nguyên văn một câu nguồn. Ý định được phân loại là nghiên cứu, nên lớp tư vấn bổ sung bảo tàng đang giữ đối tượng kèm phòng trưng bày, giờ mở cửa và giá vé, các cổ vật cùng thời kỳ khác trong cùng bộ sưu tập, và những làng nghề mà kỹ thuật còn lưu giữ có liên hệ với nó. Nếu bảo tàng đó có mô hình 3D đã số hóa, trang chi tiết mở được trình xem 3D kèm audio narration về đối tượng. Lớp cá nhân hóa, đã ghi nhận sự quan tâm tới điêu khắc và văn hóa vật chất Chăm, gợi ý xuyên danh mục — một di tích liên quan, một làng nghề, và một loại hình diễn xướng được nối qua đồ thị — mỗi mục hiển thị kèm đường đi biện minh cho nó. Không có gì trong khối thực tế là do sinh ra: bảo tàng, niên đại, chất liệu và phòng trưng bày đều là trường bản ghi có nguồn riêng.

**Tình huống B — đi dự một lễ hội.** Người dùng hỏi về một lễ hội của làng chài. Lớp trả lời giải thích ý nghĩa và cấu trúc nghi lễ kèm trích nguồn. Ý định được phân loại là dự sự kiện, nên lớp tư vấn trả về loại lịch và ngày của năm nay, địa điểm kèm tọa độ và bản đồ, các phần lễ và phần hội, dự báo cho ngày đó kèm danh mục chuẩn bị suy ra bằng luật từ xác suất mưa, một điểm quan sát được đề xuất, và chỗ gửi xe gần nhất. Lớp cá nhân hóa gợi ý văn hóa liên quan: món ăn địa phương gắn với làng, một di tích gần đó, và loại hình diễn xướng dân gian được trình diễn trong phần hội. Nếu dịch vụ thời tiết không gọi được, thẻ ghi rằng dự báo không có thay vì đoán.

**Tình huống C — một giả định sai.** Người dùng hỏi *"Cao lầu là đặc sản Huế đúng không?"*. Truy hồi neo vào món ăn đó, cổng bằng chứng xác nhận đoạn đã truy hồi nói về đúng món đó thay vì một món tương tự, và câu trả lời sinh ra mở đầu bằng việc đính chính giả định trước khi kể tiếp — vì mô hình đã được tinh chỉnh trên việc đính chính giả định sai thay vì bị để mặc mà đồng ý một cách lịch sự.

## 13. Tổng quan mô hình dữ liệu

Nền tảng lưu ba loại dữ liệu với yêu cầu toàn vẹn khác nhau.

**Kho ngữ liệu và đồ thị tri thức.** Tài liệu mang theo vùng, danh mục, tên gọi khác và các đoạn kèm định vị nguồn. Đỉnh đồ thị là tài liệu, thực thể, đơn vị hành chính, vùng, danh mục và năm. Quan hệ mang tính cấu trúc và mang bằng chứng: tài liệu–thực thể nhắc đến, tài liệu–đơn vị hành chính, tài liệu–vùng, tài liệu–danh mục, tài liệu–năm, tài liệu–tài liệu đồng xuất hiện, và tài liệu–thực thể chính danh. Không quan hệ ngữ nghĩa nào được suy ra, nên đồ thị không bao giờ khẳng định một dữ kiện mà nguồn không nói.

**Bản ghi văn hóa có cấu trúc.** Địa điểm mang tọa độ, phường và quận. Sự kiện mang loại lịch, ngày bắt đầu và kết thúc, đơn vị tổ chức và tham chiếu địa điểm, và phân rã thành các phần lễ và hội có thứ tự. Cổ vật mang niên đại, chất liệu, bảo tàng đang giữ và phòng trưng bày. Điểm quan tâm mang loại, tọa độ, nguồn và thời điểm lấy dữ liệu. Tài sản đa phương tiện mang loại (mô hình 3D hoặc audio), khóa đối tượng trong kho, tham chiếu story, ngôn ngữ với audio, transcript, giấy phép, người đóng góp, URL nguồn gốc và ngày tải lên. Mọi trường sự kiện của mọi bản ghi trong nhóm này mang theo URL nguồn và câu nguồn đã đọc ra nó, được bảo đảm bằng ràng buộc cơ sở dữ liệu thay vì bằng thói quen ở tầng ứng dụng.

**Dữ liệu người dùng và tương tác.** Tài khoản mang thông tin đăng nhập và mốc thời gian đồng ý. Mục sở thích mang tham chiếu đỉnh, trọng số, loại tương tác đã sinh ra nó, và lần cập nhật cuối, để hồ sơ có thể hiển thị lại cho người dùng kèm lý do của chính nó. Sự kiện tương tác mang loại, đỉnh đích, thời gian dừng và mốc thời gian. Log gợi ý mang hạt giống, mục được gợi ý, đường đi giải thích, hạng, thời điểm hiển thị và thời điểm nhấp — đây là thứ làm cho việc đánh giá chất lượng gợi ý ngoại tuyến trở nên khả thi. Sổ kiểm toán ghi mọi thay đổi của biên tập viên kèm giá trị trước và sau.
