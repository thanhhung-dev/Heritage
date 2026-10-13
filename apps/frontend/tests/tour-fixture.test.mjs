import assert from "node:assert/strict";
import test from "node:test";
import { extractTour } from "../scripts/extract-tapestry-tour.mjs";

test("trích đúng model, thứ tự scene, camera và highlight từ các bảng có ID khác nhau", () => {
  const t = {
    tapestry: { tapestry_id: 163 },
    threeJS: { set_id: 4 },
    threeJS_sets: { 1: { asset: "/wrong.glb" }, 4: { asset: "/petra.glb" } },
    overview: { overview_id: 100, camera_position: "72.361,41.244,-30.673", camera_target: "-4.888,22.009,8.943", audio_narration_1: "/intro.mp3", narration_cc_1: "/intro.vtt" },
    scenes: [
      { scene_id: 616, scene_sequence: "2", interactive_id: 88, start_camera_position: "46.15,7.356,-24.088", start_camera_target: "14.54,8.074,-1.886" },
      { scene_id: 617, scene_sequence: "1", interactive_id: null },
    ],
    voices: [], sceneVoices: [], mediaItems: [],
    sceneHighlights_overview: {}, threeJS_scene_highlights_overview: {},
    sceneHighlights: { 616: [{ scene_highlight_id: 77, start_time: 5, end_time: null }] },
    threeJS_scene_highlights: { 616: { 77: { highlight_model_url: "/detail.glb", highlight_position: "1,2,-3", highlight_rotation: "0,0.5,0", highlight_scale: "1,2,1", animation_type: "LoopRepeat" } } },
    interactives: [{ interactive_id: 88, camera_position: "3,7,-2", camera_target: "0,2,1", explore_area: JSON.stringify({ center: [1, 2, 3], extents: [4, 5, 6], rotation: [0, 0, 0, 1] }) }],
    interactiveHighlights: [
      { interactive_id: 89, interactive_highlight_id: 777, popup_title: "Không thuộc scene này", highlight_thumbnail: "/wrong.webp" },
      { interactive_id: 88, interactive_highlight_id: 778, popup_title: "Niches", highlight_thumbnail: "/niches.webp", highlight_order: 2, camera_position: "2,3,4", camera_target: "-1,5,7" },
    ],
    threeJS_int_highlights: { 778: { lens_position: "-6.343,25.314,7.299", lens_scale: "25,25,25" } },
  };
  const html = () => `<script>throw new Error('không được chạy');</script><script id="tapestry-data" type="application/json">${JSON.stringify({ t })}</script>`;
  const tour = extractTour(html());
  assert.equal(tour.modelUrl, "/petra.glb");
  assert.deepEqual(tour.payload.scenes.map((s) => s.id), [617, 616]);
  assert.deepEqual(tour.payload.overview.camera.start_position, [72.361, 41.244, -30.673]);
  assert.deepEqual(tour.payload.scenes[1].camera.start_target, [14.54, 8.074, -1.886]);
  const interactive = tour.payload.scenes[1].interactive[0];
  assert.equal(interactive.highlights.length, 1);
  assert.equal(interactive.highlights[0].id, 778);
  assert.equal(interactive.highlights[0].thumb_url, "/niches.webp");
  assert.equal(interactive.highlights[0].sort_order, 2);
  assert.deepEqual(interactive.highlights[0].lens_pos, [-6.343, 25.314, 7.299]);
  assert.deepEqual(interactive.highlights[0].cam_target, [-1, 5, 7]);
  assert.equal(tour.playback.s2.timedHighlights[0].model_url, "/detail.glb");
  assert.equal(tour.playback.s2.timedHighlights[0].startSeconds, 5);
  assert.equal(tour.playback.s2.timedHighlights[0].endSeconds, null);
  assert.deepEqual(tour.playback.s2.exploreArea.extents, [4, 5, 6]);
  assert.equal(tour.playback.s0.narrationUrl, "/intro.mp3");
  assert.equal(tour.playback.s0.captionsUrl, "/intro.vtt");
  delete t.interactiveHighlights[1].highlight_thumbnail;
  assert.equal(extractTour(html()).payload.scenes[1].interactive[0].highlights[0].thumb_url, null);
  t.scenes[0].start_camera_position = "NaN,2,3";
  assert.throws(() => extractTour(html()), /Tọa độ không hợp lệ/);
});
