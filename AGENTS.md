# AGENTS.md

## 1. Project Overview & Architecture

Project là monorepo gồm 2 applications độc lập hoàn toàn (riêng biệt dependencies, build, tests, configs):

- `frontend/`: Frontend application (Next.js)
- `backend/`: Backend application (Spring Boot)

**Nguyên tắc**: Tuyệt đối KHÔNG tạo coupling giữa `fe/` và `be/`. Task thuộc phạm vi nào chỉ thao tác trong thư mục tương ứng.

```text
/
├── AGENTS.md
├── apps/frontend/               # Next.js App Router (src/app, components, hooks, lib, services, types)
└── apps/backend/               # Spring Boot (src/main/java/.../web_api, resources, test)
```

## 2. Frontend Conventions (`fe/`)

- **Tech Stack**: Next.js 16 (App Router), React 19, TypeScript strict, Zod 4, Jest + RTL, Storybook 10 + Vitest, CSS Modules.
- **Server Components mặc định**: Chỉ dùng `'use client'` khi cần React state, event listeners hoặc browser APIs.
- **TypeScript & Validation**: Strict mode, tuyệt đối không dùng `any`. Runtime validation dùng Zod cho API responses và forms.
- **Cấu trúc & Colocation**:
  - Dùng path alias `@/*` (trỏ đến `fe/src/*`).
  - Đặt component con trong `_components/`, tests trong `__tests__/`, stories tại `*.stories.tsx` colocate cùng component.
  - Không thêm library State Management (Redux/Zustand) khi React State hoặc URL State đã đáp ứng đủ.

## 3. Backend Conventions (`be/`)

- **Tech Stack**: Spring Boot 4, Java 17, Spring Web, SpringDoc OpenAPI, Spring Data JPA, Hibernate, MySQL 8 (chính), H2 (in-memory test/local), Lombok, Gradle.
- **API Boundary & DTO**:
  - Luôn nhận Request DTO và trả về Response DTO; tuyệt đối không expose JPA Entities ra API.
  - Dùng Bean Validation (`@Valid`, `@NotNull`, `@NotBlank`, v.v.) tại Request DTOs.
  - Chuẩn hóa response: HTTP status chuẩn (200, 201, 204); xử lý lỗi tập trung qua `@RestControllerAdvice` (`exception/`).
- **Layers & Dependency Injection**:
  - Dùng Constructor Injection (`@RequiredArgsConstructor`).
  - Business logic và transaction (`@Transactional`) đặt tại Service layer, không viết trong Controller.
  - Repository theo feature đặt tại `<api>/repository/`; repository dùng chung đặt tại `repository/`.

## 4. API Contract, Database & Security

- **Quy trình đổi API**: Thống nhất contract -> Cập nhật BE + OpenAPI docs -> Cập nhật FE (types, schemas, services) + tests. Đảm bảo backward compatibility.
- **Database**:
  - MySQL 8: Database chính (môi trường staging/prod dùng `ddl-auto: validate` hoặc migration).
  - H2: In-memory database cho automated tests hoặc local dev khi MySQL chưa sẵn sàng (`ddl-auto: update` hoặc `create-drop`).
- **Security**: Tuyệt đối không commit secrets, API keys, credentials. Dùng `.env` (FE) và environment variables (BE).

## 5. Commands & Quy tắc an toàn (Command Safety)

### Lệnh thực thi

- **Frontend** (`apps/frontend/`): `npm run dev` | `npm run build` | `npm run test` | `npm run lint` | `npm run storybook`
- **Backend** (`apps/backend/`): `./gradlew bootRun` | `./gradlew build` | `./gradlew test`

### An toàn thực thi (BẮT BUỘC)

- **KHÔNG TỰ Ý CHẠY TEST/BUILD NẶNG**: Khi đang ở bước đọc hiểu, phân tích, lập kế hoạch hoặc trả lời câu hỏi, Agent **tuyệt đối không chạy** lệnh tốn tài nguyên hoặc full test suite/build.
- **Chỉ chạy test/build khi**:
  1. Đang ở bước `Test` của task code thực tế có sửa đổi source code liên quan.
  2. Người dùng yêu cầu chạy lệnh cụ thể.

## 6. Agentic Workflow & Nguyên tắc thực thi

### Quy trình 6 bước

```text
Understand ──> Analyze ──> Plan ──> Implement ──> Test ──> Review
```

1. **Understand & Analyze**: Nắm rõ yêu cầu, kiến trúc và phạm vi ảnh hưởng tối thiểu.
2. **Plan**: Lập kế hoạch rõ ràng (danh sách file, giải pháp, rủi ro). **BẮT BUỘC user phê duyệt trước khi viết code**.
3. **Implement**: Chỉ sửa đúng phạm vi đã duyệt. Không tự ý thêm tính năng hay refactor ngoài lề.
4. **Test**: Chạy automated tests liên quan trực tiếp đến thay đổi để xác nhận. Tự fix lỗi nếu test/build fail.
5. **Review**: Tự rà soát: tính chính xác, bảo mật, clean code, không để lại file rác. Cập nhật tài liệu nếu có thay đổi contract.

### Thứ tự ưu tiên cốt lõi

`Existing convention > Simple solution (KISS/YAGNI) > Small focused change > New abstraction > New dependency`

- Không tự bịa requirements (hallucinate).
- Không tối ưu hóa sớm cho các kịch bản tương lai xa.
