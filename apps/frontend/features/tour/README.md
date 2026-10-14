# Bộ khung tour 3D

## Luồng đang chạy

`content/[slug]/layout.tsx` giữ một `HeritageCanvas` xuyên suốt landing và các scene. F5/link scene mới quay về loading; chỉ mở Start sau khi GLB giải mã thành công. Thanh loading của trang content luôn hiện "Loading…" cho tới khi model xong (không hiện tiến độ chi tiết); lỗi tải model đi từ canvas lên layout qua `useHeritageTour().modelError` và hiện trong trang content. `HeritageViewer` ghép **điều khiển 3D + giao diện**, không tạo canvas thứ hai.

Three.js và types đã cài. Model Tự Đức dùng `/tour-assets/tuduc.glb` rewrite đến R2 vì URL R2 hiện chưa trả CORS cho trình duyệt. Decoder KTX2/Basis ở `public/three/basis/`, Draco glTF ở `public/three/draco/` (kèm license).

## Chạy thử dữ liệu Tapestry

Mở `/content/tapestry-test`, chờ tải rồi Bắt đầu trải nghiệm. Trang này đọc `features/tour/tour.json`, không gọi backend và không dùng tọa độ Petra cho model Tự Đức.

- `modelUrl`: GLB Petra từ `threeJS_sets` trong HTML, vẫn tải trực tiếp CDN nguồn (hiện có CORS). Không sao chép asset sang R2 hoặc public.
- `payload`: 1 overview, 7 scene; camera start/zoom, interactive camera và 10 marker/popup join theo ID nguồn.
- `playback`: narration/VTT tiếng Anh (`*_1`), 14 GLB highlight theo timeline. `endSeconds: null` giữ hiện đến khi đổi scene. OBB `exploreArea` được giữ để phát triển tiếp, chưa áp collision.
- Nút góc **Dive Deeper** chỉ hiện sau khi narration của scene kết thúc (hoặc Skip Voiceover), và scene có `interactive` (s2–s6). Đổi scene hoặc Replay narration sẽ ẩn lại; scene không có audio được coi là đã kết thúc. Bấm để tạm dừng audio và bay tới camera khu vực trong JSON; `free_explore`/`free` mở free orbit và hiện dấu chân, không phải chế độ đi bộ/FPS.
- Trong Explore, các ô điểm có thumbnail + tên, sắp theo `sort_order`; ô đang chọn có viền/nền cam. Chọn ô bằng chuột hoặc Enter/Space để mở nội dung và focus camera theo JSON; marker 3D vẫn chọn được. Thumbnail lấy từ nguồn Tapestry qua `thumb_url`; thiếu/lỗi ảnh dùng lens icon. Backend hiện chưa trả thumbnail, payload cũ vẫn hoạt động với icon thay thế.
- Close hoặc Escape trả về góc Explore và focus bàn phím; **Reset view** về camera interactive, **Exit 3D Mode** về camera scene. Không đưa lại hàng nút Zoom/Start/Standard/Free cũ.
- **Exit 3D Mode** dùng đúng cấu trúc nút gốc `.exitCorner` (viên kính tròn + nhãn, `position: fixed` góc trên phải): `<div.exitCorner.active> › <button.exitCorner-btn> › icon `playpen_exit_ow.svg` + `<span.exitCorner-label>`. Panel tối `.exploreControls` cũ (240px, hàng nút phụ) đã bị xoá khỏi component và stylesheet. Nút mount ở trạng thái chưa `active` rồi bật ở frame kế tiếp (double `requestAnimationFrame`) để chạy được transition `opacity 0→1` + `scale .85→1`. Khi panel điểm đang mở, `.exitCorner` bị `visibility: hidden` để nhường góc trên phải.
- Vào/thoát Explore, Reset và focus/đóng điểm dùng camera transition 1.2 giây (mặc định viewer, không phải thời lượng trong JSON). Nếu khu vực không có camera riêng, Reset bay về góc đã lưu khi vào Explore.
- Scene s3: Play hoặc skip +15 giây để thấy các model lạc đà. Đổi scene không tải lại model chính.

Tạo lại JSON từ source HTML tại máy bạn:

```sh
node scripts/extract-tapestry-tour.mjs
```

Giữ nguyên file HTML đầu vào. Script chỉ parse block JSON, không chạy JavaScript của trang. JSON đã chuẩn hóa, không sao chép các bảng index trùng lặp. Chỉ dùng dữ liệu/asset bên thứ ba này để thử, không coi là dữ liệu di sản sở hữu để phát hành.

Đây vẫn là viewer cơ bản: lens badge là quad có texture glow + số trong suốt, billboard theo camera; chưa sao chép shader gốc Tapestry. Popup mở link media; chưa có sky/fog theo nguồn. Camera chuyển cảnh bay trong 1.6 giây (instant_move đặt ngay), rồi bám thời lượng narration. Góc focus “Niches for statues” hiện khá tối trên model này; tọa độ được giữ nguyên nguồn, chưa xử lý collision. Badge số 2 ở s2 có thể bị tiêu đề che một phần; không tự dời lens_pos nguồn.

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
- `three/interactive-highlights.ts`: Group tại `lens_pos`, mesh `lens_badge` ở local zero; quad 0.1 × 0.1 gồm glow (vòng chính đường kính khoảng 0.05), nhân `lens_scale`. Số theo `sort_order`, MeshBasicMaterial không chịu ánh sáng, NormalBlending, depthTest/depthWrite=false. Billboard mỗi frame; raycast bỏ góc quad trong suốt, chọn đúng ID và callback. Texture/material được dispose khi thay điểm; geometry chung được dispose cùng engine. Khi focus sau orbit, controller xóa quán tính damping nhưng giữ đúng pose đích JSON.
  - **Hover badge ⇒ camera bay tới đứng trước badge (camera-controller):** `setHovered()` phát `DollyTarget { point, approach, minDistance }` ra `onHoverTarget`; `tour-engine` nối thẳng vào `cameraController.setDollyTarget()`. Vào badge: controller dựng pose đích bằng trục ngang của badge so với camera (giữ hướng nằm-ngoài-màn-hình, `setY(0)`) rồi nghiêng lên `rise = 0.3` (`atan` so với phương ngang) để ống kính không tụt xuống dưới mặt đất — đây là fix cho lỗi "hover thì camera lùi ra xa / bị địa hình che". Target = chính badge nên badge nằm giữa màn hình; camera `lookAt` badge nên hướng lệch ~0°. Khoảng cách đích đúng bằng `khoảng cách lúc hover × approach` (`HOVER_APPROACH = 0.3` ⇒ lại gần 3,3 lần), sàn `HOVER_MIN_DISTANCE = 0.6` chống xuyên model. Rời badge: bay về **"camera cũ" = pose đã chụp lúc BẮT ĐẦU hover** (`hoverStart`), đúng cùng pattern `entry`/`exit` của explore-controller (nút "Dive Deeper": vào thì lưu camera, ra thì khôi phục có animation). Chuyến bay dùng `easeInOutCubic` 0.9 giây. Vào hover cũng `timeline = null` để timeline không ghi đè pose mỗi frame.
  - **Hover bắt đầu GIỮA chuyến bay chuyển cảnh (đã dính):** `setDollyTarget` chỉ tắt `timeline` mà quên `flight`, nên nếu người dùng hover trong 1,2–1,6 giây đầu của deep live thì `hoverStart = snapshot()` chụp phải một điểm **giữa đường** của chuyến bay. Rời badge ⇒ camera dừng lơ lửng giữa không trung thay vì về góc mặc định của deep live. Đồng thời `update()` (flight) và `updateDolly()` cùng ghi pose mỗi frame, và `syncControls()` cuối chuyến bay bắn vào giữa chuyến hover. Fix: `captureReturnPose()` — nếu có `flight` thì lấy **ĐÍCH** của chuyến bay (`flight.toPosition/toTarget/toUp/toFov`) làm "camera cũ" rồi hủy chuyến bay (`flight = null` + `syncControls()`), để đúng một nguồn ghi pose. Có test hồi quy "hover bắt đầu GIỮA chuyến bay chuyển cảnh".
  - **Thứ tự `writer` trong log phải theo thứ tự áp pose:** trong một frame engine gọi `update()` (flight) → `updateDolly()` (dolly) → `updateTimeline()` (timeline), nên nguồn ghi **cuối cùng** mới là cái đang điều khiển camera. Log cũ xét `cameraFlying` trước nên báo sai. Có thêm cảnh báo `conflict` cho cặp `flight` + `dolly` (cặp này giờ là bất khả thi — nếu thấy là chuyến bay chưa nhường hover).
  - **Khoảng cách dí gần phải NEO vào pose gốc của chuỗi hover (đã dính — "hover 2 badge liên tiếp thì cộng dồn zoom, mất badge"):** vì `approach` là **tỉ lệ**, nếu đo `distance = camera.position.distanceTo(badge)` từ vị trí camera **hiện tại** thì mỗi lần hover tiếp theo lại nhân thêm `approach` (chuỗi hover ⇒ `approachⁿ`) và camera chui hẳn vào trong model. Tệ hơn, `hoverStart` cũng bị ghi đè mỗi lần vào badge, nên "camera cũ" trôi dần theo từng lần hover chứ không về góc gốc. Fix: cờ `chainActive` — chỉ chụp `hoverStart` **một lần** cho cả chuỗi, và `zoomIntoBadge` đo khoảng cách từ `hoverStart.position` (neo) chứ không từ `camera.position`. Chuỗi chỉ kết thúc khi **chuyến bay VỀ** chạy xong (dolly có cờ `returning`), khi người dùng kéo chuột (`syncPose`), hoặc khi `restore`/`clearDollyTarget`/`releaseDolly` được gọi. Có test hồi quy "hover liên tiếp nhiều badge".
  - **Mặt phẳng cắt gần phải nhỏ hơn khoảng cách hover (đã dính — badge "biến mất" khi dí sát):** `fit()` đặt `camera.near = sphere.radius / 1000`; model Petra có bán kính ~24.618 ⇒ `near ≈ 24,6`, **lớn hơn cả khoảng cách hover (~11)** ⇒ cả quad badge (billboard, `depthTest: false` nên không bị che, nhưng vẫn bị xén theo `near`) biến mất khỏi màn hình. `far = distance + radius * 100` thì rộng vô ích vì không có skybox (`scene.background` chỉ là màu phẳng). Fix: `near = radius / 20000` (~1,23 với Petra) và `far = distance + radius * 2`. Thêm sàn cứng trong `zoomIntoBadge`: `floor = max(target.minDistance, camera.near * 2)` ⇒ dù `approach` có nhỏ tới đâu, badge cũng không bao giờ lọt vào trong `near`. Có test hồi quy "sàn khoảng cách hover không để badge lọt vào trong mặt phẳng cắt gần".
  - **Thao tác chuột luôn thắng:** engine gọi `cameraController.attachPointerListeners(renderer.domElement)` (nghe `pointerdown` ở capture + `pointerup`/`pointercancel` trên `window`) để biết chuột đang kéo; `syncPose()` (gọi mỗi frame sau `controls.update()`) hủy chuyến hover ngay khi người dùng kéo chuột, chốt pose hiện tại làm `home` mới và gọi `syncControls()` để gieo lại trạng thái nội bộ OrbitControls — thiếu bước này `controls.update()` sẽ tính từ spherical cũ và kéo camera giật về pose trước khi hover.
  - **Bẫy vector tạm (đã dính):** pose đích của chuyến hover **không được** là `scratch`. `updateDolly` dùng `scratch.copy(fromPosition).lerp(toPosition, k)`; nếu `toPosition` alias `scratch` thì mỗi frame nó lerp về chính nó ⇒ camera đứng im hoặc bay ra xa. Pose đích phải là `new THREE.Vector3()` riêng.
  - **Chống dao động hover (đã dính — "giật giật bay xa ra"):** camera bay vào làm badge trượt khỏi con trỏ ⇒ raycast trượt ⇒ hover mất ⇒ camera bay về ⇒ badge lại về dưới con trỏ ⇒ bay vào… lặp vô tận (đo được hover lật 14 lần và camera kẹt giữa đường). `tour-engine.onPointerMove` chặn bằng `shouldEvaluateHover()`: (1) bỏ qua khi `cameraController.isApproaching()` (đang trên đường bay TỚI badge — badge đang trượt nên raycast không đáng tin), (2) chỉ đánh giá lại khi con trỏ di chuyển ≥ `HOVER_POINTER_EPSILON = 0.02` NDC, để rung chuột vài pixel không đổi trạng thái hover. Chuyến bay VỀ không bị chặn để người dùng còn hover lại được.
  - **`cameraChanged` phải tính cả `dollyMoved`:** `const cameraChanged = cameraDriven ? false : controls.update();` — nếu chỉ loại trừ `cameraFlying || timelineMoved` thì `controls.update()` vẫn chạy chồng lên chuyến hover mỗi frame.
  - **Sàn `minDistance` phải suy từ pose tác giả, KHÔNG từ bán kính model (đã dính — "hover xong camera bay ra xa"):** OrbitControls có bất biến `minDistance ≤ |camera−target| ≤ maxDistance`; vi phạm là nó kéo camera tới đúng biên ngay frame sau. `fit()` đặt `minDistance = sphere.radius * 0.05`, nhưng model Petra có bán kính rất lớn (gồm địa hình xa, ~25.000) trong khi pose tác giả chỉ ở 28–78 ⇒ sàn ~1.230, gấp ~44 lần pose. Trong lúc bay, `allowPose` tạm hạ sàn nên không thấy; vừa `DONE` là `restoreMinDistance()` khôi phục sàn ⇒ camera vọt ra xa. Fix: `noteAuthoredDistance()` (gọi trong `applyPreset`/`flyToPreset`/`startTimeline`) hạ `fitMinDistance` xuống `nửa khoảng cách pose gần nhất`, và `restoreMinDistance()` luôn kẹp `floor = Math.min(fitMinDistance, khoảng cách hiện tại)`. Đo được: sàn 2165 → 14.14, camera đứng yên 60 frame (bước 0.00).
  - `enterExplore` gọi `adoptCurrentPose()` trước khi vào để góc "về" của `resetExplore`/`exitExplore` là chỗ người dùng đang đứng; `resetExplore`, `exitExplore`, `setInteractiveHighlights` và `useTourPlayer` (trước khi đổi cảnh) gọi `clearDollyTarget()`/`releaseHighlightDolly()` để không giữ chuyến hover qua cảnh mới.
- `three/scene-highlights.ts`: GLB phụ, transform, hiện theo `[startSeconds,endSeconds)` (end null không tắt) và animation `rotate`/GLB clips `LoopRepeat` theo timeline; clone skeleton riêng để không chia sẻ bones.
- `components/ExploreControls.tsx`, `HighlightPanel.tsx`: panel điểm tương tác dựng theo đúng cấu trúc **và CSS** của panel gốc (`playpenInfoParent`):

  ```
  playpenInfoParent                    ← kính: gradient + blur(24px), radius 12%/50%
  ├─ .infoCollapse        (2 icon in/out, NẰM NGOÀI panel ở left:-48px)
  ├─ .hotspotPopupClose   (viên kính tròn 40px, top:20px left:54px, icon_close.svg)
  ├─ .playpenInfo-Title
  ├─ .infoInner           ← vùng CUỘN, max-height: calc(100vh - 160px), scrollbar 3px
  │  ├─ .infoImgGroup     (icon mở rộng chỉ hiện khi hover, ảnh tối đi brightness .6)
  │  ├─ .playpenInfo-Vid  (max-height 35vh, ::cue ẩn caption gốc của trình duyệt)
  │  ├─ .infoProgressBar  (track = .infoProgressFilled bấm để tua; fill trượt lên nhờ margin-bottom:-4px)
  │  ├─ audio
  │  ├─ .infoDescGroup    (.playpenInfo-Desc clamp 7 dòng + bung khi hover; credit 8px italic phải)
  │  └─ .infoDescButtons  (Read More / Read Less)
  └─ .infoTracker         ← absolute left:19px right:0 bottom:15px, NGOÀI vùng cuộn
  ```

  Bẫy đã dính, dễ tái phạm:
  - **`styles.visited` là class không tồn tại.** CSS chỉ có `.orbTracker-circle.visited`, component lại dùng `styles.visited` ⇒ CSS Module trả `undefined`, className thành chuỗi `"undefined"` và **chấm đã khám phá không bao giờ đổi màu**. Đã đổi thành `.orbTracker-circle.orbVisited`.
  - **Không được đặt `background-color` đặc cho `.hotspotPopup.playpenInfoParent`.** Bản cũ đặt `rgba(28,27,26,.72)`, phủ mất gradient + `backdrop-filter` của `.playpenInfoParent` ⇒ panel mất hiệu ứng kính.
  - **Độ ưu tiên:** `.hotspotPopup h2` / `.hotspotPopup p` / `.hotspotPopupMedia` (0,1,1) **thắng** `.playpenInfo-Title` / `.playpenInfo-Desc` (0,1,0). Nên `.infoInner .playpenInfo-Desc` và `.hotspotPopup.playpenInfoParent h2` phải nêu lại giá trị gốc; `.hotspotPopupMedia` phải nêu lại cả `max-height`/`margin`/`object-fit` nếu không sẽ dính `max-height:160px` của khối cũ.
  - **`display: flex` đè `[hidden]` của UA** — `.infoInner` và `.hotspotPopupClose` đều cần rule `[hidden] { display: none; }` riêng.
  - **Icon mở rộng neo giữa ảnh** nhờ `position: absolute` không kèm offset, mà muốn vậy thì tổ tiên gần nhất phải là flex-center (`.infoImageButton`).
  - `.playpenInfo-Desc:hover` của bản gốc bung clamp; nút Read More / Read Less là đường dự phòng cho bàn phím và cảm ứng — bản gốc ẩn hẳn nhóm nút (`#playpenInfo-DescButtonGroup { display: none !important }`), ở đây **cố ý giữ lại**.

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
