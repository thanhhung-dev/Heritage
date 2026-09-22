# HeritageGraph — Giải thích công nghệ trong kiến trúc

> Tài liệu này dùng để thuyết trình theo sơ đồ `kientruc-recsys-agent-platform.excalidraw`. Trọng tâm là: **dùng công nghệ gì, công nghệ đó giải quyết vấn đề nào và vì sao phù hợp với đồ án**.

## 1. Cách bắt đầu bài thuyết trình

Không bắt đầu từ người dùng. Bắt đầu ở góc **kiểm thử, đánh giá và Jenkins CI**, sau đó đi sang dữ liệu, lõi AI, ứng dụng và hạ tầng triển khai.

Thứ tự chỉ trên sơ đồ:

```text
GitHub → Jenkins CI → kiểm thử và đánh giá
       → dữ liệu, chỉ mục và knowledge graph
       → frontend và backend API
       → RAG, Qwen và Recommendation Service
       → lưu trữ media, DEV/PROD và observability
```

**Lời mở đầu gợi ý:**

> “HeritageGraph là nền tảng hỏi đáp và khám phá di sản Đà Nẵng – Huế. Em xin bắt đầu từ vòng kiểm soát chất lượng, vì với một hệ thống AI, trước khi nói model trả lời như thế nào thì cần chứng minh dữ liệu, retrieval và câu trả lời được kiểm thử ra sao. Sau đó em sẽ giải thích từng công nghệ được chọn và lý do lựa chọn.”

## 2. Bảng tóm tắt công nghệ

| Nhóm | Công nghệ | Vai trò chính |
|---|---|---|
| Source và CI | GitHub, Jenkins | Quản lý source và tự động chạy pipeline kiểm tra |
| Đánh giá | Python scripts, manual gold set | Đo retrieval, citation, refusal và chất lượng model |
| Dữ liệu | Corpus tự biên soạn, Python | Tạo corpus được tuyển chọn và pipeline deterministic |
| Retrieval | BM25 word, character n-gram, RRF | Tìm bằng chứng kể cả khi câu hỏi không dấu hoặc sai nhẹ |
| Knowledge graph | NetworkX | Biểu diễn quan hệ, mở rộng và rerank tài liệu |
| Dữ liệu ứng dụng | PostgreSQL, pgvector | Lưu profile, interaction và có đường mở rộng semantic search |
| Frontend | Next.js, React, TypeScript, Three.js | Giao diện web, chat và trải nghiệm 3D |
| Frontend hosting | Vercel | Preview và production deployment cho Next.js |
| Backend | FastAPI, Uvicorn, Pydantic | API, validation và điều phối pipeline AI |
| LLM | Qwen2.5-3B-Instruct, LoRA | Diễn đạt câu trả lời, citation và refusal |
| Inference | MLX, llama.cpp, GGUF | Chạy model trên Mac, Docker và GPU NVIDIA |
| Đóng gói | Docker, Docker Compose | Đồng nhất môi trường DEV và PROD |
| DEV network | Cloudflare Tunnel | Cấp HTTPS công khai cho backend trên máy cá nhân |
| PROD compute | AWS EC2 g4dn.xlarge | Chạy backend và model trên GPU theo giờ |
| Media | Cloudflare R2, Amazon S3 | Lưu file 3D và audio đã tạo sẵn |
| Kiểm thử tải | k6 | Đo latency, throughput và lỗi API trong Jenkins |
| Quan sát | Prometheus, Grafana, Loki, Langfuse | Theo dõi metrics, logs và trace luồng LLM |

## 3. GitHub, Jenkins và lớp kiểm soát chất lượng

### 3.1. GitHub

**GitHub là gì?** Nền tảng quản lý source code bằng Git và lưu lịch sử thay đổi.

**Vai trò trong kiến trúc:** GitHub là điểm bắt đầu của pipeline. Khi code thay đổi, Jenkins lấy đúng phiên bản source để kiểm tra.

**Vì sao chọn:** phổ biến, dễ trình bày lịch sử phát triển, phối hợp tốt với Vercel và Jenkins, phù hợp đồ án cá nhân.

### 3.2. Jenkins CI

**Jenkins là gì?** Công cụ CI/CD mã nguồn mở, tự động chạy các bước build và test theo pipeline.

**Jenkins dự kiến kiểm tra:**

- Retrieval evaluation.
- Backend regression tests.
- k6 load test cho các API quan trọng.
- Next.js production build.
- Backend Docker image build.
- Kiểm tra package model GGUF.
- Docker Compose smoke test.

**Vì sao chọn:** Jenkins thể hiện rõ quy trình CI, tự host được trên máy cá nhân và có thể chạy theo phiên nên không cần thuê thêm máy AWS 24/7.

**Điểm phải nói trung thực:** kiến trúc đã thiết kế pipeline Jenkins nhưng repository hiện chưa có `Jenkinsfile`; đây là hạng mục triển khai tiếp theo, không nên nói Jenkins đang chạy thật.

### 3.3. Python evaluation scripts và manual gold set

**Gold set là gì?** Bộ câu hỏi có đáp án, nguồn và hành vi mong đợi do con người kiểm tra trước.

**Vì sao cần:** test phần mềm chỉ cho biết API có chạy; gold set mới giúp biết hệ thống có lấy đúng bằng chứng, trích đúng nguồn và từ chối đúng lúc hay không.

Đánh giá được chia thành:

- **Retrieval quality:** tài liệu và chunk đúng có nằm trong kết quả đầu không.
- **Answer quality:** câu trả lời có đúng với gold answer không.
- **Citation:** nguồn trích dẫn có thực sự hỗ trợ câu trả lời không.
- **Refusal:** khi corpus thiếu dữ kiện, model có từ chối thay vì bịa không.
- **Recommendation:** gợi ý có liên quan, đa dạng và không lặp lại quá nhiều không.

**Lý do dùng Python scripts:** phần xử lý dữ liệu, retrieval và model đều ở Python, vì vậy script đánh giá có thể tái sử dụng trực tiếp module của hệ thống.

## 4. Corpus tự biên soạn và pipeline dữ liệu Python

### 4.1. Corpus di sản do tác giả biên soạn và tuyển chọn

**Vai trò:** cung cấp dữ liệu nền về di sản, địa điểm, lễ hội, ẩm thực và nghệ thuật Huế – Đà Nẵng.

**Vì sao chọn:** tác giả chủ động xác định phạm vi, cách diễn đạt, metadata và cấu trúc dữ liệu phù hợp với câu hỏi của đề tài. Corpus được tuyển chọn trước cũng giúp tránh thu thập Internet không kiểm soát.

**Yêu cầu chất lượng:** tự biên soạn không có nghĩa là tự suy đoán. Mỗi nội dung vẫn cần được đối chiếu với nguồn đáng tin cậy, lưu provenance và được rà soát trước khi đưa vào corpus.

### 4.2. Python deterministic indexing

**Deterministic nghĩa là gì?** Cùng dữ liệu và cấu hình sẽ sinh cùng chunk, chỉ mục và graph; không gọi LLM để đoán node hoặc edge trong giai đoạn indexing.

**Vì sao chọn:**

- Kết quả tái lập được để so sánh giữa các lần đánh giá.
- Tránh LLM tạo quan hệ không tồn tại.
- Dễ truy vết một chunk về tài liệu và URL gốc.
- Phù hợp corpus nhỏ của đồ án.

## 5. BM25 word, character n-gram và RRF

### 5.1. BM25 word

**BM25 là gì?** Thuật toán xếp hạng tài liệu theo mức độ khớp từ khóa, có tính đến tần suất từ và độ dài tài liệu.

**Vai trò:** tìm nhanh các đoạn chứa tên địa điểm hoặc khái niệm đúng với câu hỏi.

**Vì sao chọn:** nhanh, nhẹ, dễ giải thích và không cần gọi embedding API hay vận hành vector database.

### 5.2. Character n-gram

**Là gì?** Chia văn bản thành các cụm ký tự ngắn để so khớp ở cấp ký tự thay vì chỉ cấp từ.

**Vai trò:** hỗ trợ tiếng Việt không dấu, sai chính tả nhẹ hoặc khác cách viết. Ví dụ `lang minh mang` vẫn có cơ hội tìm được `Lăng Minh Mạng`.

**Vì sao không chỉ dùng BM25 word:** tokenizer theo từ có thể bỏ lỡ câu viết không dấu hoặc lỗi gõ; char n-gram bù cho điểm yếu này.

### 5.3. Reciprocal Rank Fusion — RRF

**RRF là gì?** Phương pháp hợp nhất nhiều danh sách kết quả dựa trên thứ hạng.

**Vai trò:** kết hợp kết quả BM25 word và char n-gram.

**Vì sao chọn:** điểm của hai retriever có thang đo khác nhau; RRF dùng vị trí xếp hạng nên không cần chuẩn hóa điểm thủ công và ít tham số phải tinh chỉnh.

## 6. NetworkX và lý do chưa chọn Neo4j

### 6.1. NetworkX

**NetworkX là gì?** Thư viện Python để tạo, duyệt và phân tích graph trong bộ nhớ.

**NetworkX làm gì trong HeritageGraph?**

- Lưu quan hệ giữa document, entity, region, category và year.
- Neo câu hỏi vào thực thể có thật trong corpus.
- Đi qua các quan hệ để tìm tài liệu liên quan.
- Rerank kết quả lexical retrieval.
- Cung cấp đường dẫn giải thích cho retrieval và recommendation.

**NetworkX không làm gì?** Nó không phải database, không phải vector store và không tự sinh câu trả lời. Qwen mới là thành phần diễn đạt câu trả lời.

**Vì sao chọn:** graph hiện nhỏ, dựng được từ corpus khi process khởi động, thuật toán nằm cùng backend Python và không cần vận hành thêm server.

### 6.2. So sánh NetworkX với Neo4j

| Tiêu chí | NetworkX | Neo4j |
|---|---|---|
| Loại công nghệ | Thư viện graph Python | Graph database độc lập |
| Lưu trữ chính | RAM/file export | Lưu bền trên database |
| Truy vấn | Hàm Python | Cypher |
| Vận hành | Rất đơn giản | Cần server, backup và cấu hình |
| Phù hợp hiện tại | Có | Chưa cần |

**Khi nào nên chuyển sang Neo4j:** graph lớn, cập nhật liên tục, nhiều service cùng truy cập hoặc cần các truy vấn Cypher phức tạp. Hiện tại Neo4j làm tăng vận hành nhưng chưa tạo lợi ích tương xứng.

## 7. PostgreSQL, pgvector và lý do chưa chọn Milvus

### 7.1. PostgreSQL

**PostgreSQL là gì?** Cơ sở dữ liệu quan hệ mã nguồn mở.

**Vai trò dự kiến:** lưu tài khoản, hồ sơ sở thích, lượt xem, lượt bấm, lượt lưu và lịch sử tương tác cho Recommendation Service.

**Vì sao chọn:** dữ liệu người dùng và interaction có cấu trúc rõ, cần transaction và ràng buộc dữ liệu; PostgreSQL phù hợp hơn NetworkX cho nhiệm vụ lưu trữ này.

### 7.2. pgvector

**pgvector là gì?** Extension cho PostgreSQL để lưu vector embedding và tìm kiếm theo độ tương đồng.

**Vì sao phù hợp để mở rộng:** nếu benchmark sau này chứng minh BM25 chưa đủ semantic recall, dự án có thể thêm vector search ngay trong PostgreSQL thay vì triển khai một database mới.

### 7.3. Vì sao chưa dùng Milvus

**Milvus là gì?** Vector database chuyên dụng cho lượng embedding lớn và truy vấn similarity ở quy mô cao.

**Kết luận:** Milvus tốt nhưng chưa phù hợp với corpus nhỏ và ngân sách đồ án. Nó thêm một service phải triển khai, giám sát và backup. PostgreSQL + pgvector đơn giản hơn và đủ cho giai đoạn hiện tại.

**Trạng thái:** PostgreSQL, pgvector, profile và interaction store là kiến trúc mục tiêu, chưa phải runtime đang hoạt động trong source hiện tại.

## 8. Next.js, React, TypeScript, Three.js và Vercel

### 8.1. Next.js, React và TypeScript

**Vai trò:** xây giao diện chat, hiển thị nguồn, nội dung di sản và recommendation.

**Vì sao chọn:**

- React phù hợp giao diện có nhiều state và component tương tác.
- Next.js cung cấp cấu trúc ứng dụng, routing và production build rõ ràng.
- TypeScript phát hiện lỗi dữ liệu giữa frontend và API sớm hơn JavaScript thuần.

### 8.2. Three.js

**Three.js là gì?** Thư viện JavaScript hiển thị đồ họa 3D bằng WebGL trong trình duyệt.

**Vai trò dự kiến:** hiển thị mô hình di sản `.glb` để tăng trải nghiệm khám phá.

**Vì sao chọn:** chạy trực tiếp trên web, phù hợp hệ sinh thái React và không yêu cầu người dùng cài ứng dụng 3D riêng.

### 8.3. Vercel

**Vai trò:** deploy Next.js với hai môi trường:

- **Preview:** kiểm tra từng phiên bản DEV.
- **Production:** domain frontend chính thức.

**Vì sao chọn:** tích hợp tự nhiên với Next.js và GitHub, có HTTPS/CDN sẵn và giảm phần hạ tầng frontend phải tự quản lý.

## 9. Cloudflare Tunnel cho môi trường DEV

**Cloudflare Tunnel là gì?** Kết nối outbound từ máy cá nhân tới Cloudflare để công khai backend qua HTTPS mà không mở port router trực tiếp.

**Vai trò:**

```text
Vercel Preview → HTTPS → Cloudflare Tunnel
                            ↓
                 máy cá nhân: FastAPI + model
```

**Vì sao chọn:** chi phí gần 0, không cần public IP cố định và an toàn hơn việc mở port thẳng vào mạng gia đình.

**Giới hạn quan trọng:** Tunnel không phải server. Máy cá nhân phải bật, có Internet, `cloudflared`, Docker, FastAPI và model phải đang chạy. Người khác đăng nhập Cloudflare không thể làm một máy đang tắt tự chạy lại; muốn vậy cần Wake-on-LAN, remote access hoặc người tại nhà bật máy.

Vì vậy đây là **môi trường DEV công khai tạm thời**, không phải production có độ sẵn sàng cao.

## 10. FastAPI, Uvicorn và Pydantic

### FastAPI

**Là gì?** Web framework Python để xây API.

**Vai trò:** nhận câu hỏi, gọi retriever, kiểm tra evidence, gọi model và trả câu trả lời cùng nguồn. Graph API và Recommendation API cũng thuộc boundary này.

**Vì sao chọn:** phần AI đã viết bằng Python; FastAPI có async support, OpenAPI tự động và mô hình code gọn cho API.

### Uvicorn

**Là gì?** ASGI server chạy ứng dụng FastAPI.

**Vì sao cần:** FastAPI định nghĩa ứng dụng, còn Uvicorn là process nhận kết nối HTTP và thực thi ứng dụng.

### Pydantic

**Là gì?** Thư viện khai báo và kiểm tra schema dữ liệu Python.

**Vai trò:** validate request/response, ngăn dữ liệu sai cấu trúc đi sâu vào pipeline AI.

## 11. Qwen2.5-3B-Instruct và LoRA

### 11.1. Qwen2.5-3B-Instruct

**Là gì?** Mô hình ngôn ngữ instruction-tuned khoảng 3 tỷ tham số.

**Vai trò:** nhận context đã được retrieval kiểm chứng và diễn đạt thành câu trả lời tiếng Việt tự nhiên.

**Vì sao chọn:** kích thước đủ nhỏ để chạy local/quantize nhưng vẫn có khả năng làm theo hướng dẫn và sinh tiếng Việt. Đây là cân bằng phù hợp giữa chất lượng, VRAM và ngân sách.

### 11.2. LoRA

**LoRA là gì?** Kỹ thuật fine-tune chỉ huấn luyện một số ma trận thích nghi nhỏ thay vì cập nhật toàn bộ model.

**Vai trò trong dự án:** điều chỉnh hành vi như văn phong, định dạng citation, đính chính giả định sai và từ chối khi thiếu nguồn.

**Vì sao chọn:** cần ít VRAM và tạo adapter nhỏ, dễ quản lý hơn full fine-tuning.

**Điểm phải nói chính xác:** LoRA không phải nơi lưu toàn bộ kiến thức di sản. Sự kiện thực tế được lấy từ corpus ở runtime; LoRA chủ yếu dạy model cách sử dụng bằng chứng.

## 12. MLX, llama.cpp và GGUF

### MLX

**Là gì?** Framework machine learning tối ưu cho Apple Silicon.

**Vai trò:** chạy và thử model thuận tiện trên máy Mac trong giai đoạn phát triển.

### llama.cpp

**Là gì?** Runtime inference C/C++ tối ưu để chạy model lượng tử hóa trên nhiều loại phần cứng.

**Vai trò:** chạy Qwen trong Docker và trên EC2 GPU NVIDIA mà không phụ thuộc môi trường Apple.

### GGUF

**Là gì?** Định dạng model phổ biến trong hệ llama.cpp, chứa weights và metadata phục vụ inference.

**Vì sao kết hợp ba công nghệ:** MLX tối ưu trải nghiệm local trên Mac; llama.cpp + GGUF tạo artifact gọn và portable cho Docker/AWS. Backend chọn runtime qua biến cấu hình thay vì thay business logic.

## 13. Recommendation Service

Recommendation Service là một capability riêng trong FastAPI, không phải chức năng tự động có sẵn của NetworkX.

```text
nội dung đang xem + interest profile + interactions
                         ↓
          NetworkX graph affinity
                         ↓
        seen penalty + diversification
                         ↓
           danh sách gợi ý có lý do
```

**Công nghệ và lý do:**

- **NetworkX:** đo quan hệ giữa nội dung hiện tại và ứng viên.
- **PostgreSQL:** lưu profile và hành vi người dùng.
- **FastAPI `/api/recommend`:** cung cấp một contract rõ cho frontend.
- **Thuật toán diversification:** tránh chỉ gợi ý nhiều nội dung quá giống nhau.
- **Graph-only fallback:** người dùng ẩn danh vẫn nhận gợi ý dựa trên nội dung đang xem.

**Khác retrieval:** retrieval chọn bằng chứng để trả lời một câu hỏi; recommendation chọn nội dung nên khám phá tiếp.

**Trạng thái:** NetworkX và graph traversal đã có; endpoint recommendation, personalization và PostgreSQL chưa hoàn thiện trong source.

## 14. Docker và Docker Compose

**Docker là gì?** Đóng gói ứng dụng, dependency và cấu hình runtime thành image/container.

**Docker Compose là gì?** Khai báo và chạy nhiều container cùng nhau.

**Vai trò trong dự án:** điều phối frontend, FastAPI và llama.cpp server.

**Vì sao chọn:**

- Giảm khác biệt “chạy được trên máy em nhưng không chạy trên server”.
- Dùng cùng cách đóng gói cho DEV và PROD.
- Đủ đơn giản cho số lượng service hiện tại.
- Dễ smoke test trong CI.

## 15. AWS EC2 g4dn.xlarge cho PROD

**EC2 là gì?** Dịch vụ máy ảo theo giờ của AWS.

**Vì sao chọn `g4dn.xlarge`:** có GPU NVIDIA T4, phù hợp chạy model Qwen đã quantize bằng llama.cpp và không yêu cầu xây cụm Kubernetes.

**Cách tận dụng khoản credit 100 USD:**

- Phát triển và test thường ngày trên máy cá nhân.
- Jenkins chạy local hoặc theo phiên.
- Chỉ bật EC2 khi rehearsal, kiểm tra tích hợp cuối và ngày bảo vệ.
- Tắt instance ngay khi không dùng; vẫn theo dõi phí EBS, public IPv4 và lưu trữ.
- Giữ một phần credit làm buffer thay vì dùng hết cho compute.

Với mức giá tham chiếu khoảng 0,526 USD/giờ, không nên hiểu 100 USD là gần 190 giờ an toàn tuyệt đối vì còn chi phí phụ. Kế hoạch hợp lý là giới hạn compute và kiểm tra AWS Billing thường xuyên.

**Kiến trúc PROD:**

```text
Vercel Production → HTTPS → EC2 g4dn.xlarge
                              ↓
                    Docker Compose
                              ↓
                  FastAPI + llama.cpp
```

## 16. Cloudflare R2 và Amazon S3

### Cloudflare R2

**Là gì?** Object storage tương thích S3 API, nổi bật ở chính sách không tính egress ra Internet theo mô hình thông thường của R2.

**Vai trò:** lưu và phân phối file mô hình 3D `.glb`, loại file có thể lớn và được tải trực tiếp ở frontend.

### Amazon S3

**Là gì?** Object storage của AWS.

**Vai trò:** lưu audio đã tạo trước bằng công cụ Text-to-AI bên ngoài và đã kiểm tra nội dung.

**Vì sao không sinh audio realtime:** giảm thời gian chờ, tránh phí TTS cho mỗi request và cho phép kiểm duyệt transcript trước khi công bố.

**Vì sao dùng cả R2 và S3:** đây là cách phân vai trong sơ đồ: R2 tối ưu phân phối asset 3D ra web, còn S3 đặt audio gần hệ sinh thái AWS. Với đồ án nhỏ, hoàn toàn có thể hợp nhất về một object store nếu muốn giảm vận hành; đây không phải ràng buộc kỹ thuật bắt buộc.

## 17. Analytics và observability

### Prometheus và Grafana

**Prometheus** thu thập metrics như latency, throughput, error rate và trạng thái FastAPI/model. **Grafana** đọc dữ liệu đó để hiển thị dashboard phục vụ theo dõi và thuyết trình.

### Loki và application logging

FastAPI và llama.cpp ghi structured logs; **Loki** tập trung các log này để có thể tìm kiếm và xem cùng dashboard Grafana. Loki không thay thế code logging mà là nơi thu thập và truy vấn log.

### Langfuse

**Langfuse là gì?** Nền tảng observability cho ứng dụng LLM, theo dõi prompt, context, generation, latency, token và feedback theo từng trace.

**Vì sao hữu ích:** khi câu trả lời sai, có thể phân biệt lỗi do câu hỏi đầu vào, retrieval, context hay model generation thay vì chỉ nhìn một exception log.

**Langfuse không thay thế Prometheus hoặc Loki:** Prometheus theo dõi metrics, Loki theo dõi logs, còn Langfuse tập trung vào vòng đời request AI.

**Vị trí của k6:** k6 là công cụ load test và chạy trong Jenkins CI, không phải service observability hoạt động thường trực.

**Trạng thái:** Prometheus, Grafana, Loki và Langfuse nằm trong kiến trúc mục tiêu, chưa được tích hợp runtime hiện tại. Chỉ nên bật stack này khi test, rehearsal hoặc bảo vệ để tiết kiệm tài nguyên.

## 18. Những công nghệ chưa chọn

| Công nghệ | Nó giải quyết gì? | Vì sao chưa phù hợp hiện tại? |
|---|---|---|
| Neo4j | Graph database lưu bền, Cypher | Graph nhỏ, deterministic và chỉ một backend sử dụng; NetworkX đơn giản hơn |
| Milvus | Vector search quy mô lớn | Corpus nhỏ; thêm service và chi phí vận hành chưa cần thiết |
| Istio | Service mesh cho Kubernetes | Hệ thống chưa có cụm Kubernetes và nhiều microservice cần traffic policy phức tạp |
| HashiCorp Vault | Quản lý secret tập trung | Quy mô hiện tại có thể dùng secret của Vercel/GitHub/AWS; Vault tự host tạo thêm vận hành |
| EKS/Kubernetes | Orchestration và autoscaling container | Docker Compose đủ cho một backend/model server và rẻ hơn nhiều |
| AWS RDS | Managed relational database | Chỉ nên bật khi Recommendation Service thực sự cần database online; nếu bật sớm sẽ tiêu credit liên tục |
| NAT Gateway | Kết nối outbound cho private subnet | Có phí theo giờ và dữ liệu; quá nặng cho demo một instance |

**Kết luận:** không phải các công nghệ này kém. Chúng giải quyết bài toán quy mô lớn hơn bài toán hiện tại. Kiến trúc tốt là kiến trúc đủ dùng, đo được và vận hành được trong ngân sách.

## 19. Trạng thái thực tế so với kiến trúc mục tiêu

Sơ đồ mô tả cả phần đang có và hướng hoàn thiện. Dù sơ đồ không gắn nhãn `CURRENT`, `PLANNED` hay `DEFERRED`, khi thuyết trình vẫn phải nói rõ trạng thái.

| Đã có trong source | Kiến trúc mục tiêu/chưa hoàn thiện |
|---|---|
| Corpus loader và chunking | Jenkins pipeline thực thi |
| BM25 word + char n-gram + RRF | PostgreSQL/pgvector runtime |
| NetworkX deterministic graph | Profile và interaction store |
| Graph expansion và rerank | `/api/recommend` và personalization |
| Evidence/refusal gates | Three.js và trải nghiệm 3D hoàn chỉnh |
| FastAPI chat, health và graph API | Audio cloud hoàn chỉnh |
| Qwen + LoRA; MLX/llama.cpp backends | Langfuse runtime |
| Next.js chat | Hạ tầng Vercel/R2/S3/EC2 hoàn chỉnh |
| Docker Compose | Tự động promote DEV sang PROD |
| Retripipelines/evaluation/model evaluation scripts |  |

**Cách trả lời an toàn:**

> “Sơ đồ là kiến trúc hoàn chỉnh em hướng tới. Phần lõi RAG, NetworkX, evidence gates, Qwen/LoRA, FastAPI, Next.js và Docker Compose đã có trong source. Recommendation, database người dùng, Jenkins, Langfuse, media và cloud deployment là các boundary đã thiết kế để triển khai tiếp. Em phân biệt rõ phần đã chạy và phần kiến trúc mục tiêu.”

## 20. Luồng tổng quát ngắn để tạo ngữ cảnh

Đây chỉ là phần nối các công nghệ, không cần trình bày sâu từng thuật toán:

```text
Developer push code lên GitHub
          ↓
Jenkins chạy build, test và evaluation
          ↓
Python tạo corpus, BM25 indexes và NetworkX graph
          ↓
User dùng Next.js trên Vercel
          ↓
FastAPI nhận câu hỏi và validate bằng Pydantic
          ↓
BM25 word + char n-gram + RRF tìm ứng viên
          ↓
NetworkX mở rộng/rerank + evidence gates kiểm tra nguồn
          ↓
llama.cpp/MLX chạy Qwen + LoRA với context đã kiểm chứng
          ↓
Frontend nhận câu trả lời, citation và recommendation
```

## 21. Kịch bản thuyết trình 7–10 phút

### Phút 0–1 — Mục tiêu và quality-first

> “HeritageGraph là nền tảng hỏi đáp và khám phá di sản Đà Nẵng – Huế. Em bắt đầu từ vòng quality phía dưới sơ đồ. Source nằm trên GitHub; trong kiến trúc đích, Jenkins tự động chạy test backend, build Next.js, kiểm tra Docker, GGUF và chạy evaluation. Gold set thủ công giúp đánh giá không chỉ API có chạy mà retrieval, citation và refusal có đúng hay không.”

### Phút 1–2 — Dữ liệu và retrieval

> “Dữ liệu bắt đầu từ corpus di sản do em tự biên soạn, tuyển chọn và đối chiếu nguồn. Pipeline Python deterministic làm sạch và chia chunk. Em dùng BM25 word vì nhanh, nhẹ và dễ giải thích; thêm character n-gram để xử lý tiếng Việt không dấu hoặc sai nhẹ; RRF hợp nhất hai bảng xếp hạng mà không phải chuẩn hóa điểm.”

### Phút 2–3 — Knowledge graph

> “NetworkX lưu quan hệ giữa tài liệu, thực thể, khu vực, thể loại và năm. Graph không sinh câu trả lời; nó giúp neo câu hỏi, mở rộng quan hệ và rerank bằng chứng. Em chưa dùng Neo4j vì corpus nhỏ, graph dựng được trong RAM và chỉ backend Python sử dụng. Neo4j chỉ cần khi graph lớn, cập nhật động hoặc nhiều service cùng truy vấn.”

### Phút 3–4 — Frontend và backend

> “Frontend dùng Next.js, React và TypeScript, deploy trên Vercel để có Preview và Production. Three.js là hướng hiển thị mô hình di sản 3D. Backend dùng FastAPI vì toàn bộ AI pipeline ở Python; Uvicorn chạy ASGI server và Pydantic kiểm tra schema request/response.”

### Phút 4–5 — Model và inference

> “Model là Qwen2.5-3B-Instruct, đủ nhỏ để chạy local nhưng vẫn có khả năng làm theo hướng dẫn tiếng Việt. LoRA điều chỉnh cách trích nguồn, từ chối và văn phong chứ không thay corpus làm nguồn sự thật. Local Mac dùng MLX; Docker và AWS dùng llama.cpp với GGUF để portable hơn.”

### Phút 5–6 — Recommendation và database

> “Recommendation Service tái sử dụng NetworkX để đo quan hệ nội dung, kết hợp profile và interaction trong PostgreSQL, rồi áp dụng seen penalty và diversification. Người dùng ẩn danh dùng graph-only fallback. pgvector là đường mở rộng nếu cần semantic search; em chưa chọn Milvus vì quy mô hiện tại không cần một vector database riêng.”

### Phút 6–7 — DEV, PROD và CI cost

> “DEV dùng Vercel Preview gọi Cloudflare Tunnel vào máy cá nhân. Tunnel giúp có HTTPS nhưng máy và service vẫn phải bật. PROD dùng Vercel Production và EC2 g4dn.xlarge có GPU T4. Em chỉ bật EC2 khi rehearsal và bảo vệ để tận dụng 100 USD credit, còn Jenkins chạy local hoặc theo phiên.”

### Phút 7–8 — Media và observability

> “File 3D được đặt trên Cloudflare R2, audio Text-to-AI được tạo trước, kiểm tra rồi lưu S3 để tránh TTS realtime. Python logging theo dõi ứng dụng; Langfuse là hướng bổ sung để trace prompt, context, latency và generation của LLM.”

### Kết luận

> “Mỗi công nghệ được chọn theo đúng quy mô đồ án: BM25 và NetworkX nhẹ nhưng giải thích được; Qwen, LoRA và llama.cpp cho phép tự chủ inference; Vercel, Cloudflare Tunnel và EC2 tách rõ DEV với PROD; Docker giữ môi trường nhất quán. Các công nghệ nặng như Neo4j, Milvus, Istio hay Kubernetes chỉ được thêm khi số liệu chứng minh là cần thiết.”

## 22. Câu hỏi giảng viên có thể hỏi

### Tại sao không đưa câu hỏi thẳng vào Qwen?

Vì model có thể trả lời bằng kiến thức không kiểm chứng hoặc bịa. Retrieval lấy bằng chứng trước, evidence gates quyết định có đủ nguồn không, rồi Qwen chỉ diễn đạt context đó.

### Tại sao chưa dùng semantic vector search?

BM25 word + char n-gram + graph đã nhẹ, đo được và phù hợp corpus nhỏ. Chỉ thêm pgvector khi evaluation chứng minh semantic recall là điểm yếu thực tế.

### NetworkX khác Neo4j ở điểm quan trọng nhất nào?

NetworkX là thư viện thuật toán graph chạy trong Python; Neo4j là database server có lưu bền và Cypher. Quy mô hiện tại cần thuật toán traversal/rerank hơn là một graph database độc lập.

### Recommendation có phải do LLM tạo không?

Không. Candidate và điểm gợi ý đến từ NetworkX, profile, interaction và diversification. LLM không cần quyết định nội dung nào được recommend, nên kết quả dễ giải thích hơn.

### LoRA có chứa toàn bộ kiến thức di sản không?

Không. LoRA chủ yếu điều chỉnh hành vi trả lời. Kiến thức được lấy từ corpus và citation ở runtime.

### Nếu máy DEV tắt thì Cloudflare Tunnel có chạy không?

Không. Tunnel chỉ chuyển traffic tới service đang hoạt động. Máy, Internet, `cloudflared`, backend và model đều phải chạy.

### Vì sao Jenkins không chạy thường trực trên AWS?

CI không cần GPU và không cần hoạt động 24/7 cho đồ án cá nhân. Chạy local hoặc on-demand tránh tiêu AWS credit mà vẫn chứng minh được pipeline.

### Vì sao không dùng Istio và Vault?

Istio hữu ích cho nhiều microservice trên Kubernetes; hệ hiện tại chỉ có vài container. Vault hữu ích khi có nhiều service/team và vòng đời secret phức tạp; hiện có thể dùng secret manager tích hợp của Vercel, GitHub và AWS.

### Cloudflare R2 và S3 có bị trùng vai trò không?

Cả hai đều là object storage. Sơ đồ phân R2 cho asset 3D tải nhiều và S3 cho audio trong hệ AWS. Nếu ưu tiên đơn giản hóa, dự án có thể chọn một trong hai mà không ảnh hưởng lõi RAG.

### Đây đã phải hệ production hoàn chỉnh chưa?

Chưa. Lõi phần mềm đã có, còn Jenkins, recommendation personalization, database, media, Langfuse và cloud provisioning là kiến trúc mục tiêu. Bản PROD cho ngày bảo vệ là một deployment có kiểm soát, chưa phải hệ thống thương mại HA.

## 23. Câu chốt một dòng

> **HeritageGraph chọn công nghệ nhẹ, có thể đo và giải thích: Jenkins kiểm soát chất lượng, BM25 cùng NetworkX tìm bằng chứng, Qwen + LoRA diễn đạt có nguồn, còn Docker, Vercel, Cloudflare và AWS giúp đưa cùng hệ thống từ DEV lên môi trường demo PROD trong ngân sách.**
