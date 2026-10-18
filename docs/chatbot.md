# Kiến trúc chatbot HeritageGraph

Ngày cập nhật: 15/09/2026.

## 1. Quyết định kiến trúc

HeritageGraph dùng kiến trúc **Domain GraphRAG/KAG-lite**:

- tham khảo **Microsoft GraphRAG** cho dataflow lập chỉ mục, provenance qua text
  unit, Local Search và Context Builder;
- tham khảo **OpenSPG KAG** cho ontology có schema, mutual indexing, query planner
  và các retrieval operator;
- dùng **PostgreSQL** làm nguồn sự thật thay vì sử dụng storage/runtime của hai
  framework;
- dùng **Qwen3-4B local** để tổng hợp và trình bày evidence, không dùng model làm
  kho kiến thức;
- giữ **FastAPI modular monolith**, chưa cần agent framework, Neo4j, OpenSPG hay
  Microsoft GraphRAG runtime.

MVP là một vertical slice đào sâu một địa điểm. Sau khi pipeline được kiểm chứng,
cùng mô hình được nhân sang 29 địa điểm còn lại.

## 2. Phân chia reference

| Thành phần | Reference chính | Cách áp dụng |
|---|---|---|
| Document và chunk | Microsoft GraphRAG | `source_doc` → `passage` |
| Provenance | Microsoft GraphRAG | Mọi tri thức trỏ về passage nguồn |
| Local entity context | Microsoft GraphRAG Local Search | Dựng Entity Dossier theo entity trung tâm |
| Context Builder | Microsoft GraphRAG | Hợp nhất, loại trùng và giới hạn evidence |
| Ontology domain | KAG | Entity, event, predicate và field có schema |
| Mutual indexing | KAG | Truy vấn được cả knowledge → chunk và chunk → knowledge |
| Query planning | KAG | Chọn operator theo intent thay vì một search cho mọi câu |
| Multi-hop reasoning | KAG | Graph traversal có giới hạn 1–2 hop |
| Persistence | HeritageGraph | PostgreSQL + Alembic |
| Narrative biên tập | HeritageGraph | Nội dung chuyên đề do người biên soạn và review |
| Generation | HeritageGraph | Qwen3-4B local |
| Grounding | HeritageGraph | Citation gate trước khi trả response |

Không sao chép nguyên framework. Chỉ dùng những pattern phù hợp với dữ liệu di
sản curated và quy mô 30 địa điểm lõi.

## 3. Kiến trúc tổng thể

```text
                     OFFLINE — KNOWLEDGE INDEXER
                     (Microsoft GraphRAG + KAG)

Nguồn chính thức / học thuật / quản lý / báo chí
                           │
                           ▼
                    Source ingestion
                           │
                           ▼
                source_doc → passage
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           entity        claim     timeline_event
              │                           │
              └──────── relation ─────────┘
                           │
                           ▼
                  narrative_section
                           │
                           ▼
                Review + corpus_version
                           │
                           ▼
              FTS / n-gram / vector indexes


                         ONLINE — QA SOLVER
                              (KAG-lite)

User → Normalize → Resolve entity → Classify intent → Query planner
                                                           │
                  ┌────────────────────────────────────────┤
                  ▼               ▼                        ▼
             Exact operator  Graph operator           Text operator
             claim/timeline  relation 1–2 hop      BM25/ngram/vector
                  └───────────────┬────────────────────────┘
                                  ▼
                    Local Context / Entity Dossier
                                  ▼
                       Evidence Context Builder
                                  ▼
                             Qwen3-4B
                                  ▼
                       Citation/Grounding Gate
                         ├── answered
                         ├── clarify
                         └── abstained
```

## 4. Ranh giới trách nhiệm

### 4.1 Knowledge Indexer

Chạy offline hoặc khi publish corpus version mới:

1. Thu thập và lưu tài liệu nguồn.
2. Chia tài liệu thành passage.
3. Trích hoặc biên tập entity, claim, event và relation.
4. Liên kết mọi tri thức dẫn xuất về passage.
5. Review trước khi publish.
6. Dựng lại lexical/vector indexes có thể tái tạo.

LLM có thể đề xuất extraction nhưng không được tự publish tri thức.

### 4.2 QA Solver

Chạy cho mỗi câu hỏi:

1. Chuẩn hóa câu hỏi.
2. Resolve entity và kiểm tra phạm vi.
3. Phân loại intent.
4. Lập query plan nhỏ, xác định trước.
5. Chạy các operator cần thiết.
6. Dựng evidence package.
7. Gọi Qwen3-4B.
8. Kiểm tra grounding và citation.

QA Solver không sửa dữ liệu và không tạo knowledge graph trong lúc trả lời.

### 4.3 Qwen3-4B

Qwen làm:

- tổng hợp evidence thành câu trả lời tiếng Việt;
- giải thích quan hệ giữa dữ kiện, sự kiện và entity;
- trình bày chronology;
- đính chính tiền đề sai nếu evidence chứng minh;
- gắn citation ID đã được backend cấp.

Qwen không làm:

- tự sinh SQL production;
- tự tìm toàn bộ database;
- tự tạo nguồn, entity, relation hoặc citation;
- dùng kiến thức trong trọng số để bổ sung dữ liệu còn thiếu;
- tự quyết định `in_scope`, `depth_tier` hoặc `entry_status`.

## 5. Data model theo Microsoft GraphRAG

Mô hình cơ sở:

```text
Microsoft GraphRAG       HeritageGraph
──────────────────       ─────────────
Document                 source_doc
TextUnit                 passage
Entity                   entity
Relationship             relation
Covariate/Claim          claim + timeline_event
Community Report         không dùng trong MVP
```

### 5.1 `source_doc`

Một dòng là một tài liệu nguồn: trang web, PDF, hồ sơ di sản hoặc bài nghiên cứu.
Bảng lưu URL, loại nguồn, tier, license, raw text, hash và thời điểm thu thập.

### 5.2 `passage`

Passage tương đương TextUnit của Microsoft GraphRAG. Đây là đơn vị:

- retrieval;
- citation;
- extraction;
- truy vết provenance;
- tái lập tri thức dẫn xuất.

Văn bản gốc chỉ lưu một lần tại passage. Các bảng tri thức không copy toàn bộ
đoạn nguồn.

### 5.3 `entity` và `entity_alias`

`entity` là sổ danh tính, mỗi đối tượng một ID/slug ổn định. `entity_alias` ánh xạ
tên chính thức, Hán Việt, dân gian, lịch sử, tiếng Anh và lỗi gõ đã review về
cùng entity ID.

Ba cờ điều khiển có trách nhiệm rõ ràng:

- `in_scope`: solver có được phép trả lời về entity không;
- `depth_tier`: mức độ sâu mà retrieval được kỳ vọng hỗ trợ;
- `entry_status`: dữ liệu đang draft hay đã đủ điều kiện phục vụ.

`place_profile` giữ dữ liệu riêng của địa điểm như tọa độ và địa chỉ hiển thị.

### 5.4 `claim`

Một dòng là một thuộc tính nguyên tử, một nguồn và một thời điểm quan sát:

```text
entity          field             value
Chùa Thiên Mụ   nam_khoi_lap      1601
Hiện vật X      chieu_cao         250 cm
Địa điểm Y      gia_ve            150000 VND
```

Claim dùng cho câu hỏi “bao nhiêu”, giá trị hiện tại và canonical lookup. Dữ liệu
biến động dùng `valid_until` để solver biết khi nào không được khẳng định như mới.

### 5.5 `timeline_event`

Một dòng là một sự kiện có thời gian, actor/object và evidence:

```text
1601       Dựng chùa
1710       Đúc Đại Hồng Chung
1844–1846 Xây tháp Phước Duyên
```

Timeline dùng cho “khi nào”, “chuyện gì xảy ra”, sắp xếp chronology và lọc theo
thế kỷ/khoảng năm.

Claim và timeline có thể cùng phản ánh một năm nhưng không cùng trách nhiệm:

- `claim.nam_khoi_lap = 1601` trả một giá trị canonical;
- timeline mô tả ai làm gì, trong bối cảnh nào vào năm 1601.

Cả hai trỏ về cùng passage nếu cùng xuất phát từ một bằng chứng.

### 5.6 `relation`

Relation là cạnh knowledge graph giữa hai entity:

```text
Khải Tường Lâu ──IS_PART_OF────▶ Cung An Định
Cung An Định    ──LIEN_QUAN_DEN▶ Vua Khải Định
Hiện vật X      ──TRUNG_BAY_TAI▶ Cung An Định
```

Predicate là tập đóng theo ontology. Không cho extraction tự phát minh predicate
mới khi chưa qua review.

### 5.7 `narrative_section`

Narrative là văn bản do người biên soạn theo từng chủ đề:

```text
tong_quan
ten_goi
khoi_lap
vai_tro_lich_su
kien_truc
hien_vat
nhan_vat
bien_dong_hien_dai
tham_quan
```

Narrative không tương đương Community Report của Microsoft GraphRAG:

- Community Report là summary do model tạo cho một cụm graph;
- Narrative Section là nội dung domain được biên tập và review.

MVP dùng narrative cho câu hỏi giải thích chuyên sâu, không cần community
clustering/report generation.

## 6. Mutual indexing theo KAG

Mọi knowledge record phải truy ngược được về evidence:

```text
source_doc D1
    └── passage P17
          ├── hỗ trợ claim C4
          ├── hỗ trợ timeline event T8
          ├── hỗ trợ relation R3
          └── được dùng bởi narrative N2
```

Hệ thống hỗ trợ hai chiều:

- passage → các entity/claim/event/relation được trích;
- entity/claim/event/relation → supporting passages;
- narrative → các passages đã dùng để biên soạn;
- chat answer → evidence package của lượt trả lời.

Để một knowledge record có nhiều nguồn mà không nhân đôi bản ghi, kiến trúc bổ
sung hai bảng nối:

```text
relation_evidence
├── relation_id
└── passage_id

narrative_evidence
├── narrative_section_id
└── passage_id
```

`source_url` trong narrative chỉ phục vụ hiển thị/legacy. `narrative_evidence` mới
là liên kết provenance chính xác ở mức passage.

## 7. Query understanding

### 7.1 Contract chuẩn hóa

```json
{
  "raw_query": "Khải Tường Lâu xây khi nào?",
  "normalized_query": "khai tuong lau xay khi nao",
  "intent": "timeline",
  "entity_ids": ["entity-khai-tuong-lau"],
  "field_code": null,
  "time_range": null,
  "requested_relations": [],
  "needs_clarification": false
}
```

### 7.2 Entity resolution

Thứ tự resolve:

1. canonical name chính xác;
2. normalized alias chính xác;
3. alias xuất hiện trong câu;
4. fuzzy candidates;
5. hỏi lại nếu candidates gần nhau.

Entity ID đã chọn được dùng xuyên suốt query plan. Không tiếp tục truy vấn bằng
chuỗi tên đã được sửa.

### 7.3 Intent taxonomy

| Intent | Ví dụ | Operator chính |
|---|---|---|
| `overview` | “Giới thiệu Cung An Định” | Local Context/Dossier |
| `field` | “Cung có diện tích bao nhiêu?” | Exact claim |
| `timeline` | “Cung được xây dựng khi nào?” | Timeline |
| `relationship` | “Cung liên quan đến những vị vua nào?” | Graph |
| `section` | “Kiến trúc có gì đặc biệt?” | Narrative + text |
| `comparison` | “Cổng chính khác Khải Tường Lâu thế nào?” | Multi-operator |
| `open_text` | Câu hỏi không ánh xạ chính xác | Hybrid text |
| `out_of_scope` | Ngoài knowledge domain | Abstain |

Router ưu tiên luật và metadata. Qwen chỉ hỗ trợ phân loại trường hợp khó và phải
trả output theo schema, không tự thực hiện retrieval.

## 8. Query planner theo KAG

Planner không phải autonomous agent. Nó tạo một danh sách operator nhỏ từ intent
và entity đã resolve.

### 8.1 Exact operator

Đọc claim canonical cho giá vé, năm khởi lập, kích thước, xếp hạng và thông tin
tham quan. Không dùng vector search để đoán một giá trị đã có cấu trúc.

### 8.2 Timeline operator

Lọc event theo entity, event type và khoảng thời gian, sau đó lấy passage hỗ trợ.

### 8.3 Graph operator

Đi tối đa 1–2 hop qua predicate allowlist phù hợp intent. Câu hỏi nhân vật không
mở rộng qua cạnh địa điểm lân cận nếu không liên quan.

### 8.4 Section operator

Lấy narrative section đúng chủ đề và passages chứng minh cho section đó.

### 8.5 Text operator

Kết hợp:

- BM25 word cho từ khóa chính xác;
- BM25 n-gram cho truy vấn không dấu và lỗi gõ;
- dense vector cho paraphrase nếu eval chứng minh có lợi;
- RRF để hợp nhất thứ hạng;
- reranker để chọn evidence cuối.

### 8.6 Multi-operator plan

Ví dụ:

> Vì sao Khải Tường Lâu mang phong cách châu Âu và nó liên quan thế nào tới vua
> Khải Định?

```text
Resolve Khải Tường Lâu
  → Graph: IS_PART_OF Cung An Định
  → Graph: tìm relation tới vua Khải Định
  → Section: kiến trúc
  → Text: passage nói về phong cách châu Âu
  → Context Builder: hợp nhất và loại trùng evidence
```

## 9. Local Context và Entity Dossier

Đây là phần áp dụng Microsoft GraphRAG Local Search cho domain di sản.

Với entity trung tâm, Context Builder có thể lấy:

- thuộc tính canonical;
- timeline events quan trọng;
- entity lân cận và relations;
- narrative sections đúng intent;
- passages hỗ trợ.

Khi người dùng hỏi “hãy giúp tôi hiểu toàn bộ địa điểm”, backend dựng dossier
tạm thời:

```json
{
  "entity": {"id": "...", "name": "Cung An Định", "type": "place"},
  "canonical_claims": [],
  "key_timeline_events": [],
  "relevant_sections": [],
  "important_relations": [],
  "supporting_passages": []
}
```

Dossier không phải bảng mới và không phải bản copy toàn bộ database. Nó được dựng
theo query và token budget.

## 10. Evidence Context Builder

Mọi operator trả cùng một contract:

```json
{
  "evidence_id": "passage-uuid",
  "evidence_type": "timeline",
  "entity_id": "entity-uuid",
  "content": "Đầu năm 1919, công việc xây dựng hoàn tất...",
  "source_title": "Tên tài liệu",
  "source_url": "https://example.org/source",
  "tier": 1,
  "observed_at": "2026-09-15",
  "retrieval_score": 0.92,
  "reason": "supports timeline event 1917–1919"
}
```

Context Builder chịu trách nhiệm:

1. Loại evidence trùng.
2. Xác minh evidence thuộc đúng entity và corpus version.
3. Ưu tiên nguồn theo tier và độ mới phù hợp với loại dữ kiện.
4. Giữ nguồn mâu thuẫn nếu cần trình bày xung đột.
5. Chọn khoảng 3–8 evidence mạnh nhất trong token budget.
6. Cấp citation ID cho model.

Các retriever không tự tạo prompt riêng. Chúng chỉ trả candidate evidence.

## 11. Generation và grounding

### 11.1 Input cho Qwen3-4B

```text
Quy tắc:
- Chỉ sử dụng evidence bên dưới.
- Không bổ sung kiến thức bên ngoài.
- Mỗi khẳng định thực tế phải có citation.
- Nếu nguồn mâu thuẫn, trình bày rõ sự khác biệt.

[P17] ...
[P21] ...

Câu hỏi: ...
```

Generation mặc định deterministic, temperature `0–0.2`. Không bật reasoning dài
nếu eval chưa chứng minh nó cải thiện chất lượng.

### 11.2 Pre-generation gate

- entity đã resolve hoặc câu hỏi không cần entity;
- `in_scope = true`;
- `entry_status` cho phép phục vụ;
- query plan hợp lệ;
- evidence vượt ngưỡng của intent;
- dữ liệu biến động chưa hết hạn;
- evidence thuộc đúng corpus version.

### 11.3 Post-generation gate

- citation ID chỉ thuộc evidence package;
- mọi số và ngày tháng xuất hiện trong evidence;
- câu factual có citation hỗ trợ;
- mức chắc chắn không cao hơn nguồn;
- xung đột nguồn không bị che giấu;
- lỗi format chỉ retry một lần.

Response có đúng một trạng thái:

```text
answered   Có câu trả lời và citation hợp lệ
clarify    Cần người dùng làm rõ entity hoặc ý định
abstained  Evidence không đủ hoặc grounding thất bại
```

## 12. Luồng nhập dữ liệu

Không nhập theo kiểu hoàn thành từng bảng trên toàn dự án. Xử lý lần lượt từng
nguồn của một địa điểm:

```text
1. source_doc
2. passage
3. entity/alias phát hiện trong passage
4. claim có thể trích
5. timeline event có mốc rõ
6. relation giữa các entity
7. review structured knowledge
8. biên soạn narrative từ nhiều passages
9. publish corpus version
```

Một passage có thể hỗ trợ đồng thời nhiều projection:

```text
Passage P1
├── claim: nam_khoi_lap = 1601
├── timeline: năm 1601 dựng chùa
└── relation: chùa DUOC_TAO_BOI Nguyễn Hoàng
```

Đây không phải copy dữ liệu: text chỉ tồn tại ở P1; ba bản ghi còn lại phục vụ ba
loại truy vấn khác nhau.

## 13. MVP cho một địa điểm chuyên sâu

### Knowledge package

- nhiều source document có độ tin cậy khác nhau;
- passages theo section tự nhiên;
- một root place và các entity phụ có giá trị truy vấn;
- aliases đã review;
- claims cho dữ kiện chính xác;
- timeline cho các mốc quan trọng;
- relations có supporting passages;
- narrative sections cho các chủ đề cần giải thích dài.

Không đặt quota cứng. Chỉ tạo entity và knowledge record khi nội dung thật sự tồn
tại và có ích cho câu hỏi.

### Ba lớp kiểm thử

1. **Retrieval test:** query → expected entity, intent, operator và passage.
2. **Generation test:** evidence đúng cố định → Qwen answer, faithfulness, citation.
3. **End-to-end test:** resolver → planner → retrieval → context → Qwen → gate.

Chỉ mở rộng sang địa điểm tiếp theo khi pipeline không chứa logic hard-code dành
riêng cho địa điểm pilot.

## 14. Ánh xạ vào repository

| Trách nhiệm | Module sở hữu |
|---|---|
| Query normalization | `apps/backend/core/textutil.py` |
| Entity resolution | `apps/backend/services/kg.py` |
| Intent router/query planner | module riêng trong `apps/backend/core/` |
| BM25/ngram/RRF | `apps/backend/core/retriever.py` |
| Graph retrieval | `apps/backend/core/kg.py` + PostgreSQL repository |
| Local Context/Entity Dossier | service context riêng hoặc `apps/backend/core/rag.py` |
| Evidence Context Builder | `apps/backend/core/rag.py` |
| Prompt | `apps/backend/core/prompt.py` |
| Qwen inference | `apps/backend/core/llm.py` |
| API orchestration | service chat, endpoint chỉ validate/serialize |
| Provenance | PostgreSQL + SQLAlchemy models |
| Evaluation | `pipelines/evaluation/` + regression tests |

Không đặt SQL, retrieval, planning, prompt và citation validation cùng trong
endpoint `/api/chat`.

## 15. Những phần không áp dụng từ references ở MVP

Từ Microsoft GraphRAG:

- community detection bằng Leiden;
- community reports;
- Global Search map-reduce;
- DRIFT search;
- tự động extraction và publish hoàn toàn bằng LLM.

Từ KAG:

- OpenSPG/TuGraph runtime;
- logical-form language đầy đủ;
- solver agent nhiều vòng;
- tất cả loại index như AtomicQuery, KnowledgeUnit và Outline;
- graph traversal không giới hạn.

Những phần này chỉ được xem xét khi câu hỏi và eval thực tế chứng minh kiến trúc
hiện tại không đáp ứng.

## 16. Tiêu chí hoàn thành

- Một địa điểm được mô hình hóa đủ sâu và có provenance.
- Entity, claim, event, relation và narrative truy ngược được về passage.
- Tên chuẩn, không dấu và alias resolve về cùng entity.
- Claim lookup không phụ thuộc LLM suy đoán.
- Timeline query lọc và sắp xếp đúng theo năm.
- Graph query đi đúng relation path tối đa 2 hop.
- Câu hỏi chuyên đề lấy đúng narrative và supporting passages.
- Câu hỏi tổng quan dựng được Local Context/Entity Dossier trong token budget.
- Qwen3-4B chỉ nhận evidence đã được chọn.
- Mọi câu factual có citation hợp lệ.
- Thiếu evidence thì clarify hoặc abstain.
- Evaluation phân biệt được lỗi retrieval và lỗi generation.

Kiến trúc chốt:

> **Microsoft GraphRAG-style knowledge indexing và Local Context → KAG-style
> query planner và retrieval operators → HeritageGraph Evidence Builder →
> Qwen3-4B generation → grounding gate.**
