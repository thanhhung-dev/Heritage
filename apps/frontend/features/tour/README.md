# Bộ khung tour 3D

## Luồng đang chạy

`content/[slug]/layout.tsx` giữ một `HeritageCanvas` xuyên suốt landing và các scene. F5/link scene mới quay về loading; chỉ mở Start sau khi GLB giải mã thành công. `HeritageViewer` ghép **điều khiển 3D + giao diện**, không tạo canvas thứ hai.

Three.js và types đã cài. Model Tự Đức dùng `/tour-assets/tuduc.glb` rewrite đến R2 vì URL R2 hiện chưa trả CORS cho trình duyệt. Decoder KTX2/Basis ở `public/three/basis/`, Draco glTF ở `public/three/draco/` (kèm license).

## Chạy thử dữ liệu Tapestry

Mở `/content/tapestry-test`, chờ tải rồi Bắt đầu trải nghiệm. Trang này đọc `features/tour/tour.json`, không gọi backend và không dùng tọa độ Petra cho model Tự Đức.

- `modelUrl`: GLB Petra từ `threeJS_sets` trong HTML, vẫn tải trực tiếp CDN nguồn (hiện có CORS). Không sao chép asset sang R2 hoặc public.
- `payload`: 1 overview, 7 scene; camera start/zoom, interactive camera và 10 marker/popup join theo ID nguồn.
- `playback`: narration/VTT tiếng Anh (`*_1`), 14 GLB highlight theo timeline. `endSeconds: null` giữ hiện đến khi đổi scene. OBB `exploreArea` được giữ để phát triển tiếp, chưa áp collision.
- Nút góc **Dive Deeper** chỉ hiện sau khi narration của scene kết thúc (hoặc Skip Voiceover), và scene có `interactive` (s2–s6). Đổi scene hoặc Replay narration sẽ ẩn lại; scene không có audio được coi là đã kết thúc. Bấm để tạm dừng audio và bay tới camera khu vực trong JSON; `free_explore`/`free` mở free orbit và hiện dấu chân, không phải chế độ đi bộ/FPS.
- Trong Explore, chọn marker hoặc nút trong danh sách điểm để mở nội dung và focus camera theo JSON. Close hoặc Escape trả về góc Explore và focus bàn phím; **Reset view** về camera interactive, **Exit 3D Mode** về camera scene. Không đưa lại hàng nút Zoom/Start/Standard/Free cũ.
- Vào/thoát Explore, Reset và focus/đóng điểm dùng camera transition 1.2 giây (mặc định viewer, không phải thời lượng trong JSON). Nếu khu vực không có camera riêng, Reset bay về góc đã lưu khi vào Explore.
- Scene s3: Play hoặc skip +15 giây để thấy các model lạc đà. Đổi scene không tải lại model chính.

Tạo lại JSON từ source HTML tại máy bạn:

```sh
node scripts/extract-tapestry-tour.mjs
```

Giữ nguyên file HTML đầu vào. Script chỉ parse block JSON, không chạy JavaScript của trang. JSON đã chuẩn hóa, không sao chép các bảng index trùng lặp. Chỉ dùng dữ liệu/asset bên thứ ba này để thử, không coi là dữ liệu di sản sở hữu để phát hành.

Đây vẫn là viewer cơ bản: marker cầu thay lens shader; popup mở link media; chưa có sky/fog theo nguồn. Camera chuyển cảnh bay trong 1.6 giây (instant_move đặt ngay), rồi bám thời lượng narration. Góc focus “Niches for statues” hiện khá tối trên model này; tọa độ được giữ nguyên nguồn, chưa xử lý collision.

## Nơi phát triển tiếp

- `player/useTourPlayer.ts`: điều phối narration, captions, Explore và highlight được chọn; URL scene vẫn là nguồn trạng thái scene.
- `player/useNarration.ts`: audio thật, play/pause/seek/mute, thời gian và lỗi. Không có URL thì Play bị khóa, không chạy đồng hồ giả.
- `player/useCaptions.ts`: fetch VTT, cue plain text và cue chồng nhau theo thời gian audio. Chưa hỗ trợ styling/region VTT.
- `three/model-loader.ts`: cache GLTF theo URL trong phiên engine, decoder, abort và giải phóng tài nguyên. Model clone dùng chung geometry/material; không tự dispose chúng ngoài loader.
- `three/environment.ts`: nền, ánh sáng, exposure. Thêm sky/fog/light_settings tại đây.
- `three/camera-controller.ts`: fit model, snapshot/reset, preset DB và camera perspective trong GLB. `flyToPreset(preset, zoom, duration)` bay mượt (ease-in-out cubic) giữa hai stop; `duration = 0` hoặc `instant_move` thì đặt ngay. `update(delta)` tiến tween mỗi frame — `tour-engine` gọi trong animation loop; `isFlying()` báo đang bay. `applyPreset` vẫn đặt ngay (dùng cho focus marker). Model Tự Đức hiện không có camera GLB.
  - **Trần góc cực (polar):** `OrbitControls` mặc định bị chặn `maxPolarAngle = π/2` (không cho camera xuống dưới mặt phẳng ngang của target). Preset trong `tour.json` có cảnh đặt camera **thấp hơn target** (polar > 90° — hiện 4/7 cảnh). Nếu để clamp đó bật, `controls.update()` chạy mỗi frame sẽ ép camera về đúng mặt phẳng `π/2`, khiến camera **đứng im** dù tween vẫn tiến. Vì vậy controller giữ một `polarCeiling` riêng và tự nới nó trong `allowPose()` theo pose thực tế của từng preset. **Không** hard-code clamp polar bên ngoài controller — mọi thay đổi `maxPolarAngle` phải đi qua `allowPose`. Có test hồi quy cho case này trong `tests/tour-player.test.ts`.
  - **Camera bám timeline narration:** `startTimeline(preset, narrationSeconds)` nội suy tuyến tính từ pose `start` sang pose `zoom` trong **toàn bộ thời lượng audio**; `updateTimeline(seconds)` áp pose mỗi frame, `stopTimeline()` tắt. Vì `seconds` là `currentTime` của audio nên **tua video là camera nhảy đúng vị trí tương ứng**, không chỉ tiến một chiều; pause giữ nguyên pose. Metadata đến khi đang chuyển cảnh không hủy chuyến bay: controller hòa chuyến bay vào pose narration hiện tại, tránh nhảy khi audio tự phát sớm. `flyToPreset`/`applyPreset` tắt timeline trước đó để thao tác chọn góc/focus marker không bị kéo lại. Trong Explore hoặc cảnh instant_move thì timeline tắt để người dùng tự do xoay.
  - **Đồng hồ phát nội bộ:** `tour-engine` tự tiến `playbackClock` mỗi frame khi audio đang chạy (`setPlaybackTime(seconds, playing)`), thay vì bám thẳng `currentTime` của React (chỉ cập nhật theo `timeupdate` ~4Hz). Nhờ vậy camera và scene-highlight chạy mượt 60fps và vẫn đồng bộ đúng khi seek.
  - **Hiệu năng đường chạy mỗi frame (quan trọng):** `applyPose` là đường nóng nhất của chuyển động camera, phải giữ thật rẻ:
    - Chỉ `copy` position/target + `lookAt`; **không** gọi `controls.update()`, **không** gọi `updateProjectionMatrix()` (fov giữa hai pose của một cảnh không đổi nên ma trận chiếu không cần dựng lại).
    - `allowPose` chỉ nới `maxDistance/minDistance/maxPolarAngle` — đều là so sánh số, không cấp phát.
    - **Không cấp phát `Vector3` mỗi frame.** Dùng các vector tạm `scratch` / `scratchTarget` / `scratchOffset`. Mỗi mục đích phải có vector **riêng**: nếu `allowPose` dùng chung vector với tham số `position` đang truyền vào thì nó ghi đè chính giá trị cần áp (aliasing) và camera dừng sai toạ độ. Có test hồi quy "không có aliasing vector tạm".
    - Khi controller tự ghi pose (`drivingPose`), `tour-engine` **bỏ hẳn** `controls.update()` trong frame đó — nó không có gì để tính mà lại rất nặng (dựng lại spherical + `lookAt`). Chỉ gọi `syncControls()` **một lần** khi kết thúc chuyến bay / khi timeline chốt pose cuối.
    - `updateTimeline` có cờ `settled`: tới đích rồi thì thôi áp pose mỗi frame, nhưng **tự bật lại khi thời gian lùi về trong đoạn bay** (nếu không, tua ngược sẽ không kéo camera về).
    - Đo được trong 60 frame bay: `updateProjectionMatrix = 0`, `controls.update = 0` (do `drivingPose`), `lookAt = 60`.
- `three/explore-controller.ts`: Standard/Free orbit, reset về góc lúc vào và exit. Free orbit **chưa phải FPS/đi bộ**, chưa có collision/giới hạn `explore_area`.
- `three/interactive-highlights.ts`: marker cầu, raycast chọn và callback. Thay marker bằng lens/icon/model tương tác tại đây.
- `three/scene-highlights.ts`: GLB phụ, transform, hiện theo `[startSeconds,endSeconds)` (end null không tắt) và animation `rotate`/GLB clips `LoopRepeat` theo timeline; clone skeleton riêng để không chia sẻ bones.
- `components/ExploreControls.tsx`, `HighlightPanel.tsx`: UI cơ bản. Panel hiện title/text và link media; cần contract MIME/type để nhúng ảnh/video/audio đúng loại.

## Nối dữ liệu thật

Engine sẵn sàng lấy từ `useHeritageTour().engine`; không truy cập renderer qua DOM/global. API chính:

```ts
engine?.applyCameraPreset(scene.camera); // start; tham số thứ hai true để dùng zoom
engine?.useGLBCamera("Camera_Main"); // false nếu không có camera perspective này
engine?.setInteractiveHighlights(interactive.highlights);
engine?.setSceneHighlights(timedHighlights); // Promise; caller phải xử lý lỗi tải
engine?.setPlaybackTime(seconds);
```

Trong viewer, truyền URL narration/VTT **đã được adapter chuẩn hóa**:

```ts
const player = useTourPlayer({ narrationUrl, captionsUrl });
```

Payload `HeritageScene` hiện chưa có narration/VTT riêng hoặc thời điểm scene highlight. Không lấy `voice_clips[0]` làm narration, không tự đoán thời gian. Bản đang chạy chưa tự áp camera/highlight từ demo vì tọa độ demo không khớp GLB thật. Khi nối DB, reset/thay highlights theo scene tại `useTourPlayer`, xử lý Promise và chỉ áp preset sau khi xác nhận cùng hệ tọa độ/model.

Asset bên ngoài cần CORS hoặc proxy/rewrite phù hợp (rewrite hiện tại chỉ dành cho model Tự Đức). Không tự proxy mọi URL.

Chạy `npm run lint`, `npx tsc --noEmit --incremental false`, `npm test` từ `apps/frontend`.
