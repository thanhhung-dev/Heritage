# terrain-gen — sinh lớp địa hình GLB từ toạ độ

Công cụ tạo "lớp bối cảnh" (context terrain) cho một điểm di sản, theo đúng cách
Tapestry/CyArk làm với Petra: một node riêng, lưới heightfield thưa, UV chiếu phẳng,
chỉ có albedo — không normal map.

Gồm ba script:

| File | Việc |
|---|---|
| `terrain_glb.py` | tải DEM + ảnh vệ tinh, dựng lưới, xuất GLB terrain |
| `merge_glb.py` | gộp terrain vào GLB công trình, canh tâm + mức chân |
| `ktx2-to-png.mjs` | đổi texture KTX2 → PNG để **Blender mở được** |

## Blender không import được: "KHR_texture_basisu is not available"

glTF addon của Blender 4.x không giải mã KTX2 và không có cách bật. Phải chuyển ảnh sang PNG:

```bash
node tools/terrain-gen/ktx2-to-png.mjs tuduc_merged_full.glb tuduc_merged_blender.glb \
     --max 2048 --level 6
```

- `--max` — cạnh lớn nhất sau khi thu nhỏ (box filter). `0` = giữ 4096.
- `--level` — mức nén zlib của PNG (0–9).
- Chỉ thay `bufferView` của **ảnh**; geometry, UV, node, material copy nguyên byte.

> **Đừng xoá `byteStride` của bufferView hình học.** File RealityCapture dùng accessor
> interleaved; xoá stride thì Blender vẫn báo đủ số tam giác nhưng lưới nổ tung.
> Đếm tam giác không phát hiện được lỗi này — phải render thử.

```
python tools/terrain-gen/terrain_glb.py --lat 16.43278 --lng 107.56528 \
    --size 2000 --grid 160 --tex 3000 --out tuduc_near.glb --preview tuduc_near.png
```

## Nguồn dữ liệu

| Thành phần | Nguồn | Độ phân giải | Giấy phép |
|---|---|---|---|
| Cao độ | AWS Terrain Tiles (terrarium PNG), gốc SRTM/ASTER/GMTED | ~30 m | Public domain / USGS, dùng thương mại được |
| Ảnh nền | ESRI World Imagery (`MapServer/export`) | 0,3–0,6 m ở đô thị VN | **Chỉ dùng nội bộ / dev**. Xuất bản phải có license Esri/Maxar |

Endpoint ảnh chỉ nhận tối đa ~3000 px mỗi cạnh (4000 trả HTTP 500), nên `--tex`
bị kẹp ở 3000. Muốn 4K–8K cho bản production thì thay `IMG_URL` bằng nguồn bạn
có license (Maxar, Airbus, hoặc ảnh drone tự bay).

Nếu cần bản phát hành thương mại với chi phí 0: dùng **Sentinel-2** (ESA, 10 m,
CC BY) cho lớp xa ≥ 10 km; lớp gần vẫn phải mua hoặc bay drone.

## Tham số

| Cờ | Mặc định | Ý nghĩa |
|---|---|---|
| `--lat` `--lng` | — | tâm ô vuông (WGS84) |
| `--size` | 2000 | cạnh ô vuông, mét |
| `--grid` | 192 | số đỉnh mỗi cạnh (192 → 36.864 đỉnh, 73k tam giác) |
| `--tex` | 3000 | cạnh texture, kẹp ở 3000 |
| `--hole` | 0 | bán kính khoét lỗ giữa, để lồng lớp gần vào |
| `--z-scale` | 1.0 | phóng đại cao độ (1.5–2 hay dùng cho cảnh núi thấp) |
| `--median` | 5 | lọc trung vị, xoá blob tán cây của SRTM |
| `--smooth` | 2 | số lần lọc hộp 3×3 |
| `--dem-zoom` | tự | ép mức zoom tile DEM |
| `--no-texture` | — | chỉ sinh hình khối |
| `--preview` | — | ghi ảnh hillshade PNG để kiểm tra nhanh |

## Gợi ý tham số theo cấp

| Cấp | size | grid | tex | hole | Ghi chú |
|---|---|---|---|---|---|
| Vùng (horizon) | 20.000–40.000 | 160–192 | 3000 | 700 | thay cho `gcontext.006lp` của Petra |
| Trung | 4.000–8.000 | 192 | 3000 | 0 | thay cho `gcontext.005` |
| Gần | 1.500–2.500 | 128–160 | 3000 | 0 | nền quanh quần thể |

Ba cấp lồng nhau, cấp xa khoét lỗ bằng bán kính nhỏ hơn nửa cạnh cấp gần
(ví dụ gần 2000 m → nửa cạnh 1000 m → `--hole 700`) để hai lớp chồng mép, không hở đường nối.

## Giới hạn phải biết

**DEM miễn phí 30 m không đủ cho cảnh ở cự ly dưới ~500 m.** Một ô 30 m là cả
một cái sân; toàn bộ địa hình Tự Đức chỉ có ~50 m chênh cao trên 2 km, phần lớn
là nhiễu tán cây của radar. Vì vậy Petra phải có thêm `context_low.002` (434 m)
làm bằng photogrammetry drone — không có nguồn miễn phí nào thay được lớp đó.

Nói cách khác: công cụ này giải quyết lớp **≥ 1 km**. Muốn có mặt đất chi tiết
quanh công trình thì phải bay drone (WebODM/Metashape) hoặc quét LiDAR.

## Gắn vào app

GLB xuất ra đã ở hệ Y-up, đơn vị mét, tâm ở gốc, Y=0 tại điểm thấp nhất. Có ba cách dùng:

### 1. Gộp thẳng vào GLB công trình — `merge_glb.py`

Đúng cách Petra làm: một file duy nhất chứa cả monument lẫn địa hình.

```bash
# tự canh theo bbox world của công trình
python tools/terrain-gen/merge_glb.py \
    --base TuDuckt.glb --terrain tuduc_near.glb \
    --out tuduc_merged.glb --auto

# gộp tiếp lớp vành xa, dùng đúng offset của lớp trước
python tools/terrain-gen/merge_glb.py \
    --base tuduc_merged.glb --terrain tuduc_far.glb \
    --out tuduc_merged_full.glb --x 1.84 --y -21.18 --z 21.54
```

Công cụ **không decode lại hình học**: nó nối BIN chunk rồi đánh lại index của
`bufferView / accessor / material / texture / image / sampler`. Nhờ vậy Draco,
KTX2, UV và material của file gốc giữ nguyên tuyệt đối.

`--auto` tính ba thứ:
- tâm mặt bằng = trung điểm bbox **world** (đã áp rotation của root node — file
  RealityCapture thường có một quaternion căn chỉnh ở root, bỏ qua là lệch)
- mức đặt chân = phân vị `--ground-percentile` (mặc định 2%) của cao độ đỉnh
- hạ thêm `--ground-offset` (mặc định −2 m) để terrain không nhô lên xuyên qua
  sân công trình

Node terrain được đặt tên `terrain_<tên>` và là **root node riêng**, không nằm
trong cây của monument — nên rất dễ lọc bỏ khi tính camera.

### 2. Load riêng trong three.js

```ts
const terrain = await new GLTFLoader().loadAsync("/tour-assets/terrain/tuduc_near.glb");
terrain.scene.position.set(offsetX, offsetY, offsetZ); // canh theo gốc model công trình
terrain.scene.traverse((o) => {
  if ((o as THREE.Mesh).isMesh) o.userData.isContext = true; // để camera.fit() bỏ qua
});
scene.add(terrain.scene);
```

Đánh dấu `isContext` rất quan trọng: `camera-controller.fit()` đang lấy
`Box3.setFromObject(model)` trên toàn scene, nên một lớp 24 km sẽ kéo
`near`/`minDistance` lên hàng trăm mét.

### 3. Đo lại độ chính xác của phép canh

`--auto` chỉ căn theo **tâm và mức chân**, không căn theo điểm khống chế. Muốn
chính xác đến mét thì phải chọn 3–4 điểm chung (góc tường, đỉnh bậc, cột cổng),
đo toạ độ trong cả hai hệ rồi giải phép biến đổi similarity. Với scan drone
thường sai số vài mét là chấp nhận được vì terrain chỉ là phông nền.

## Cấu trúc output

Một node duy nhất, một mesh, một material, một texture JPEG nhúng trong BIN chunk.
Không Draco, không KTX2 — mở được bằng Blender, three.js, Windows 3D Viewer.

- `POSITION` float32, `NORMAL` float32 (tính từ đạo hàm trung tâm), `TEXCOORD_0` float32
- index `uint16` nếu < 65.536 đỉnh, `uint32` nếu hơn
- sampler `LINEAR / LINEAR_MIPMAP_LINEAR / CLAMP_TO_EDGE`
