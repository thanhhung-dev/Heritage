---
title: "Project Plan — HeritageGraph"
project: "CulturalMemoryGraph (CMG) / HeritageGraph"
version: "1.1"
status: "rebaselined"
effective_date: "2026-09-19"
start_date: "2026-08-27"
feature_complete_date: "2026-11-30"
demo_date: "2026-12-06"
source:
  - "C1SE.50_ProjectPlan_CulturalMemoryGraph-V1.0 (1).pdf"
authoring_language: "Vietnamese"
---

# PROJECT PLAN — HERITAGEGRAPH

**Capstone Project 1 — C1SE.50**  
**International School, Duy Tan University**

## Revision History

| Version | Date | Description | Author |
|---|---:|---|---|
| 1.0 | 14/09/2026 | Initial release | Dương Bảo Ngọc |
| 1.1 | 19/09/2026 | Rebaseline kiến trúc, phạm vi, lịch triển khai, AWS, Admin Knowledge Studio, Airflow và observability | Nhóm C1SE.50 |

## Project Information

| Thuộc tính | Nội dung |
|---|---|
| Project acronym | CMG |
| Project title | A Personalized GraphRAG Assistant for Exploring, Understanding and Planning Local Cultural Experiences |
| Product name | HeritageGraph |
| Start date | 27/08/2026 |
| Feature complete | 30/11/2026 |
| Final demo | 06/12/2026 |
| Lead institution | International School, Duy Tan University |
| Project mentor | ThS. Nguyễn Thị Thanh Tâm |
| Project leader | Dương Thanh Hùng |
| Target regions | Huế và Đà Nẵng |

> **Rebaseline rule:** `ARCHITECH-TECHNOLOGY.png` sau khi hiệu chỉnh, `docs/chatbot.md`, `schema.sql` và `docs/planning-artifacts/epics.md` là baseline hiện hành. PRD và Project Plan v1.0 chỉ tiếp tục binding ở các yêu cầu sản phẩm không xung đột.

---

# 1. Introduction

## 1.1 Purpose

Tài liệu này mô tả mục tiêu, phạm vi, tổ chức nhóm, kiến trúc công nghệ, kế hoạch triển khai, mốc bàn giao, nguồn lực, chi phí, tiêu chí chất lượng và rủi ro của HeritageGraph.

Version 1.1 rebaseline kế hoạch từ ngày 19/09/2026 để phản ánh:

- kiến trúc Domain GraphRAG/KAG-lite hiện tại;
- Admin Knowledge Studio thay cho nhập dữ liệu trực tiếp bằng SQL;
- workflow draft corpus → Airflow validation/indexing → human review → publish;
- Public Heritage Portal là giao diện sản phẩm chính, không chỉ có chatbot;
- backend và data được triển khai trên AWS;
- observability bằng Prometheus, Loki, Tempo, Grafana và Langfuse;
- feature freeze vào cuối tháng 11, dành 01–06/12 cho test, tài liệu và demo.

## 1.2 Project Overview

HeritageGraph là nền tảng trợ lý AI hỗ trợ khám phá, tìm hiểu chuyên sâu và lập kế hoạch trải nghiệm văn hóa tại Huế và Đà Nẵng trên sáu nhóm nội dung:

1. Di tích lịch sử;
2. Ẩm thực;
3. Danh thắng;
4. Nghệ thuật trình diễn;
5. Lễ hội;
6. Làng nghề truyền thống.

Hệ thống kết hợp:

- structured cultural knowledge có provenance;
- Hybrid Retrieval gồm lexical search, tìm không dấu/lỗi gõ và pgvector;
- Knowledge Graph cho entity resolution, graph traversal và recommendation;
- Qwen3-4B + LoRA để tổng hợp evidence thành câu trả lời tiếng Việt;
- citation/grounding gates để từ chối khi evidence không đủ;
- trải nghiệm Web kể chuyện di sản xuyên suốt Home, Explore, Entity Detail, Chat, Recommendation, 3D và audio.

LLM không phải kho kiến thức và không tự tạo sự thật. PostgreSQL là nguồn sự thật; mọi knowledge record quan trọng truy ngược được về passage và document nguồn.

## 1.3 Product Principles

1. **Evidence before generation:** Qwen chỉ nhận evidence do backend chọn.
2. **Draft is not production:** dữ liệu mới không phục vụ online trước khi validation và review hoàn tất.
3. **Human-controlled publishing:** Airflow không tự publish tri thức.
4. **Published-version consistency:** một request chỉ dùng một corpus version.
5. **Graceful degradation:** thiếu model, media hoặc dịch vụ ngoài không dẫn tới dữ liệu bịa hoặc trang trắng.
6. **Measure continuously:** test và observability được thêm cùng feature, không để tới cuối dự án.
7. **Feature complete by November:** không phát triển feature mới trong tuần demo.

## 1.4 Technology Stack

| Architectural area | Technology |
|---|---|
| UX/UI design | Figma, FigJam; public heritage storytelling design system |
| Public frontend | Next.js 14 App Router, React 18, TypeScript; custom editorial composition, Ant Design/Ant Design X chỉ làm component primitive khi phù hợp |
| Admin frontend | Next.js 14 App Router, React 18, TypeScript, Ant Design |
| Maps | Leaflet, OpenStreetMap |
| 3D | Three.js hoặc `<model-viewer>`, `.glb`, Draco/Meshopt |
| Backend API | Python 3.12, FastAPI, Pydantic v2, Uvicorn |
| Persistence | PostgreSQL 16, SQLAlchemy, Alembic |
| Search extensions | pgvector, pg_trgm, PostgreSQL full-text search |
| Knowledge graph | PostgreSQL source of truth; versioned NetworkX projection cho traversal/recommendation |
| Data orchestration | Apache Airflow |
| Embedding/indexing | Semantic chunking, content hash, vector embedding contract, versioned manifest |
| LLM | Qwen3-4B + LoRA |
| Local inference | MLX base + adapter hoặc llama.cpp với GGUF/adapter tương thích; không trộn hai format runtime |
| AWS data/storage | Amazon RDS PostgreSQL, Amazon S3, Amazon ECR; AWS compute theo ADR triển khai |
| Infrastructure | Terraform |
| CI/CD | GitHub, Jenkins |
| Metrics | Prometheus |
| Logs | Loki |
| Distributed traces | OpenTelemetry, Tempo hoặc AWS X-Ray theo ADR triển khai |
| Dashboards/alerts | Grafana |
| LLM observability | Langfuse |
| Testing | Python unit/integration tests, API contract tests, Playwright E2E |

### AWS Storage Decision

Trong MVP, Amazon S3 là object store chuẩn cho raw documents, manifests, audio và 3D assets. Không dual-write đồng thời R2/S3/Azure trong critical path. Cloudflare R2 chỉ được bổ sung sau khi có yêu cầu CDN/cost cụ thể và có ADR xác định ownership, migration và URL policy.

### Inference Decision

Backend và data chạy trên AWS. LLM inference có thể chạy local hoặc trên inference host riêng trong thời gian capstone. Nếu dùng llama.cpp, model/adapter phải ở format GGUF tương thích. MLX adapter chỉ chạy trong MLX runtime. Việc chuyển đổi hoặc fuse model phải qua regression evaluation trước deployment.

## 1.5 Architecture Overview

```text
OFFLINE KNOWLEDGE LIFECYCLE

Admin Knowledge Studio
        │
        ▼
FastAPI validation → Draft Corpus Release
        │
        ▼
Airflow: validate → deduplicate → provenance/version checks
        │             → chunk/embed → indexes + manifest
        ▼
Validation Report → Human Review → Atomic Publish
                                        │
                                        ▼
ONLINE SERVING — PUBLISHED CORPUS ONLY

Public Portal → FastAPI
                 ├── Graph Service
                 ├── Recommendation Service
                 └── Chat Service
                       │
                       ▼
Normalize → Resolve Entity → Intent → Query Planner
                       │
          Exact / Timeline / Graph / Section / Text
                       │
                       ▼
            Evidence Context Builder
                       │
              Pre-generation Gate
                       │
                 Qwen3-4B + LoRA
                       │
             Citation/Grounding Gate
                 ├── answered
                 ├── clarify
                 └── abstained
```

## 1.6 Target Users and Product Surfaces

### Public UI Design Direction — Heritage Storytelling

Toàn bộ giao diện người dùng — Home, Explore, Entity Detail, Chat, Recommendation và Multimedia — sử dụng một visual language kể chuyện văn hóa thống nhất:

- bố cục editorial giàu hình ảnh, có nhịp điệu giữa khối lớn/nhỏ thay vì lưới dashboard đồng đều;
- card nội dung, đường thời gian, địa điểm, nhân vật, sự kiện và quan hệ được kết nối thành mạch khám phá;
- màu sắc, typography, texture và transition gợi chất liệu di sản Huế–Đà Nẵng nhưng vẫn đảm bảo khả năng đọc;
- người dùng có thể chuyển từ một câu chuyện sang nguồn, thực thể liên quan, bản đồ, chatbot hoặc recommendation mà không mất ngữ cảnh;
- desktop và mobile giữ cùng hierarchy, narrative flow và nhận diện thị giác;
- loading, empty, error, clarify và abstained cũng phải theo cùng design language.

Admin Knowledge Studio sử dụng Ant Design dashboard/form/table rõ ràng, mật độ thông tin cao và ưu tiên thao tác an toàn thay vì bố cục kể chuyện của Public Portal.

### Admin / Cultural Knowledge Manager

- quản lý document và metadata nguồn;
- tạo passage và chọn evidence;
- quản lý entity, alias và place profile;
- biên tập claim, timeline, relation và narrative;
- submit validation, xử lý issues, review và publish corpus;
- xem audit log, graph/corpus health và evaluation metrics.

### End Users

- khám phá nội dung qua Home và Explore;
- tìm kiếm/lọc theo vùng và loại;
- xem Entity Detail, sources, timeline, relation và narrative;
- hỏi chatbot tiếng Việt có citation;
- nhận recommendation có reason path;
- xem bản đồ, mô hình 3D, nghe audio và đọc transcript.

## 1.7 Main Application Routes

| Route | Chức năng |
|---|---|
| `/` | Story-driven Home: visual stories, search, featured content, category/region và recommendation |
| `/explore` | Heritage discovery canvas với search/filter và linked heritage cards |
| `/explore/[entityId]` | Story-driven Entity Detail: narrative, claims, timeline, relations, sources, map và media |
| `/chat` | Grounded HeritageGraph assistant trong cùng public visual language |
| `/preferences` | Quản lý consent, xuất và đặt lại hồ sơ cá nhân hóa ẩn danh lưu trong `localStorage` |
| `/admin/*` | Knowledge Studio, validation, review, publish, audit và dashboard |

## 1.8 Scope

### Mandatory scope by 30/11/2026

- Public Heritage Portal có visual language kể chuyện di sản thống nhất xuyên suốt Home, Explore, Entity Detail, Chat và Recommendation;
- Admin Knowledge Studio hoàn chỉnh;
- một workflow Airflow validation/indexing/publish hoạt động end-to-end;
- published corpus và provenance ở mức passage;
- Hybrid Retrieval + Graph operators + grounded Q&A;
- cold-start và explainable recommendation cơ bản;
- tối thiểu một địa điểm pilot có nội dung sâu, 3D và audio/transcript;
- dữ liệu corpus hướng tới 80+ documents, tối thiểu 8 tài liệu cho mỗi nhóm cốt lõi khi nguồn cho phép;
- AWS staging/demo environment;
- test, evaluation và observability dashboard.

### Conditional/stretch scope

- proactive weather/POI advisory cards;
- audio tiếng Anh nếu audio tiếng Việt và evidence gate đã ổn định;
- nhiều hơn một 3D site;
- R2 CDN hoặc multi-cloud media storage;
- staged production traffic rollout thật nếu môi trường demo không có traffic thực.

### Out of scope

- mobile native;
- đặt vé/tour hoặc thanh toán;
- crowd-sourced knowledge publishing;
- OCR/video recognition quy mô lớn;
- autonomous agents tự sửa/publish knowledge;
- graph traversal không giới hạn;
- LLM dùng kiến thức trong weights để thay evidence còn thiếu.

---

# 2. Team Organization

## 2.1 Group Information

| Full name | Role | Contact |
|---|---|---|
| ThS. Nguyễn Thị Thanh Tâm | Project Supervisor | ttamdtu@gmail.com |
| Dương Thanh Hùng | Project Leader / AI Backend Engineer | hungthanhhung37@gmail.com |
| Cao Văn Khoa | Data and Knowledge Engineer | caovankhoa11@gmail.com |
| Đào Hồ Anh Tùng | UI/UX and Public Frontend Developer | daohoanhtung@gmail.com |
| Lê Anh Nghĩa | UI/UX and Admin Frontend Developer | leanhnghia23@gmail.com |
| Dương Bảo Ngọc | QA and Documentation | ngocduong.200011@gmail.com |

## 2.2 Roles and Responsibilities

### Project Leader / AI Backend Engineer

- quản lý scope, risk, milestones và Scrum process;
- sở hữu kiến trúc tổng thể và API contracts;
- phát triển Chat/Graph orchestration, query planner, retrieval operators và Evidence Builder;
- tích hợp Qwen3-4B, citation validation và abstention/grounding gates;
- review backend/data contracts và quality gates;
- phối hợp deployment backend trên AWS.

### Data and Knowledge Engineer

- thu thập, chuẩn hóa và cân bằng corpus;
- thiết kế ontology, claim fields, predicates và event types;
- quản lý provenance và quality rules;
- phát triển Airflow DAG cho validation, embedding, indexing và manifests;
- xây versioned NetworkX projection và pgvector indexes;
- hỗ trợ domain logic và typed forms của Admin frontend.

### UI/UX and Public Frontend Developer

- Figma và heritage storytelling design system cho toàn bộ Public Portal;
- phát triển Home, Explore, Entity Detail, Chat và Recommendation theo cùng visual language;
- tích hợp map, timeline, citation/source drawer, recommendation, 3D và audio;
- phát triển Preferences UI để xem consent, xuất và đặt lại hồ sơ cá nhân hóa trong `localStorage`;
- responsive design, accessibility và frontend performance.

### UI/UX and Admin Frontend Developer

- Figma cho Admin Knowledge Studio;
- phát triển document/passage/evidence và structured knowledge editors;
- phát triển Validation Center, review/publish, audit và dashboards;

### QA and Documentation

- duy trì Test Plan và traceability FR → story → test;
- thiết kế và thực hiện unit, integration, contract, E2E và UAT scenarios;
- quản lý gold/evaluation datasets cùng Data/AI owners;
- đo retrieval, citation, abstention, recommendation và latency;
- biên soạn SRS, API specifications, data dictionary, user guide, runbook và final reports.

### Project Supervisor

- review tiến độ hàng tuần;
- định hướng scope và phương pháp;
- review quyết định kiến trúc/AI quan trọng;
- phê duyệt deliverables cuối kỳ.

## 2.3 Assignment Rule

Project Plan chỉ xác định role ownership. Tên người thực hiện từng hạng mục được gán trong Jira ở mức **story/subtask**, không hard-code trong epic/sprint. Mỗi UI story có các subtasks Figma, review, implementation, responsive/accessibility và tests. Mỗi backend/data story có subtasks implementation, migration, test, observability và documentation tương ứng.

## 2.4 Communication and Reporting

| Activity | Frequency | Tools | Output |
|---|---|---|---|
| Daily team sync | Hằng ngày, 10–15 phút | Google Meet/Zalo/Discord | Blockers và kế hoạch ngày |
| Sprint planning | Đầu sprint | Jira, GitHub | Sprint goal và committed stories |
| Design/architecture review | Hằng tuần | Figma, Jira, Google Meet | Quyết định UX/architecture và ADR |
| Mentor progress review | Hằng tuần | Trực tiếp/Google Meet/Email | Demo increment và feedback |
| Test/AI review | Cuối mỗi test cycle | Grafana, Langfuse, evaluation reports | Quality findings và go/no-go |
| Sprint review/retrospective | Cuối sprint | Demo + Jira | Accepted work và process actions |
| Final handover | 06/12/2026 | Demo, reports, source repository | Acceptance package |

---

# 3. Development Process

## 3.1 Agile/Scrum Model

Từ rebaseline 19/09, dự án chạy theo Sprint 0 một tuần và năm sprint chức năng khoảng hai tuần. Mỗi sprint gồm:

1. planning và story refinement;
2. Figma/handoff cho UI story trong cùng sprint;
3. implementation;
4. integration và tests;
5. observability instrumentation cho feature mới;
6. demo và retrospective.

Phân bổ mục tiêu trong sprint:

- khoảng 75% xây feature;
- khoảng 15% test và documentation;
- khoảng 10% instrumentation/observability.

Observability là Definition of Done, không phải mục tiêu feature độc lập.

## 3.2 Epic Structure

| Epic | User outcome |
|---|---|
| Epic 1 — Admin Knowledge Studio | Admin biên soạn knowledge package ở trạng thái draft mà không dùng SQL/UUID thủ công |
| Epic 2 — Corpus Validation & Publishing | Draft được Airflow kiểm tra, human review và publish atomically |
| Epic 3 — Public Heritage Portal | Người dùng khám phá published content qua giao diện kể chuyện di sản xuyên suốt Home, Explore và Entity Detail |
| Epic 4 — Grounded Heritage Assistant | Người dùng nhận answered/clarify/abstained với citation hợp lệ |
| Epic 5 — Explainable Personalized Discovery | Người dùng nhận recommendation có reason path từ hồ sơ ẩn danh trên thiết bị và tự kiểm soát dữ liệu đó |
| Epic 6 — 3D and Multimedia Heritage Experience | Người dùng xem 3D, bản đồ, nghe audio và đọc transcript có provenance |

FR coverage và epic structure được quản lý tại `docs/planning-artifacts/epics.md`; stories và assignee tiếp tục được chi tiết hóa ở mức story/subtask.

## 3.3 Sprint 0 Engineering Enablers

Sprint 0 quản lý các enabler stories trước feature development:

1. repository và environment configuration;
2. PostgreSQL/RDS, extensions và Alembic baseline;
3. AWS staging, ECR, S3, IAM và networking;
4. GitHub/Jenkins/Terraform delivery foundation;
5. Prometheus/Loki/Tempo/Grafana/Langfuse baseline;
6. Figma foundations, public heritage storytelling design system, public/admin shells và API mocks;
7. test harness, fixtures, Playwright và documentation templates.

## 3.4 Definition of Done

Một story chỉ hoàn tất khi:

- acceptance criteria pass;
- code review hoàn tất;
- migration/rollback được kiểm tra nếu story thay đổi DB;
- unit/integration/contract/E2E tests phù hợp pass;
- UI state và accessibility được kiểm tra nếu story có UI;
- metrics/logs/traces cần thiết đã được instrument;
- secrets/PII không xuất hiện trong logs/traces;
- API/data/operational docs được cập nhật;
- feature chạy trên AWS staging hoặc documented target environment;
- demo evidence được đính kèm Jira story.

---

# 4. Schedule and Milestones

## 4.1 Overall Timeline

| Phase | Dates | Goal |
|---|---:|---|
| Initiation and original planning | 27/08–18/09 | Proposal, SRS, schema, baseline, original architecture and plan |
| Sprint 0 — Rebaseline and engineering foundation | 19/09–25/09 | Architecture/UX contracts, AWS staging and delivery foundations |
| Sprint 1 — Source authoring and Public Home | 26/09–09/10 | Document/passage/entity draft flow; Public Home |
| Sprint 2 — Structured knowledge and Explore | 10/10–23/10 | Structured editors; Explore and Entity Detail |
| Sprint 3 — Validation, publishing and public integration | 24/10–06/11 | Airflow validation/review/publish; public UI on published APIs |
| Sprint 4 — Grounded QA and Recommendation | 07/11–20/11 | Chatbot, citations, grounding and recommendation MVP |
| Sprint 5 — Multimedia and release candidate | 21/11–30/11 | 3D/audio, integration, evaluation, UAT and feature freeze |
| Demo freeze and handover | 01/12–06/12 | Bug fixes only, full verification, reports, rehearsal and demo |

## 4.2 Detailed Rebaseline Schedule

### Sprint 0 — 19/09 to 25/09

**Objective:** establish a shared implementation substrate.

- architecture and API contracts;
- PostgreSQL/Alembic migration plan;
- AWS staging and object-storage policy;
- Jenkins/Terraform baseline;
- observability baseline;
- Figma information architecture, heritage storytelling visual direction, design tokens và low-fidelity critical flows;
- public/admin shells, mocks and test foundation.

**Exit gate:** frontend reaches FastAPI health on AWS staging; backend reaches PostgreSQL; migration and telemetry smoke tests pass.

### Sprint 1 — 26/09 to 09/10

**Objective:** admin creates basic draft knowledge and users see the first Public Home increment.

- admin authentication and audit;
- document source CRUD;
- passage/evidence workspace;
- entity/alias draft management;
- story-driven Home, navigation, search entry và featured story sections;
- API contract and E2E tests;
- feature metrics/logs/traces.

**Exit gate:** admin creates document → passage → entity → evidence as draft; Public Home works with seed/mock data.

### Sprint 2 — 10/10 to 23/10

**Objective:** complete structured knowledge authoring and public discovery surfaces.

- claim, timeline, participant, relation and narrative editors;
- duplicate/type/provenance validation;
- Explore discovery canvas, search và filters;
- story-driven Entity Detail với narrative, claims, timeline, relations và sources;
- representative deep knowledge package for one pilot location;
- frontend/backend integration tests.

**Exit gate:** one pilot location has a complete draft knowledge package; Home → Explore → Entity Detail journey works.

### Sprint 3 — 24/10 to 06/11

**Objective:** establish trusted corpus publication.

- submission and idempotent validation run;
- Airflow validation, deduplication, provenance/version checks;
- embedding, index and manifest generation;
- Validation Center, issue navigation, review and atomic publish;
- Home/Explore/Detail switch from mocks to published APIs;
- Airflow/corpus dashboards and failure alerts.

**Exit gate:** a release goes draft → validation → issue resolution → review → publish; online APIs cannot read draft data.

### Sprint 4 — 07/11 to 20/11

**Objective:** deliver grounded QA and explainable recommendation.

- normalization, fuzzy correction and entity resolution;
- intent router and query planner;
- exact, timeline, graph, section and text operators;
- Evidence Context Builder;
- Qwen3-4B inference and citation/grounding gates;
- answered/clarify/abstained UX;
- cold-start, candidate generation, rank/diversify and reason path;
- Preferences, consent và local profile export/reset flow;
- retrieval, generation, grounding and recommendation tests.

**Exit gate:** published-content questions return grounded responses; insufficient/ambiguous questions abstain or clarify; recommendation displays a reason path.

### Sprint 5 — 21/11 to 30/11

**Objective:** complete multimedia integration and produce a release candidate.

- map and timeline final integration;
- one production-ready `.glb` experience;
- Vietnamese audio and transcript with evidence checks;
- optional English audio only after mandatory gates pass;
- S3 asset provenance and fallback states;
- responsive/accessibility/performance hardening;
- full integration/E2E/evaluation/UAT;
- feature freeze on 28/11 and release candidate by 30/11.

**Exit gate:** complete Home → Explore → Detail → Chat → Recommendation → 3D/Audio journey passes on AWS staging.

### Demo Freeze — 01/12 to 06/12

No new features are accepted.

- fix release blockers only;
- rerun full tests and evaluation;
- backup RDS, S3 and manifests;
- complete SRS/API/Data Dictionary/User Guide/Evaluation Report;
- prepare demo video and fallback assets;
- rehearse Research Journey and Cultural Visit Journey;
- finalize slides and acceptance package.

## 4.3 Milestones

| Date | Milestone |
|---:|---|
| 25/09 | AWS staging, DB migration, CI and observability foundation ready |
| 09/10 | Basic Admin draft authoring and Public Home demonstrated |
| 23/10 | Complete pilot knowledge package and Entity Detail demonstrated |
| 06/11 | First validated and published corpus release |
| 20/11 | Grounded chatbot and recommendation MVP complete |
| 28/11 | Feature freeze |
| 30/11 | Release candidate and UAT complete |
| 03/12 | Final evaluation report and demo video complete |
| 06/12 | Final demonstration and handover |

## 4.4 Scope-Cut Order

Nếu tiến độ trượt, cắt theo thứ tự:

1. số lượng 3D sites, giữ tối thiểu một pilot;
2. audio tiếng Anh, giữ audio tiếng Việt và transcript;
3. proactive weather/POI advisory cards;
4. số lượng polished locations, giữ reusable pipeline và deep pilot;
5. staged rollout thật, thay bằng controlled staging demonstration.

Không được cắt:

- provenance/evidence;
- validation/review/publish gate;
- citation và abstention/grounding gate;
- Public Home/Explore/Entity Detail;
- Admin Knowledge Studio critical flow;
- test/evaluation suite;
- consent, export/reset cho hồ sơ cá nhân hóa cục bộ đã lưu.

---

# 5. Quality, Evaluation and Observability

## 5.1 Product Quality Targets

| Metric | Target |
|---|---:|
| Retrieval recall@1 | ≥95% trên tập in-domain gồm alias, không dấu và paraphrase |
| Citation faithfulness | ≥85% |
| Citation coverage | ≥90% |
| Abstention accuracy | ≥90% |
| Recommendation precision@5 | ≥70% trên evaluation sample có review |
| Chat p95 | ≤8 giây trong môi trường demo |
| Recommendation latency excluding LLM | ≤2 giây |
| Entity Detail load | ≤3 giây ở điều kiện đo đã ghi nhận |
| Fabricated typed-card fields | 0 |
| Published records without required provenance | 0 |

Các report phải ghi model, adapter/GGUF hash, prompt version, corpus version, retrieval configuration và evaluation dataset version.

## 5.2 Testing Layers

1. **Unit tests:** domain validation, normalization, scoring, gates.
2. **Database tests:** constraints, migrations, version isolation, transactions.
3. **Contract tests:** frontend/backend, Airflow/backend, inference/backend.
4. **Integration tests:** repository, retrieval, graph, embedding, object storage.
5. **AI regression tests:** fixed query/evidence/generation cases.
6. **E2E tests:** Admin publish journey và Public discovery/chat journey.
7. **Failure tests:** Airflow, PostgreSQL, LLM và media outages.
8. **UAT:** hai end-to-end demo journeys.

## 5.3 Observability

Observability chiếm khoảng 10% Definition of Done mỗi sprint, không thay thế feature development.

| Signal | Stack | Examples |
|---|---|---|
| Metrics | Prometheus | request rate, error rate, p50/p95/p99, DB pool, Airflow duration, retrieval/LLM latency |
| Logs | Loki | structured application, Airflow and deployment logs with correlation ID |
| Service traces | OpenTelemetry + Tempo/X-Ray | frontend/API/DB/service request path |
| LLM traces | Langfuse | model/prompt/corpus version, evidence IDs, tokens, latency, grounding result |
| Dashboards/alerts | Grafana | service health, corpus pipeline, QA, recommendation, media and AWS health |

Không ghi password, token, raw IP hoặc dữ liệu cá nhân nhạy cảm vào logs/traces.

---

# 6. Infrastructure and Delivery

## 6.1 AWS Target

```text
GitHub
   │
   ▼
Jenkins ── tests/build ──▶ Amazon ECR
                              │
                              ▼
                    AWS backend compute
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
      Amazon RDS          Amazon S3        Airflow runtime
   PostgreSQL+pgvector  data/media/manifests validation/indexing
```

Exact AWS compute choice is recorded in an ADR before Sprint 1. EKS and MWAA are not introduced unless current infrastructure or budget requires them; the team prefers the smallest operational surface that meets the demo goal.

## 6.2 CI/CD Gates

1. detect changed components;
2. lint/type checks;
3. unit/integration/contract tests;
4. migration validation;
5. frontend build and Playwright smoke tests;
6. image build and ECR push;
7. staging deployment;
8. smoke/health checks;
9. rollback on failure.

Software deployment and model/prompt rollout are separate pipelines. A model rollout must pass grounding, latency and error gates before promotion.

## 6.3 Security and Privacy

- Argon2id for Admin passwords;
- HttpOnly/Secure/SameSite cookies for Admin authenticated sessions;
- least-privilege IAM;
- secrets outside source control;
- authenticated admin write paths;
- Public User không cần tài khoản hoặc đăng nhập; backend không lưu định danh hay hồ sơ cá nhân hóa của Public User;
- consent trước khi frontend ghi tương tác vào `localStorage`;
- schema hồ sơ ẩn danh phải có giới hạn, version và được backend kiểm tra khi nhận recommendation request;
- Preferences cho phép xuất và đặt lại hồ sơ cá nhân hóa cục bộ;
- audit log for administrative changes;
- private/default-deny infrastructure where practical.

---

# 7. Cost and Effort

## 7.1 Labor Cost

| Role | Rate |
|---|---:|
| Project Lead / AI Backend | USD 4/hour |
| Data and Knowledge Engineer | USD 4/hour |
| Public Frontend Developer | USD 4/hour |
| Admin Frontend Developer | USD 4/hour |
| QA and Documentation | USD 4/hour |

## 7.2 Budget Baseline

| Item | Cost |
|---|---:|
| Labor: 1,200 person-hours × USD 4 | USD 4,800 |
| AWS hosting, storage, domains and contingency | USD 500 |
| **Total** | **USD 5,300** |

### Capacity Correction

Project Plan v1.0 ghi “16 hours/day/person”, nhưng phép tính đúng là:

```text
1,200 person-hours ÷ 5 members ÷ 15 weeks = 16 hours/week/person
```

Do đó baseline chính thức là **240 giờ/người trong 15 tuần, trung bình 16 giờ/tuần/người**. Actual effort và AWS cost được theo dõi hằng tuần; vượt budget phải kích hoạt scope-cut order.

---

# 8. Project Risks

| Risk | Impact | Likelihood | Mitigation / trigger |
|---|---|---|---|
| Dữ liệu không đều giữa sáu nhóm | High | Medium | Theo dõi inventory theo category; ưu tiên nguồn thiếu; giữ ≥8/category khi nguồn cho phép |
| Sai entity/alias tiếng Việt hoặc truy vấn không dấu | High | High | Closed vocabulary, alias review, fuzzy/trigram search, curated regression set |
| Knowledge thiếu hoặc sai provenance | High | Medium | DB constraints, evidence selector, Airflow validation, human publish gate |
| Draft hoặc cross-version data bị phục vụ online | Extreme | Medium | Published-only repository filters; pin corpus version; version-isolation tests |
| Qwen tạo claim/citation không được evidence hỗ trợ | High | Medium | Evidence-only prompt, pre/post gates, citation validation, abstention regression tests |
| MLX adapter và llama.cpp/GGUF không tương thích | High | Medium | Separate runtimes; versioned model manifest; conversion/fusion evaluation gate |
| Airflow retry tạo duplicate hoặc partial index | High | Medium | Idempotency key, validation run state, staged manifest và atomic activation |
| AWS deployment/cost vượt budget | High | Medium | Smallest viable services, weekly billing review, Terraform, avoid premature EKS/MWAA |
| Frontend chờ backend/data contracts | High | Medium | OpenAPI contract từ Sprint 0, generated types, mock server và contract tests |
| 3D/audio gây chậm hoặc trễ | Medium | Medium | Một pilot, pre-generated audio, compressed GLB, S3/CDN cache, fallback states |
| Observability được thêm quá muộn | Medium | Medium | Instrument cùng story; Sprint 0 telemetry baseline; Grafana gates mỗi sprint |
| Tích hợp nhiều subsystem làm trễ lịch | High | High | Feature freeze 28/11, weekly critical-path review, scope-cut order đã định trước |
| Thiếu thời gian test/tài liệu cuối kỳ | High | Medium | QA/docs chạy từ Sprint 0; 01–06/12 chỉ hardening và handover |

---

# 9. Handover Products

| No. | Deliverable | Acceptance summary |
|---:|---|---|
| 1 | Web Prototype & Source Code | Public Portal, Admin Studio và documented local/AWS startup |
| 2 | AWS Infrastructure & Delivery Assets | Terraform, Jenkins pipeline, deployment/runbook và environment documentation |
| 3 | Cultural Data Repository | Standardized documents, structured knowledge, evidence links và published corpus manifest |
| 4 | Admin Knowledge Studio | Draft authoring, evidence selection, validation issues, review, publish và audit |
| 5 | Airflow Knowledge Pipeline | Idempotent validation, embedding/indexing, quality report và versioned manifest |
| 6 | Hybrid RAG & GraphRAG Pipeline | Retrieval operators, graph traversal, traceability và evaluation reports |
| 7 | Qwen3-4B + LoRA Deliverable | Versioned model/adapter or GGUF manifest; grounded generation integration |
| 8 | Recommendation Module | Cold start, anonymous local-profile ranking, diversity và reason path |
| 9 | Public Heritage Experience | Story-driven Home, Explore, Entity Detail, Chat, recommendation, map, timeline và one 3D/audio pilot |
| 10 | Observability & Evaluation Suite | Grafana/Langfuse views, automated tests, metrics and reproducible reports |
| 11 | Documentation Package | SRS, architecture, API specs, data dictionary, Test Plan, User Guide, runbook and final report |
| 12 | Demo Package | Research Journey, Cultural Visit Journey, slides, demo video and fallback assets |

---

# 10. Acceptance Criteria

Project handover is accepted when:

1. one knowledge package can travel from draft through validation/review to published;
2. draft/retired/withdrawn data cannot be served as active knowledge;
3. Public Home, Explore, Entity Detail, Chat và Recommendation sử dụng nhất quán heritage storytelling visual language và published data;
4. grounded chatbot returns citation-backed answers and safely clarifies/abstains;
5. recommendation includes an explainable reason path;
6. one pilot location demonstrates map, timeline, 3D, audio and transcript;
7. mandatory tests and evaluation reports run from documented commands;
8. Grafana/Langfuse provide enough evidence to diagnose the demo request path;
9. AWS staging/demo environment can be recreated or recovered from documented assets;
10. source, manifests, reports and documentation are handed over by 06/12/2026.

---

# 11. References

## 11.1 Standards and Technical Documents

1. IEEE 830 / ISO/IEC/IEEE 29148 — Software Requirements Specification / Requirements Engineering.
2. IEEE 1016 — Software Design Description.
3. IEEE 829 / ISO/IEC/IEEE 29119 — Software Testing.
4. ISO/IEC/IEEE 12207:2017 — Software Life Cycle Processes.
5. ISO/IEC 25010 — Systems and Software Quality Requirements and Evaluation.
6. ISO/IEC 23894 — Artificial Intelligence Risk Management.

## 11.2 AI, RAG and GraphRAG

1. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS 2020. https://arxiv.org/abs/2005.11401
2. Microsoft Research. *Project GraphRAG: LLM-Derived Knowledge Graphs.*
3. OpenSPG. *Knowledge Augmented Generation (KAG).* Reference patterns only; runtime is not adopted for MVP.

## 11.3 Digital Cultural Heritage

1. CyArk. *Digital Heritage Preservation.*

## 11.4 Internal Project Sources

1. `ARCHITECH-TECHNOLOGY.png` — technology architecture baseline, reviewed 19/09/2026.
2. `docs/chatbot.md` — chatbot target architecture.
3. `schema.sql` — knowledge persistence baseline.
4. `docs/planning-artifacts/epics.md` — current requirements and epic coverage.
5. `C1SE.50_ProjectPlan_CulturalMemoryGraph-V1.0 (1).pdf` — Version 1.0 source plan.
