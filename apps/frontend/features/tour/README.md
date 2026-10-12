# Bộ khung tour 3D

## Luồng đang chạy

`content/[slug]/layout.tsx` giữ một `HeritageCanvas` xuyên suốt landing và các scene. F5/link scene mới quay về loading; chỉ mở Start sau khi GLB giải mã thành công. `HeritageViewer` ghép **điều khiển 3D + giao diện**, không tạo canvas thứ hai.

Three.js và types đã cài. Model Tự Đức dùng `/tour-assets/tuduc.glb` rewrite đến R2 vì URL R2 hiện chưa trả CORS cho trình duyệt. Decoder KTX2/Basis ở `public/three/basis/`, Draco glTF ở `public/three/draco/` (kèm license).

## Chạy thử dữ liệu Tapestry

Mở `/content/tapestry-test`, chờ tải rồi Bắt đầu trải nghiệm. Trang này đọc `features/tour/tour.json`, không gọi backend và không dùng tọa độ Petra cho model Tự Đức.

- `modelUrl`: GLB Petra từ `threeJS_sets` trong HTML, vẫn tải trực tiếp CDN nguồn (hiện có CORS). Không sao chép asset sang R2 hoặc public.
- `payload`: 1 overview, 7 scene; camera start/zoom, interactive camera và 10 marker/popup join theo ID nguồn.
- `playback`: narration/VTT tiếng Anh (`*_1`), 14 GLB highlight theo timeline. `endSeconds: null` giữ hiện đến khi đổi scene. OBB `exploreArea` được giữ để phát triển tiếp, chưa áp collision.
- Nút **Zoom view / Start view** thử hai preset. Vào scene s2 rồi **Explore in 3D**, click marker để mở nội dung và focus camera; Close trả về góc Explore, Reset về camera interactive, Exit về camera scene.
- Scene s3: Play hoặc skip +15 giây để thấy các model lạc đà. Đổi scene không tải lại model chính.

Tạo lại JSON từ source HTML tại máy bạn:

```sh
node scripts/extract-tapestry-tour.mjs
```

Giữ nguyên file HTML đầu vào. Script chỉ parse block JSON, không chạy JavaScript của trang. JSON đã chuẩn hóa, không sao chép các bảng index trùng lặp. Chỉ dùng dữ liệu/asset bên thứ ba này để thử, không coi là dữ liệu di sản sở hữu để phát hành.

Đây vẫn là viewer cơ bản: marker cầu thay lens shader; popup mở link media; camera chuyển ngay, chưa tween/guided zoom/sky/fog theo nguồn. Góc focus “Niches for statues” hiện khá tối trên model này; tọa độ được giữ nguyên nguồn, chưa xử lý collision.

## Nơi phát triển tiếp

- `player/useTourPlayer.ts`: điều phối narration, captions, Explore và highlight được chọn; URL scene vẫn là nguồn trạng thái scene.
- `player/useNarration.ts`: audio thật, play/pause/seek/mute, thời gian và lỗi. Không có URL thì Play bị khóa, không chạy đồng hồ giả.
- `player/useCaptions.ts`: fetch VTT, cue plain text và cue chồng nhau theo thời gian audio. Chưa hỗ trợ styling/region VTT.
- `three/model-loader.ts`: cache GLTF theo URL trong phiên engine, decoder, abort và giải phóng tài nguyên. Model clone dùng chung geometry/material; không tự dispose chúng ngoài loader.
- `three/environment.ts`: nền, ánh sáng, exposure. Thêm sky/fog/light_settings tại đây.
- `three/camera-controller.ts`: fit model, snapshot/reset, preset DB và camera perspective trong GLB. Preset hiện chuyển ngay; thêm tween/guided animation tại đây. Model Tự Đức hiện không có camera GLB.
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
