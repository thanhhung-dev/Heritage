# Góc camera của tour 3D — lấy từ đâu và cách tự đặt

Tài liệu này trả lời hai câu: **toạ độ camera mở đầu của mỗi cảnh đang lấy từ đâu**, và
**có thể dựng camera trong Blender rồi xuất kèm GLB hay không**.

## 1. Chuỗi dữ liệu

```
bảng scene (PostgreSQL)
  camera_node_name  text          -- tên camera nhúng trong GLB (nếu có)
  cam_start_pos     jsonb         -- [x, y, z]  mét, hệ glTF
  cam_start_target  jsonb         -- điểm ngắm của góc Start
  cam_zoom_pos      jsonb         -- góc Zoom (dùng cho timeline theo audio)
  cam_zoom_target   jsonb
  instant_move      bool          -- true = đặt ngay, không bay
        │
        ▼
GET /api/heritages/{slug}/tour  →  scene.camera  (apps/backend/api/heritage.py)
        │  JSONB được trả NGUYÊN XI, không nhân hệ số, không đổi trục
        ▼
useTourPlayer.ts  →  engine.flyCameraPreset(camera)  /  engine.useGLBCamera(node_name)
        │
        ▼
camera-controller.ts  →  camera.position / controls.target
```

Điểm quan trọng: **con số trong DB là toạ độ của model sau khi đã nạp vào three.js**,
tức hệ glTF (Y hướng lên, đơn vị mét, -Z là hướng nhìn của camera). Không có bước quy
đổi nào ở giữa, nên toạ độ đọc trong Blender phải đổi trục trước khi ghi vào DB.

## 2. Hiện trạng của `lang-tu-duc`

| sequence | cảnh | cam_start_pos | camera_node_name |
| --- | --- | --- | --- |
| -1 | Khiêm Lăng – Dấu ấn một đế vương | `null` | `null` |
| 0 | Giấc mộng Khiêm Lăng | `null` | `null` |
| 1 | Khiêm Cung Ký | `null` | `null` |
| 2 | Bia đá và những nỗi niềm | `null` | `null` |
| 3 | Lăng mộ – Bí ẩn nơi an nghỉ | `null` | `null` |

Tất cả đang `null`, nên hiện tại **không cảnh nào có góc đặt trước**. Client rơi về
`cameraController.fit(model)`: khung toàn bộ model theo hướng `(1, 0.8, 1)`, không có
góc ngắm riêng, và vì model đã gộp cả địa hình 24 km nên công trình nằm khá xa.

## 3. Thứ tự ưu tiên khi vào cảnh

1. `cam_start_pos` + `cam_start_target` — toạ độ tác giả ghi trong DB.
2. `camera_node_name` — camera nhúng trong GLB (mục 5).
3. Không có cả hai — giữ góc `fit()`.

Toạ độ DB đứng trước vì nó không gãy khi model được xuất lại và đổi tên node.

## 4. Cách 1 — đặt camera trong Blender rồi ghi toạ độ vào DB (khuyến nghị)

### 4.1 Dựng trong Blender

1. Mở file `.blend` của công trình, **cùng hệ trục với file sẽ export** (nếu model cuối
   là bản đã gộp địa hình thì camera phải nằm trong bản đã gộp).
2. Thêm camera (`Shift+A ▸ Camera`), đặt vào vị trí muốn thấy lúc mở cảnh.
3. Thêm một **Empty** đặt tên `<tên camera>_target` ngay tại điểm muốn camera quay
   quanh (tâm công trình, cổng chính…). Đây là `cam_start_target`; thiếu nó thì
   script lấy `vị trí + hướng nhìn × khoảng cách`, kém chính xác hơn nhiều.
4. Hướng camera vào Empty: chọn camera ▸ `Add Object Constraint ▸ Track To`, target là
   Empty, `To = -Z`, `Up = Y`.
5. Đặt tên camera theo cảnh: `S0_Cam`, `S1_Cam`… và góc zoom là `S0_Zoom`, `S1_Zoom`…
   (số **đầu tiên** trong tên là `sequence` của cảnh; có thể ghi đè bằng custom
   property `scene_sequence`).

### 4.2 Xuất toạ độ

```bash
blender -b kien-truc.blend -P tools/blender-camera-export.py -- \
    --out tmp/tuduc-cameras.json --sql tmp/tuduc-cameras.sql \
    --slug lang-tu-duc --mode coords
```

Script đổi trục Blender → glTF `(gx, gy, gz) = (bx, bz, -by)` (đúng phép đổi của glTF
exporter), làm tròn 3 chữ số, rồi in bảng toạ độ và sinh file `.sql`:

```sql
update scene set
  cam_start_pos = '[46.15,7.356,-24.088]'::jsonb,
  cam_start_target = '[14.54,8.074,-1.886]'::jsonb
where heritage_id = (select id from heritage where slug = 'lang-tu-duc')
  and sequence = 0;
```

Chạy file `.sql` đó lên DB là xong, không cần build lại frontend.

Cờ hữu ích:

| cờ | ý nghĩa |
| --- | --- |
| `--mode coords` | chỉ ghi `cam_start_*` / `cam_zoom_*` (mặc định, chạy được ngay) |
| `--mode node` | chỉ ghi `camera_node_name` (dùng camera nhúng trong GLB, mục 5) |
| `--mode both` | ghi cả hai |
| `--distance 50` | khoảng cách điểm ngắm khi không có Empty `_target` |
| `--precision 3` | số chữ số thập phân |

### 4.3 Nếu chỉ có ảnh/không có file .blend

Đặt camera bằng tay trong Blender rồi xuất `.blend`, hoặc lấy toạ độ từ một viewer
glTF (mở model, xoay tới góc ưng ý, đọc `camera.position` và `controls.target` qua
`window.__tourCameraDump()` — xem mục 6).

### 4.4 Chốt góc ngay trong trình duyệt (không cần Blender)

Nhanh hơn và thấy đúng thứ người xem sẽ thấy (cùng renderer, cùng sky, cùng audio).

```
1. Chạy backend + frontend, mở /content/lang-tu-duc/s0
2. Bấm pause audio          ← timeline đang chạy sẽ kéo camera về quỹ đạo, phải dừng trước
3. Kéo chuột tới góc mong muốn
4. Console:  __tourCameraDump()
5. Copy JSON vừa in, lưu vào tmp/dump.json
6. python tools/camera-pose-sql.py --slug lang-tu-duc --scene 0 --pose-file tmp/dump.json
7. Chạy file .sql sinh ra (hoặc thêm --out tmp/s0.sql rồi psql -f)
```

Góc Zoom thì thêm `--role zoom`. Nhiều cảnh một lượt:

```bash
# tmp/poses.json = [{"scene":0,"role":"start","position":[...],"target":[...]}, ...]
python tools/camera-pose-sql.py --slug lang-tu-duc --batch tmp/poses.json --out tmp/cameras.sql
```

Công cụ nhận cả JSON đầy đủ của `__tourCameraDump()` (chỉ lấy `camera.position` và
`camera.target`) lẫn dạng rút gọn `{"position":[…],"target":[…]}`; toạ độ có thể là mảng
hoặc `{x,y,z}`.

Lưu ý: `__tourCameraDump()` chỉ có ở môi trường dev (hoặc bật bằng
`window.__tourCameraDebug = true`).


## 5. Cách 2 — dựng camera trong Blender và xuất kèm GLB

**Được, và addon glTF của Blender có sẵn tuỳ chọn này**:

`File ▸ Export ▸ glTF 2.0 (.glb)` → panel `Include` → tích **Cameras**.
Camera sẽ thành một node có thuộc tính `camera` trong file; three.js đọc vào
`gltf.cameras`. Nếu quên tích, file GLB không có camera nào và bước dưới trả về `false`.

Sau đó ghi tên camera vào DB:

```bash
blender -b kien-truc.blend -P tools/blender-camera-export.py -- \
    --out tmp/cameras.json --sql tmp/cameras.sql --slug lang-tu-duc --mode node
```

Client khi đó chạy `engine.useGLBCamera(node_name)`, đọc từ GLB:

- **vị trí** — `camera.getWorldPosition()`;
- **hướng** — `camera.getWorldDirection()` (trục -Z của camera);
- **fov dọc** — `camera.fov` do GLTFLoader dựng từ `yfov`;
- **điểm ngắm** — theo thứ tự: node `<tên camera>_target` / `CAM_Target` trong GLB →
  tia bắn từ camera vào model, lấy điểm trúng đầu tiên → lùi về điểm cách 1 m theo
  hướng nhìn.

Camera trong glTF **chỉ có vị trí và hướng**, không có "điểm ngắm" — mà OrbitControls
lại quay quanh một điểm. Vì thế nếu chỉ export camera trần, hãy export kèm một Empty
tên `<tên camera>_target` (Empty cũng được xuất thành node khi tích `Include ▸ Empty`).

`up` của camera trong GLB bị **bỏ qua** (dùng trục Y thế giới): OrbitControls dựng hệ
quay quanh `camera.up`, một camera có roll sẽ làm cả quỹ đạo quay nghiêng theo. Nếu
camera có roll, console in cảnh báo `[cam:glb-cam]`.

### So sánh hai cách

| | toạ độ trong DB | camera trong GLB |
| --- | --- | --- |
| Xuất lại model đổi tên node | không ảnh hưởng | gãy (phải cập nhật `camera_node_name`) |
| Số cảnh dùng chung một model | thoải mái | thoải mái, mỗi cảnh một camera |
| Cần build lại frontend | không | không (đã nối sẵn) |
| Dùng được cho timeline start→zoom | có (`cam_zoom_*`) | chỉ có góc start |

## 6. Kiểm tra

Dev mặc định bật log camera. Trong console trình duyệt:

```js
window.__tourCameraDump()   // pose hiện tại + writer đang điều khiển camera
window.__tourCameraDebug = true   // bật/tắt log [cam:*]
```

Log cần thấy khi vào cảnh:

- `[cam:glb-cam] dùng camera S1_Cam · pos=(…) · fov=… · target=(…)` — đang dùng camera GLB;
- `[cam:glb-cam] GLB không có camera phối cảnh tên "…" (đang có: …)` — sai tên hoặc
  chưa tích `Include ▸ Cameras` khi export;
- `[cam:timeline] start 87.7s · (…) → zoom (…)` — timeline theo audio đã bật.

## 7. Lưu ý

- Toạ độ phải nằm trong **hệ của model cuối cùng**. `tools/terrain-gen/merge_glb.py`
  chỉ thêm node địa hình, không dịch công trình, nên toạ độ đo trên model gốc vẫn đúng;
  nhưng nếu có bước nào scale/rotate cả model thì phải đo lại.
- Model càng lớn (đã gộp địa hình 24 km) thì `fit()` càng đẩy camera ra xa. Đặt
  `cam_start_pos` là cách duy nhất để cảnh mở đầu đúng ý.
- `instant_move = true` thì góc được đặt ngay, không bay 1.6 s; timeline theo audio
  cũng bị bỏ qua cho cảnh đó.

## 8. Bản gốc (Tapestry / CyArk) làm bằng cách nào

Kiểm tra trực tiếp trên `features/tour/tapestry.html` (dữ liệu nhúng `tapestry-data`) và
`tmp/petranew_lod0.glb`:

**GLB không chứa camera.** `cameras = 0`, không node nào tên chứa "cam"; 13 node là các
mảnh scan (`gcontext.005`, `gcontext.006lp`, `l_building1`…), do `glTF-Transform v4.5.0`
xuất ra. Model Tự Đức trên R2 cũng vậy: `cameras = 0`, root node
`Tu Duc's Tomb - Stele Building Aerial`.

**Toàn bộ camera nằm trong dữ liệu (CMS), đúng như bảng `scene` của mình:**

```
threeJS_sets[set_id]           ← 1 set, 1 asset cho CẢ tour
  asset        = …/petranew_lod0.glb
  type         = "lod"
  tjs_settings = { sky: { azimuthOffset, environmentIntensity } }

scenes[i]                      ← mỗi cảnh
  start_camera_position = "46.15,7.356,-24.088"     ← chuỗi "x,y,z", không phải array
  start_camera_target   = "14.54,8.074,-1.886"
  zoom_camera_position  = "6.539,6.987,-1.516"
  zoom_camera_target    = "1.43,7.161,2.022"
  instant_move          = 0
  camera_fov            = null        (7/7 cảnh Petra đều null ⇒ dùng fov mặc định)
  audio_narration_1 / narration_cc_1  → audio + phụ đề của cảnh

overview                       ← dùng TÊN FIELD KHÁC
  camera_position / camera_target / zoom_camera_position / zoom_camera_target
```

`scripts/extract-tapestry-tour.mjs` chỉ việc tách chuỗi đó thành mảng:
`vector(value) → value.split(",").map(Number)`. Không có bước đọc camera từ GLB.

### Đối chiếu với schema của mình

| Bản gốc | Bảng `scene` | Ghi chú |
| --- | --- | --- |
| `start_camera_position` | `cam_start_pos` | string "x,y,z" → JSONB array |
| `start_camera_target` | `cam_start_target` | |
| `zoom_camera_position` | `cam_zoom_pos` | |
| `zoom_camera_target` | `cam_zoom_target` | |
| `instant_move` | `instant_move` | |
| `camera_fov` | — | bản gốc để `null`; engine mình cũng cố định fov 50 |
| — | `camera_node_name` | **không có ở bản gốc**, đây là phần thêm của dự án |

Kết luận: chọn hướng **"1 GLB + export xyz"** là bám đúng kiến trúc gốc. Camera nhúng
trong GLB (mục 5) là tuỳ chọn thêm, không phải cách bản gốc làm.

Khác biệt đáng lưu ý: Petra dùng 1 GLB **6,9 MB** cho 7 cảnh; Tự Đức hiện là **110 MB**
(chưa gộp địa hình) / **138 MB** (bản đã gộp) — nặng gấp ~20 lần, nên thời gian vào cảnh
không thể so với bản gốc.

