# Roadmap chatbot GraphRAG cho 30 địa điểm lõi

Ngày lập: 15/09/2026.

## 1. Mục tiêu

Xây chatbot tiếng Việt chạy local, dùng Qwen3-4B để trả lời có nguồn về 30 địa
điểm lõi tại Huế, Đà Nẵng và Quảng Nam. Mỗi địa điểm được đào sâu qua các thực
thể liên quan như lễ hội, nhân vật, hiện vật, món ăn và làng nghề.

Chatbot phải:

- nhận diện đúng địa điểm và tên gọi thay thế;
- trả lời dữ kiện chính xác từ dữ liệu có cấu trúc;
- trả lời câu hỏi mô tả từ các passage có nguồn;
- đi qua quan hệ graph cho câu hỏi liên kết nhiều thực thể;
- hỏi lại khi tên mơ hồ;
- từ chối khi không có đủ bằng chứng;
- gắn citation truy vết được cho mọi khẳng định thực tế.

Phạm vi này là **30 địa điểm gốc**, không phải chỉ 30 entity. Tổng số entity sẽ
tăng theo chiều sâu nội dung.

```text
30 place lõi
  ├── festival
  ├── person
  ├── artifact
  ├── dish
  ├── craft
  └── place liên quan
```

## 2. Nguyên tắc kiến trúc

1. PostgreSQL là nguồn sự thật cho entity, evidence, claim, timeline và relation.
2. LLM không tự tìm sự thật trong toàn database; backend chọn evidence trước.
3. Dữ kiện có cấu trúc được ưu tiên hơn việc để LLM suy ra từ văn bản.
4. BM25, n-gram, vector và graph là các kênh retrieval, không phải nguồn sự thật.
5. Qwen3-4B dùng để hiểu yêu cầu và diễn đạt, không tự sinh SQL production.
6. Mỗi kết luận phải truy ngược được tới passage hoặc nguồn đã duyệt.
7. Thêm kiến thức bằng ingestion/RAG; chỉ fine-tune để sửa hành vi của model.
8. Giữ backend ở dạng modular monolith; chưa cần Neo4j, microservice hay agent
   framework.

## 3. Kiến trúc đích

```text
Người dùng
    ↓
FastAPI /api/chat
    ↓
Query normalizer
    ↓
Entity resolver ── mơ hồ ──→ Clarification response
    ↓
Intent router
    ├── field          → claim canonical
    ├── timeline       → timeline_event
    ├── festival       → festival + festival_instance
    ├── overview       → narrative + passage
    ├── relationship   → relation + graph traversal
    └── open_text      → BM25/ngram/vector
    ↓
Evidence builder + reranker
    ↓
Qwen3-4B generation
    ↓
Grounding/citation gate
    ├── pass → answer + citations
    ├── ambiguous → clarification
    └── fail → abstain
```

### Contract evidence thống nhất

Mọi retriever nên trả cùng một cấu trúc nội bộ:

```json
{
  "evidence_id": "passage-uuid",
  "evidence_type": "claim",
  "entity_id": "entity-uuid",
  "content": "Nội dung đủ để hỗ trợ một khẳng định",
  "source_title": "Tên nguồn",
  "source_url": "https://example.org/source",
  "tier": 1,
  "observed_at": "2026-09-15",
  "score": 0.92
}
```

LLM chỉ được sử dụng và citation các `evidence_id` có trong request hiện tại.

## 4. Hiện trạng có thể tái sử dụng

Không xây lại những phần repository đã có:

- `backend/core/textutil.py`: chuẩn hóa tiếng Việt, bỏ dấu và n-gram;
- `backend/core/retriever.py`: BM25 word, BM25 n-gram và RRF;
- `backend/core/kg.py`: graph deterministic;
- `backend/core/rag.py`: chọn context và các cổng từ chối trước generation;
- `backend/core/prompt.py`: prompt cho câu trả lời có nguồn;
- `backend/core/llm.py`: inference local qua llama.cpp/GGUF;
- `backend/services/kg.py`: entity/location resolution từ PostgreSQL;
- `eval/eval_attribution.py`: phân loại lỗi retrieval và ngoài phạm vi.

Các thành phần cần bổ sung hoặc nâng cấp:

- intent router có contract rõ ràng;
- các structured retriever cho claim, timeline và festival;
- evidence contract dùng chung;
- retrieval từ PostgreSQL theo entity ID;
- dense retrieval nếu spike chứng minh có lợi;
- post-generation citation/grounding gate;
- eval set phủ đủ 30 địa điểm và các entity mở rộng.

## 5. Giai đoạn 0 — Chốt phạm vi và tiêu chuẩn chất lượng

### Công việc

- [ ] Chốt danh sách đúng 30 địa điểm lõi, mỗi địa điểm có `slug` ổn định.
- [ ] Gán `depth_tier` và người chịu trách nhiệm nội dung cho từng địa điểm.
- [ ] Chốt loại entity: `place`, `festival`, `dish`, `artifact`, `person`, `craft`.
- [ ] Chốt predicate tối thiểu và chiều truy vấn của từng predicate.
- [ ] Lập ma trận nội dung cho mỗi địa điểm: tổng quan, lịch sử, kiến trúc, hiện
      vật, nhân vật, lễ hội, món ăn, tham quan và nguồn.
- [ ] Chốt taxonomy câu hỏi: overview, field, timeline, festival, relationship,
      comparison, open text và out of domain.
- [ ] Ghi baseline retrieval và generation hiện tại trước khi thay đổi pipeline.

### Sản phẩm

- Danh sách 30 slug chính thức.
- Từ điển entity type, predicate, field và section.
- Ma trận coverage cho 30 địa điểm.
- Báo cáo baseline có corpus/model/retrieval version.

### Cổng hoàn thành

Không còn địa điểm chưa rõ tên chuẩn, khu vực hoặc phạm vi nội dung. Mọi loại câu
hỏi mục tiêu đều có nơi lưu dữ liệu và đường retrieval dự kiến.

## 6. Giai đoạn 1 — Dựng PostgreSQL làm nguồn sự thật

### Công việc

- [ ] Chuyển schema đã chốt thành Alembic migration thay vì chạy SQL thủ công
      trên production.
- [ ] Tạo các bảng nguồn và tri thức lõi: `source_doc`, `passage`, `entity`,
      `entity_alias`, `claim`, `timeline_event`, `narrative_section`, `relation`.
- [ ] Tạo bảng chuyên biệt cho `festival` và `festival_instance`.
- [ ] Thêm index cho alias, entity, relation, passage FTS và corpus version.
- [ ] Chốt embedding model trước khi cố định dimension vector.
- [ ] Tạo dữ liệu tham chiếu cho entity type, field, section, predicate và event.
- [ ] Viết test migration trên database trống.
- [ ] Viết test cho FK, unique và các CHECK quan trọng.

### Cổng hoàn thành

- Database sạch migrate từ zero thành công.
- Restart không mất dữ liệu.
- Có thể backup và restore database thử nghiệm.
- Một source có thể truy từ document → passage → claim/relation.

## 7. Giai đoạn 2 — Xây corpus sâu cho 30 địa điểm

### Quy trình dữ liệu

```text
Nguồn đã chọn
    → source_doc
    → chunk thành passage
    → entity + alias
    → claim / timeline / narrative
    → relation
    → review
    → publish corpus version
```

### Công việc

- [ ] Import theo khóa ổn định và bảo đảm chạy lại không tạo bản ghi trùng.
- [ ] Mỗi địa điểm có ít nhất một nguồn tổng quan đáng tin cậy.
- [ ] Thu thập nguồn chính thức riêng cho dữ liệu biến động như giá vé, giờ mở
      cửa và lịch lễ hội.
- [ ] Tạo alias cho tên chính thức, Hán Việt, dân gian, tiếng Anh, lịch sử và lỗi
      gõ phổ biến.
- [ ] Tạo entity riêng cho người, lễ hội, món ăn, hiện vật và làng nghề; không
      nhét tất cả thành text của place.
- [ ] Chỉ tạo relation khi có passage hoặc URL chứng minh.
- [ ] Tách claim mâu thuẫn theo nguồn; không ghi đè để tạo một sự thật giả.
- [ ] Gắn `corpus_version` cho mỗi lần publish dữ liệu.
- [ ] Sau mỗi batch 5 địa điểm, dựng lại graph và chạy regression retrieval.

### Mức phủ đề xuất cho mỗi địa điểm lõi

- một section tổng quan đã review;
- một section tham quan đã review hoặc đánh dấu chưa có dữ liệu;
- các mốc timeline quan trọng có nguồn;
- alias tên thường gặp;
- các relation chính tới entity phụ;
- passage đủ để chứng minh từng claim được chatbot sử dụng.

Không đặt quota cứng cho số lễ hội, món ăn hay nhân vật vì mức độ phong phú của
mỗi địa điểm khác nhau. Dùng coverage theo nội dung thật, không tạo entity để đủ
số lượng.

### Cổng hoàn thành

- 30/30 địa điểm có tổng quan và nguồn.
- Không có relation được publish mà không có provenance.
- Không có entity phụ mồ côi ngoài trường hợp được chủ ý ghi nhận.
- Import lần hai không làm thay đổi số bản ghi.

## 8. Giai đoạn 3 — Entity resolver và intent router

### Output chuẩn hóa

```json
{
  "normalized_query": "le hoi tai dien hon chen",
  "intent": "festival",
  "entity_ids": ["entity-uuid"],
  "field_code": null,
  "time_range": null,
  "needs_clarification": false
}
```

### Công việc

- [ ] Resolve theo thứ tự exact slug/name → normalized alias → fuzzy candidate.
- [ ] Dùng `entity_id` xuyên suốt pipeline, không dùng tên hiển thị làm khóa.
- [ ] Dựa trên top-1 score và margin để quyết định resolve hoặc hỏi lại.
- [ ] Chuẩn hóa từ đồng nghĩa về field, ví dụ “vé vào cửa” → `gia_ve`.
- [ ] Trích xuất mốc năm, khoảng thời gian và từ “hiện nay”.
- [ ] Router ưu tiên luật/template cho intent rõ; chỉ dùng Qwen3-4B hỗ trợ khi
      câu hỏi không khớp luật.
- [ ] Nếu dùng model cho router, ép output bằng JSON Schema và temperature thấp.
- [ ] Log raw query, candidates, lựa chọn và outcome để cải thiện resolver.

### Cổng hoàn thành

- Tên có dấu, không dấu và alias hợp lệ đi tới cùng entity.
- Alias trùng trả yêu cầu làm rõ thay vì chọn ngẫu nhiên.
- Intent router chọn đúng retriever trên bộ test đã gán nhãn.

## 9. Giai đoạn 4 — Retrieval theo nhiều đường chuyên biệt

### 4.1 Structured retrieval

- `field` → canonical claim;
- `timeline` → timeline event theo entity và khoảng năm;
- `festival` → festival invariant + instance của năm được hỏi;
- `relationship` → graph traversal có giới hạn;
- `overview` → narrative đã review và passage hỗ trợ.

Structured retrieval phải được triển khai trước dense retrieval vì nó cho kết
quả xác định đối với giá vé, ngày tháng, số liệu và trạng thái hiện tại.

### 4.2 Open-text retrieval

- [ ] Giữ BM25 word và BM25 n-gram hiện có.
- [ ] Lọc candidate theo entity đã resolve khi câu hỏi gọi tên rõ địa điểm.
- [ ] Thử dense embedding trên bộ paraphrase; chưa đưa production trước khi đo.
- [ ] Nếu dense có lợi, hợp nhất word/ngram/dense bằng RRF.
- [ ] Dùng graph để mở rộng tối đa 1–2 hop, có predicate allowlist theo intent.
- [ ] Rerank và chỉ đưa khoảng 3–8 evidence tốt nhất cho Qwen3-4B.
- [ ] Endpoint trace phải giải thích evidence đến từ kênh nào và vì sao được giữ.

### Cổng hoàn thành

- Structured query trả đúng dữ kiện mà không cần LLM suy đoán.
- Open-text retrieval giữ được passage hỗ trợ trong top-k.
- Graph expansion không kéo entity xa chủ đề vào context.
- OOD query không đi qua cổng chỉ vì dense score cao.

## 10. Giai đoạn 5 — Generation bằng Qwen3-4B

### Cấu hình ban đầu

- Qwen3-4B Instruct, quantization phù hợp với máy triển khai;
- temperature `0–0.2`;
- context chỉ chứa evidence đã chọn;
- câu trả lời ngắn, tiếng Việt, citation theo `evidence_id`;
- chưa fine-tune ở vòng đầu.

### Quy tắc prompt

1. Chỉ dùng evidence được cung cấp.
2. Mỗi con số, ngày tháng và khẳng định thực tế phải có citation.
3. Không biến giả thuyết, truyền thuyết hoặc nguồn hạng thấp thành sự thật chắc chắn.
4. Khi nguồn mâu thuẫn, trình bày mâu thuẫn thay vì tự chọn.
5. Khi evidence thiếu, chỉ trả lời phần có bằng chứng hoặc từ chối.
6. Không tạo URL, entity hoặc citation mới.

### Hai chế độ trả lời

- **Template:** field lookup, lịch, địa chỉ, yêu cầu làm rõ và từ chối.
- **LLM synthesis:** tổng quan, giải thích, so sánh và câu hỏi quan hệ.

### Cổng hoàn thành

- Model không cần biết toàn bộ 30 địa điểm trong trọng số.
- Cùng input và evidence cho kết quả ổn định ở mức chấp nhận được.
- Câu trả lời không citation bị chặn trước khi gửi cho người dùng.

## 11. Giai đoạn 6 — Grounding và citation gate

### Pre-generation gate

- entity đã resolve hoặc đã xác định câu hỏi không cần entity;
- retrieval vượt ngưỡng phù hợp với từng intent;
- dữ liệu volatile chưa hết hạn;
- evidence thuộc đúng entity và corpus version.

### Post-generation gate

- [ ] Parse toàn bộ citation do model sinh.
- [ ] Từ chối citation ID không nằm trong evidence request.
- [ ] Kiểm tra số, ngày tháng và tên riêng xuất hiện trong evidence.
- [ ] Kiểm tra mỗi câu factual có ít nhất một citation hỗ trợ.
- [ ] Retry tối đa một lần khi format sai hoặc thiếu citation.
- [ ] Nếu vẫn fail, trả abstain an toàn; không đưa bản nháp lỗi ra frontend.

### Cổng hoàn thành

Mỗi câu trả lời production thuộc đúng một trạng thái: `answered`, `clarify` hoặc
`abstained`. Trạng thái `answered` luôn có citation hợp lệ và lưu được trace.

## 12. Giai đoạn 7 — Bộ đánh giá và ngưỡng phát hành

### Bộ câu hỏi vàng

Mỗi địa điểm phải có câu hỏi ở các nhóm phù hợp:

- gọi đúng tên, không dấu và alias;
- tổng quan;
- dữ kiện/field;
- timeline;
- lễ hội, người, món ăn hoặc hiện vật liên quan;
- quan hệ 1 hop và 2 hop;
- paraphrase;
- tiền đề sai hoặc entity mơ hồ;
- không có dữ liệu;
- ngoài phạm vi.

Không bắt buộc mỗi địa điểm có mọi nhóm nếu nội dung thật không tồn tại. Bộ gold
phải chứa hard negative giữa những địa điểm hoặc entity có tên gần giống nhau.

### Metric tách theo tầng

| Tầng | Metric |
|---|---|
| Resolver | entity accuracy, clarify precision/recall |
| Router | intent accuracy |
| Retrieval | Recall@1, Recall@3, MRR |
| Generation | answer correctness, faithfulness |
| Citation | citation precision, citation coverage |
| Safety | abstention accuracy, OOD leakage |
| Vận hành | p50/p95 latency, token count, error rate |

### Ngưỡng phát hành đề xuất

- entity resolution ≥ 95% trên alias đã biết;
- retrieval Recall@3 ≥ 95% cho câu hỏi trong phạm vi;
- citation precision ≥ 95%;
- citation coverage ≥ 90%;
- OOD refusal ≥ 90%;
- không có lỗi nghiêm trọng về nhầm entity hoặc bịa số liệu trong test release.

Mỗi report phải lưu corpus version, model, prompt version, retrieval config và Git
revision. Không gộp lỗi retrieval và lỗi generation thành một con số duy nhất.

## 13. Giai đoạn 8 — Fine-tune và tối ưu sau MVP

Chỉ fine-tune Qwen3-4B khi retrieval đã ổn định và trace chứng minh lỗi nằm ở
generation.

### Fine-tune khi

- context đúng nhưng model thường xuyên bỏ citation;
- model thêm chi tiết không có trong evidence;
- cách từ chối hoặc hỏi lại không ổn định;
- model trình bày nguồn mâu thuẫn sai;
- format đầu ra thường xuyên không tuân thủ dù đã constrained decoding.

### Không fine-tune khi

- retriever lấy sai passage;
- database thiếu dữ kiện;
- alias hoặc relation sai;
- passage quá dài hoặc chunk sai;
- thông tin mới chưa được ingestion.

Sau khi đạt chất lượng, mới tối ưu cache, batch embedding, quantization, prompt
length và latency. Chỉ cân nhắc model 7B–14B cho các truy vấn so sánh/suy luận sâu
nếu eval cho thấy 4B là nút thắt thật sự.

## 14. Thứ tự triển khai thực tế

```text
M0  Chốt 30 địa điểm + ontology + baseline
 ↓
M1  PostgreSQL migration + provenance
 ↓
M2  Import sâu 5 địa điểm pilot
 ↓
M3  Resolver + router + structured retrieval
 ↓
M4  Evidence contract + Qwen3-4B + citation gate
 ↓
M5  Eval pilot và sửa lỗi theo đúng tầng
 ↓
M6  Mở rộng lần lượt đủ 30 địa điểm
 ↓
M7  Dense retrieval nếu spike chứng minh có lợi
 ↓
M8  Fine-tune/đổi model chỉ khi generation là nút thắt
```

Không nhập đồng thời cả 30 địa điểm trước khi pipeline chạy đúng. Nên dùng 5 địa
điểm pilot có độ phức tạp khác nhau: một địa điểm nhiều nhân vật, một địa điểm
nhiều lễ hội, một địa điểm nhiều hiện vật, một địa điểm có dữ liệu tham quan biến
động và một địa điểm có tên/alias dễ nhầm.

## 15. Definition of Done cho MVP

- [ ] 30 địa điểm lõi đã publish, mỗi địa điểm có nguồn tổng quan.
- [ ] Entity phụ và relation quan trọng đã được tách và truy vết nguồn.
- [ ] Resolver xử lý tên chuẩn, không dấu, alias và trường hợp mơ hồ.
- [ ] Router chọn đúng structured hoặc open-text retrieval.
- [ ] Câu hỏi field/timeline/festival không phụ thuộc vào LLM suy đoán.
- [ ] Qwen3-4B chỉ nhận evidence đã được chọn.
- [ ] Mọi câu trả lời factual có citation hợp lệ.
- [ ] Thiếu evidence thì hỏi lại hoặc từ chối.
- [ ] Bộ eval chạy tự động và đạt ngưỡng phát hành.
- [ ] Trace đủ để xác định lỗi thuộc dữ liệu, resolver, retrieval hay generation.

Khi hoàn thành các tiêu chí này, chatbot đã đủ chuẩn hóa cho phạm vi 30 địa điểm
đào sâu. 3D tour, recommendation và model lớn hơn là các nhánh nâng cấp độc lập,
không phải điều kiện để lõi hỏi đáp hoạt động đúng.
