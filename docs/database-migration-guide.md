# Hướng dẫn thêm PostgreSQL và nối chatbot

Tài liệu này là checklist triển khai theo thứ tự:

1. Chốt schema tối thiểu.
2. Thêm PostgreSQL vào Docker Compose.
3. Thêm SQLAlchemy và Alembic.
4. Import corpus và dữ kiện đã xác minh.
5. Nối chatbot với database.

Mục tiêu đầu tiên là giải quyết đúng truy vấn tên địa danh và nguồn dữ liệu, ví dụ:

```text
"lăng an định ở đâu?"
-> alias/ứng viên
-> Cung An Định
-> địa chỉ đã xác minh
-> câu trả lời kèm nguồn
```

## 0. Nguyên tắc trước khi code

- PostgreSQL là nguồn chuẩn cho dữ liệu entity, alias, địa chỉ và provenance.
- Corpus file hiện tại vẫn giữ lại để đối chiếu, huấn luyện và backup; không xóa ngay.
- LLM không được tự tạo tên chuẩn, địa chỉ hoặc URL nguồn.
- Fuzzy matching chỉ tạo ứng viên; dữ liệu chính thức phải qua bước xác minh.
- Migration phải được quản lý bằng Alembic, không dùng `metadata.create_all()` trong production.
- Không đưa dữ liệu cá nhân hoặc mật khẩu vào Git; corpus công khai chỉ commit khi giấy phép cho phép.

## 1. Chốt schema tối thiểu

### 1.1. Phạm vi migration đầu tiên

Chỉ tạo các bảng cần cho truy vấn có nguồn:

```text
document
passage
entity
entity_alias
place_location
```

Các bảng `site`, `scene`, `model_asset`, `story`, `narration` và những bảng 3D có thể để migration sau. Không nên tạo toàn bộ schema 3D trước khi có nhu cầu sử dụng.

### 1.2. Loại bỏ dữ liệu alias trùng

Trong `entity`, bỏ cột:

```dbml
aliases text[]
```

Chỉ dùng bảng `entity_alias`:

```text
entity
  id
  name
  normalized_name
  type
  source_document_id
  source_passage_id

entity_alias
  id
  entity_id
  alias
  normalized_alias
  alias_type
  confidence
  source_document_id
  source_passage_id
```

`normalized_alias` nên được chuẩn hóa bằng code dùng chung với truy vấn:

- trim khoảng trắng;
- chuyển lowercase;
- chuẩn hóa Unicode;
- có thể thêm bản không dấu cho tìm kiếm, nhưng không thay thế giá trị alias gốc;
- không tự bỏ các từ có ý nghĩa như `cung`, `lăng`, `chùa` nếu chúng cần phân biệt thực thể.

### 1.3. Cho phép nhiều địa danh cùng alias

Không đặt unique toàn cục trên `normalized_alias`. Một alias có thể trỏ tới nhiều entity, ví dụ các địa danh có tên trùng ở nhiều địa phương.

Nên dùng:

```sql
UNIQUE (entity_id, normalized_alias)
```

và index tìm kiếm:

```sql
CREATE INDEX ix_entity_alias_normalized
ON entity_alias (normalized_alias);
```

Khi có nhiều ứng viên, entity resolver phải xếp hạng theo:

1. Tên chuẩn khớp chính xác.
2. Alias đã xác minh.
3. Khu vực/địa phương xuất hiện trong câu hỏi.
4. Loại entity phù hợp với intent.
5. Confidence và số lượng nguồn hỗ trợ.

Không tự chọn nếu điểm hai ứng viên quá gần nhau.

### 1.4. Bảng địa chỉ có nguồn và thời gian hiệu lực

Thêm bảng `place_location` thay vì đặt một cột `address` trực tiếp trong `entity`:

```text
place_location
  id UUID primary key
  entity_id UUID not null references entity(id)
  address text not null
  ward text
  district text
  province text not null
  latitude numeric(9,6)
  longitude numeric(9,6)
  valid_from date
  valid_to date
  source_url text not null
  source_title text
  source_sentence text not null
  verification_status text not null default 'pending'
  verified_at timestamptz
  created_at timestamptz not null default now()
```

Ràng buộc đề xuất:

```sql
CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90)
CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
CHECK (verification_status IN ('pending', 'verified', 'rejected', 'withdrawn'))
```

Chỉ bản ghi `verified` mới được dùng để trả lời khẳng định. `valid_from` và `valid_to` dùng để phân biệt địa chỉ hiện tại với tên đơn vị hành chính lịch sử.

### 1.5. Cập nhật `schema_v2.dbml`

Sau khi chốt, sửa DBML theo các điểm sau:

- xóa `entity.aliases`;
- thêm `entity.normalized_name`;
- đổi index alias thành `(entity_id, normalized_alias) [unique]`;
- thêm `place_location`;
- giữ `source_url` và `source_sentence` bắt buộc cho địa chỉ;
- không cố định vector nếu chưa chọn embedding model;
- ghi rõ các CHECK sẽ nằm trong Alembic.

**Điều kiện hoàn thành bước 1:** DBML không có hai nơi lưu alias; có bảng địa chỉ có nguồn; quy tắc alias trùng tên đã được quyết định.

## 2. Thêm PostgreSQL vào Docker Compose

Thêm service database vào `docker-compose.yml`:

```yaml
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-heritagegraph}
      POSTGRES_USER: ${POSTGRES_USER:-heritagegraph}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - heritage-network

  backend:
    environment:
      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is required}
    depends_on:
      db:
        condition: service_healthy
      llm:
        condition: service_started
```

Đây là phần cần ghép vào cấu hình hiện có, không tạo service `backend` thứ hai. Giữ nguyên build, ports, biến LLM và healthcheck của backend; chuyển `depends_on` hiện tại sang dạng mapping trên.

Khai báo volume ở cuối file:

```yaml
volumes:
  postgres_data:
```

Trong `.env.docker.example`, thêm:

```dotenv
POSTGRES_DB=heritagegraph
POSTGRES_USER=heritagegraph
POSTGRES_PASSWORD=change-this-in-local-env
```

Compose tạo `DATABASE_URL` cho container backend/migration từ các biến
`POSTGRES_*`, hostname service `db` và cổng nội bộ `5432`. Cách này tránh dùng
nhầm URL chạy ngoài Docker như `localhost:5433` bên trong container. Nếu mật khẩu
có ký tự dành riêng của URL, phải percent-encode giá trị dùng trong URL.

Không commit file `.env` thật. Không cần expose `5432` ra host khi backend là consumer duy nhất. Nếu cần debug local, expose tạm thời qua biến môi trường và không dùng trong môi trường public.

Ví dụ lệnh dưới dùng file môi trường riêng `.env.docker` đã điền thông tin local. Mật khẩu trong URL phải được percent-encode nếu có ký tự đặc biệt và phải khớp mật khẩu PostgreSQL. Khi chạy backend ngoài Docker, thay hostname `db` bằng địa chỉ host/cổng đã publish. `docker compose config` hiển thị secret đã nội suy, không chia sẻ nguyên output.

Kiểm tra service:

```bash
docker compose --env-file .env.docker config
docker compose --env-file .env.docker up -d db
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs db
```

**Điều kiện hoàn thành bước 2:** database healthy, volume giữ dữ liệu sau restart và backend resolve được hostname `db`.

## 3. Thêm SQLAlchemy và Alembic

### 3.1. Dependency

Chọn một nơi quản lý dependency thống nhất với backend hiện tại. Các package cần có:

```text
SQLAlchemy
Alembic
psycopg[binary]
```

Không thêm package bằng tay vào container nếu dependency không được ghi vào file quản lý của project.

### 3.2. Cấu trúc thư mục đề xuất

```text
backend/
  db/
    __init__.py
    base.py
    session.py
    models.py
    repositories/
      entity_repository.py
      location_repository.py
  migrations/
    env.py
    script.py.mako
    versions/
```

Nếu dùng Alembic ở root thì giữ `alembic.ini` ở root và trỏ tới model metadata của backend.

### 3.3. Model tối thiểu

Các model phải biểu diễn:

- UUID primary key;
- foreign key đến document/passage/entity;
- index `normalized_name` và `normalized_alias`;
- unique `(entity_id, normalized_alias)`;
- CHECK của `place_location`;
- timestamp UTC;
- trạng thái xác minh.

Không đưa logic fuzzy matching vào SQLAlchemy model. Logic resolver nằm trong service/repository layer.

### 3.4. Migration

Chạy từ root trong môi trường Python đã cài dependency. Chỉ chạy `init` một lần nếu chưa có thư mục migrations:

```bash
alembic init backend/migrations
```

Trước khi autogenerate, cấu hình `env.py` đọc `DATABASE_URL`, import models và gán `target_metadata = Base.metadata`. Dùng URL truy cập được từ nơi chạy Alembic; hostname `db` chỉ hoạt động trong mạng Compose. Không hardcode mật khẩu vào `alembic.ini`.

```bash
alembic revision --autogenerate -m "create heritage knowledge tables"
alembic upgrade head
```

Trong Docker, service `migrate` chạy `python -m backend.db.migrate`. Wrapper này
chạy Alembic bình thường với database mới. Với volume được tạo trước khi dự án
dùng Alembic, wrapper chỉ stamp baseline khi tập bảng và view khớp đầy đủ schema
legacy đã biết; schema thiếu hoặc có bảng lạ sẽ bị từ chối thay vì stamp mù. Sau
đó revision repair tạo `place_location` nếu volume legacy chưa có bảng này.

Review migration bằng tay trước khi chạy. Kiểm tra đặc biệt:

- migration có vô tình drop `aliases` trước khi chuyển dữ liệu không;
- foreign key có đúng thứ tự tạo bảng không;
- index có dùng đúng tên không;
- default JSON/UUID có hợp lệ trên PostgreSQL không;
- CHECK không làm mất dữ liệu hợp lệ hiện có.

Kiểm tra trạng thái:

```bash
alembic current
alembic history
```

### 3.5. Quy tắc migration dữ liệu alias

Nếu đã có dữ liệu trong `entity.aliases`:

1. Tạo `entity_alias`.
2. Đọc từng alias trong array.
3. Chuẩn hóa và insert với `ON CONFLICT (entity_id, normalized_alias) DO NOTHING`.
4. Kiểm đếm alias trước và sau.
5. Chỉ sau khi kiểm tra thành công mới drop `entity.aliases` trong migration tiếp theo.

Không drop cột cũ và tạo cột mới trong cùng một bước nếu chưa có backup và kiểm thử chuyển đổi.

**Điều kiện hoàn thành bước 3:** `alembic upgrade head` chạy được trên database trống và database có dữ liệu thử; rollback/restore đã được kiểm tra.

## 4. Import corpus và dữ kiện đã xác minh

### 4.1. Thứ tự import

```text
document
  -> passage
  -> entity
  -> entity_alias
  -> place_location
```

Import theo thứ tự foreign key. Bảng `relation` chỉ import ở migration sau nếu chưa nằm trong phạm vi tối thiểu. Dùng transaction theo document hoặc batch nhỏ để một document lỗi không làm hỏng toàn bộ lần import.

### 4.2. Khóa ổn định và chống trùng

Không dùng tên hiển thị làm primary key. Giữ UUID của entity ổn định khi đổi tên hoặc cập nhật corpus. Dùng định danh nguồn ổn định hoặc bảng ánh xạ nguồn để nhận diện bản ghi; tên chuẩn hóa chỉ tạo ứng viên, không đủ để gộp hai địa danh. Document/passage cần khóa phiên bản hoặc content hash riêng để giữ được nội dung nguồn cũ khi cập nhật.

Importer phải idempotent: chạy hai lần cho cùng input không tạo thêm entity, alias hoặc passage trùng.

### 4.3. Quy tắc dữ liệu Cung An Định

Dữ liệu mẫu chỉ được import sau khi kiểm tra nguồn chính thống:

```text
entity.name: Cung An Định
entity.type: place
entity_alias.alias: Lăng An Định
entity_alias.alias_type: typo (gợi ý sửa tên, không phải tên chính thức)
place_location.verification_status: verified chỉ khi nguồn xác nhận
place_location.source_url: URL nguồn thực tế
place_location.source_sentence: câu nguồn chứa địa chỉ
```

Không dùng URL Wikipedia giả, URL không tồn tại hoặc câu do LLM viết làm `source_url`/`source_sentence`.

### 4.4. Kiểm tra sau import

Phải kiểm tra:

- entity không có source khi được dùng làm factual answer;
- alias không có entity cha;
- passage không có document;
- location chưa verified nhưng bị chọn làm answer;
- quote không xuất hiện trong passage/transcript tương ứng;
- duplicate normalized alias trên cùng entity;
- số lượng import khớp số lượng nguồn.

Tái tạo index BM25 và graph sau import. Ghi lại `corpus_version` và thời điểm build.

**Điều kiện hoàn thành bước 4:** dữ liệu import lặp lại an toàn; các location dùng để trả lời đều có URL và câu nguồn; các bản ghi lỗi bị từ chối hoặc đưa vào review.

## 5. Nối chatbot vào database

### 5.1. Không thay retrieval hiện tại ngay lập tức

Giữ pipeline hiện tại làm fallback:

```text
database lookup -> nếu có entity/location verified thì dùng kết quả
BM25 + graph -> nếu cần mô tả hoặc database chưa có dữ kiện
LLM -> chỉ diễn đạt evidence đã chọn
```

Không xóa `backend/core/fuzzy_match.py` hoặc `backend/core/rag.py` khi database mới chỉ được triển khai.

### 5.2. Luồng truy vấn mới

```text
message
  -> normalize query
  -> detect intent
  -> resolve entity từ entity.name/entity_alias
  -> nếu intent=location:
       lấy place_location có status=verified
       lọc valid_from <= ngày hỏi <= valid_to theo quy ước biên đã chốt
  -> nếu có một kết quả đủ tin cậy:
       trả template + source
  -> nếu có nhiều kết quả:
       trả suggestions, không gọi LLM
  -> nếu không có location:
       BM25/graph retrieval
       nếu evidence không đủ: từ chối hoặc nói thiếu nguồn
```

### 5.3. Repository API đề xuất

`valid_to IS NULL` không đủ chứng minh dữ liệu còn hiện hành: bản ghi có thể chưa bắt đầu hiệu lực. Ngày NULL là chưa biết, không tự coi là hiện tại. Nếu có nhiều bản ghi đã duyệt mâu thuẫn hoặc thiếu thông tin xác định hiệu lực, yêu cầu rà soát hoặc trả lời có giới hạn thay vì chọn tùy ý.

```python
resolve_entities(query: str, region: str | None = None) -> list[EntityCandidate]
get_verified_locations(entity_id: UUID, at: date | None = None) -> list[PlaceLocation]
get_entity_evidence(entity_id: UUID) -> list[Evidence]
```

Repository chỉ truy vấn dữ liệu. Quyết định confidence, intent và câu trả lời nằm ở service layer.

#### 5.3.1. Entity resolution priorities

`resolve_entities()` tìm entity theo 5 tầng ưu tiên, dừng khi có kết quả ở tầng cao hơn:

```text
Priority 1: exact normalized_name match (score 1.0)
Priority 2: substring alias match — alias xuất hiện trong query (score = alias.confidence)
Priority 3: substring entity name match — tên entity xuất hiện trong query (score 0.9)
Priority 4: address-based match — keywords từ query match place_location.address/ward/district (score 0.35-0.80)
Priority 5: fuzzy match — fallback trên toàn bộ tên + alias (score >= 0.68)
```

**Priority 4 — address-based resolution:**

Khi user nhớ tên đường/phường thay vì tên chính thức (ví dụ: "nhà thờ trần phú đà nẵng" thay vì "Nhà thờ chính tòa Đà Nẵng"):

1. Tách query thành core keywords: bỏ location type prefix (nhà thờ, chùa, lăng...), stopwords, question words, region names, và address classifiers (đường, phố, phường...).
2. Tìm `place_location` có `address`/`ward`/`district` chứa core keywords (substring match, accent-stripped).
3. Yêu cầu: ít nhất 2 keywords, 50% keywords match, ít nhất 1 keyword dài (>= 4 ký tự).
4. Score = 0.70 * ratio; boost +0.10 nếu location đã verified (cap 0.90).
5. Chỉ chạy khi Priority 1-3 đều rỗng — address match yếu hơn name/alias match.

### 5.4. Intent location

Với câu hỏi `ở đâu`, ưu tiên template:

```text
{canonical_name} nằm tại {address}, {ward}, {district}, {province}.
Tên bạn nhập là "{original_query_name}"; tên chuẩn trong dữ liệu là "{canonical_name}".
Nguồn: {source_title} - {source_url}
```

Chỉ hiển thị các phần địa chỉ có giá trị. Không nối chuỗi `None`, không tự suy ra phường/quận từ tên địa điểm.

### 5.5. Tích hợp với `backend/api/chat.py`

Thay vì chỉ nhận `corrections` từ fuzzy matcher, endpoint nên nhận một kết quả resolve có cấu trúc:

```text
resolved_entity_id
canonical_name
original_name
candidates
resolution_status
```

Các trạng thái tối thiểu:

```text
resolved
ambiguous
not_found
```

Giữ response fields hiện có để frontend không hỏng đột ngột:

- `corrected_from`;
- `corrected_to`;
- `needs_user_choice`;
- `suggestions`;
- `sources`.

Bổ sung sau khi frontend sẵn sàng:

- `entity_id`;
- `intent`;
- `resolution_status`;
- `answer_type`.

### 5.6. Quy tắc nguồn

- `verified location` là nguồn ưu tiên cho câu hỏi vị trí.
- Passage dùng để bổ sung mô tả, không thay thế location nếu passage không chứa địa chỉ.
- Citation phải trỏ tới source thực tế.
- Nếu nguồn chỉ nói địa điểm thuộc Huế nhưng không có địa chỉ chi tiết, không trả lời số nhà.
- Khi không có bằng chứng, trả lời thiếu nguồn thay vì đoán.

### 5.7. Test bắt buộc

```text
Cung An Định ở đâu?
cung an dinh o dau
Lăng An Định ở đâu?
nhà thờ con dê ở đâu?
con gà ở đâu?
nhà thờ chính toà ở đâu?
nhà thờ trần phú đà nẵng ở đâu?
bảo tàng chăm đường bạch đằng ở đâu?
địa danh không tồn tại ở đâu?
hai địa danh khác nhau cùng tên ở đâu?
địa điểm có location pending ở đâu?
```

Phải kiểm tra:

- alias đúng dẫn tới entity chuẩn;
- nhiều entity cùng alias tạo lựa chọn;
- location pending không được trả lời khẳng định;
- không có source thì không hiển thị citation giả;
- câu chào không bị ép qua entity resolver;
- retrieval cũ vẫn pass các test hồi quy.

**Điều kiện hoàn thành bước 5:** chatbot dùng database cho entity/location đã xác minh, vẫn có fallback corpus, và không sinh địa chỉ không có bằng chứng.

## 6. Thứ tự commit đề xuất

Tách thành các commit nhỏ để dễ review và rollback:

1. `docs: add database migration guide`
2. `schema: finalize minimal heritage tables`
3. `infra: add postgres compose service`
4. `backend: add sqlalchemy and alembic foundation`
5. `data: add idempotent corpus importer`
6. `chat: resolve entities from database`
7. `tests: cover database and location answer regressions`

Không gộp migration, import dữ liệu và thay đổi prompt/LLM vào một commit lớn.

## 7. Checklist kết thúc

- [ ] DBML đã chốt và không còn alias lưu ở hai nơi.
- [x] PostgreSQL có volume và healthcheck.
- [x] `DATABASE_URL` dùng secret qua environment.
- [x] Alembic migration chạy trên database trống và nhận diện volume legacy an toàn.
- [ ] CHECK, FK, unique và index đã được test.
- [x] Import corpus idempotent (45 document, 349 passage, 45 entity, 53 alias).
- [x] Location Cung An Định có URL chính thức, câu nguồn và trạng thái xác minh.
- [x] Alias trùng giữa nhiều entity được xử lý bằng candidate list.
- [x] Chatbot resolve entity từ database.
- [x] Resolver DB hỗ trợ tên sai chính tả, tên rút gọn và alias; chỉ tự chọn khi điểm đủ cao và tách biệt.
- [x] Resolver DB hỗ trợ tìm entity theo địa chỉ (tên đường/phường) khi user không nhớ tên chính thức.
- [x] Intent location dùng verified structured data trước LLM.
- [x] Câu trả lời không có bằng chứng bị từ chối hoặc nói rõ thiếu nguồn.
- [ ] Test hồi quy cũ vẫn pass.
- [ ] Backup/restore đã được thử trước khi dùng dữ liệu thật.

> Trạng thái dữ liệu local ngày 2026-09-11: migration ở revision
> `d0f4a2c81e7b`; importer đã nạp 45 document, 349 passage, 45 entity, 53 alias
> và một location đã xác minh. Nguồn chính thức của Trung tâm Bảo tồn Di tích Cố
> đô Huế xác nhận Cung An Định tại 97 đường Phan Đình Phùng, Thành phố Huế.
