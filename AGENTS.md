# AGENTS.md

## 1. Tổng quan dự án & Kiến trúc

**HeritageGraph** là nền tảng khám phá di sản văn hóa, tích hợp GraphRAG, chatbot AI và trải nghiệm tham quan 3D tương tác.

Project là monorepo gồm 2 applications độc lập (riêng biệt dependencies, build, tests, configs):

* `apps/frontend/`: Frontend application (Next.js).
* `apps/backend/`: Backend application (FastAPI).

**Nguyên tắc:** Không tạo coupling trực tiếp giữa Frontend và Backend. Hai ứng dụng chỉ giao tiếp thông qua REST API. Task thuộc phạm vi nào chỉ thao tác trong thư mục tương ứng, trừ khi yêu cầu liên quan đến cả hai.

```text
/
├── AGENTS.md
├── apps/
│   ├── frontend/           # Next.js App Router, React, TypeScript, Three.js
│   └── backend/            # FastAPI, GraphRAG, LLM, Database
└── docker-compose.yml
```

## 2. Frontend Conventions (`apps/frontend/`)

* **Tech Stack:** Next.js 14 (App Router), React, TypeScript, CSS Modules, Three.js, React Three Fiber.
* **Server Components mặc định:** Chỉ dùng `'use client'` khi cần React state, event listeners, hooks hoặc browser APIs.
* **TypeScript:** Ưu tiên strict typing, không sử dụng `any` khi có thể xác định kiểu dữ liệu.
* **Cấu trúc & Colocation:**
  * Tuân thủ cấu trúc thư mục và path alias hiện có.
  * Đặt components, hooks, services và types theo convention của dự án.
  * Ưu tiên tái sử dụng components trước khi tạo mới.
  * Không thêm thư viện State Management nếu React State hoặc URL State đã đáp ứng đủ.
* **Three.js & 3D:**

  * Sử dụng React Three Fiber để tích hợp Three.js với React.
  * Tránh khởi tạo lại renderer, geometry, material và texture không cần thiết.
  * Cleanup resources, event listeners và animation frames khi component unmount.
  * Không tự ý thay đổi camera controls, scene interactions hoặc logic tải mô hình 3D.
* **Styling:** Sử dụng CSS Modules, đảm bảo responsive và tuân thủ thiết kế hiện tại và hãy viết cách truy cập module CSS là kiểu alias.

## 3. Backend Conventions (`apps/backend/`)

* **Tech Stack:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL 16, pgvector, llama.cpp, Qwen2.5, BGE-M3.
* **Architecture:** Hexagonal Architecture (Ports & Adapters).
* **API Boundary & DTO:**

  * Sử dụng Pydantic models cho Request và Response.
  * Không expose trực tiếp ORM entities qua API.
  * Sử dụng HTTP status chuẩn (200, 201, 204, 400, 404, 500).
  * Xử lý exceptions tập trung và nhất quán.
* **Layers & Dependency Injection:**

  * API Router chỉ xử lý HTTP requests/responses.
  * Business logic đặt tại Application/Service layer.
  * Domain không phụ thuộc trực tiếp vào FastAPI, SQLAlchemy hoặc infrastructure.
  * Infrastructure triển khai các interfaces/ports theo kiến trúc hiện tại.
  * Sử dụng FastAPI Dependency Injection theo convention dự án.
* **AI & GraphRAG:**

  * Retrieval hiện tại: BM25 Word + Character N-gram → RRF → Graph Reranking (optional) → BGE-M3 → pgvector → Evidence Filtering → LLM.
  * LLM inference sử dụng llama.cpp với mô hình Qwen2.5 Fine-tuned.
  * Câu trả lời phải có citation hợp lệ theo Answer Gate.
  * Không tạo thông tin lịch sử không có căn cứ.
  * Không tự ý thay đổi retrieval strategy, embedding model hoặc inference backend.
  * Ưu tiên tối ưu latency, memory và token usage nhưng không đánh đổi tính chính xác khi chưa được phê duyệt.

## 4. API Contract, Database & Security

* **Quy trình đổi API:** Thống nhất contract → Cập nhật Backend + OpenAPI docs → Cập nhật Frontend (types, services) + tests. Đảm bảo backward compatibility.
* **Database:**

  * PostgreSQL 16 là database chính và nguồn dữ liệu chuẩn (source of truth).
  * pgvector phục vụ semantic/vector search.
  * SQLAlchemy quản lý database access.
  * Alembic quản lý database migrations.
  * Không tự ý chỉnh sửa schema hoặc dữ liệu production.
  * Không sử dụng `create_all()` để thay thế migrations trong staging/production.
* **Object Storage:** Cloudflare R2 lưu trữ các tài nguyên media và mô hình 3D.
* **Infrastructure:** Docker Compose, AWS, Jenkins, Terraform, OpenTelemetry và Prometheus.
* **Security:** Tuyệt đối không commit secrets, API keys, credentials hoặc private keys. Sử dụng `.env` và environment variables. Không tự ý thay đổi production configurations.

## 5. Commands & Quy tắc an toàn (Command Safety)

### Lệnh thực thi

* **Frontend** (`apps/frontend/`): `npm run dev` | `npm run build` | `npm run lint` | `npm run test` (nếu script tồn tại).
* **Backend** (`apps/backend/`): Sử dụng lệnh FastAPI/Uvicorn, pytest và các công cụ quản lý dependencies theo cấu hình thực tế của dự án.
* **Docker:** `docker compose up -d` | `docker compose ps` | `docker compose logs`.
* **Database Migration:** `alembic upgrade head` (chỉ khi được phê duyệt).

### An toàn thực thi (BẮT BUỘC)

* **KHÔNG TỰ Ý CHẠY TEST/BUILD NẶNG:** Khi đang ở bước đọc hiểu, phân tích, lập kế hoạch hoặc trả lời câu hỏi, Agent **tuyệt đối không chạy** full test suite, full build hoặc các lệnh tốn tài nguyên.

* **Chỉ chạy test/build khi:**

  1. Đang ở bước `Test` của task code thực tế đã được phê duyệt và có sửa đổi source code liên quan.
  2. Người dùng yêu cầu chạy lệnh cụ thể.

* **Quy tắc bổ sung:**

  * Ưu tiên targeted tests thay vì full test suite.
  * Không tự ý cài đặt hoặc nâng cấp dependencies.
  * Không tự ý chạy database migrations.
  * Không tự ý khởi động toàn bộ Docker services.
  * Không tự ý deploy hoặc thay đổi infrastructure.
  * Không thực hiện destructive commands như `git reset --hard`, `git clean -fd`, `docker compose down -v`, `DROP TABLE` hoặc `terraform destroy` khi chưa được phê duyệt.

## 6. Agentic Workflow & Nguyên tắc thực thi

### Quy trình 6 bước

```text
Understand ──> Analyze ──> Plan ──> Implement ──> Test ──> Review
```

1. **Understand:** Nắm rõ yêu cầu, mục tiêu và phạm vi task. Không tự suy diễn requirements.
2. **Analyze:** Kiểm tra source code, kiến trúc, dependencies và các thành phần liên quan. Ưu tiên giải pháp có sẵn.
3. **Plan:** Lập kế hoạch rõ ràng (danh sách file, giải pháp, phạm vi ảnh hưởng, rủi ro). **BẮT BUỘC user phê duyệt trước khi viết code.**
4. **Implement:** Chỉ sửa đúng phạm vi đã duyệt. Không tự ý thêm tính năng, dependencies hoặc refactor ngoài lề. Nếu cần thay đổi ngoài kế hoạch, phải xin phê duyệt bổ sung.
5. **Test:** Chạy automated tests liên quan trực tiếp đến thay đổi. Tự sửa lỗi do thay đổi hiện tại gây ra. Không sửa test chỉ để làm test pass.
6. **Review:** Tự rà soát tính chính xác, bảo mật, clean code và Git diff. Không để lại debug code hoặc file rác. Cập nhật tài liệu nếu thay đổi API contract.

### Thứ tự ưu tiên cốt lõi

`Correctness & Security > User Requirements > Existing Conventions > KISS/YAGNI > Small Focused Change > New Abstraction > New Dependency`

* Không tự bịa requirements hoặc giả định code/API tồn tại khi chưa kiểm tra.
* Không tối ưu hóa sớm cho các kịch bản tương lai xa.
* Không thay đổi kiến trúc hiện tại nếu chưa được yêu cầu.
* Không tạo abstraction không cần thiết.
* Không sửa file ngoài phạm vi task.
* Không tự ý thay đổi API contract, database schema hoặc AI pipeline.
* Không tuyên bố test/build thành công nếu chưa thực sự chạy.
* Khi hoàn thành, báo cáo ngắn gọn các file đã thay đổi, kết quả kiểm thử và vấn đề còn tồn tại.
