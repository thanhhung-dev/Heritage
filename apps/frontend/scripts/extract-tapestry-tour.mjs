import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

// Chỉ đọc JSON nhúng; không thực thi script của trang HTML.
export function extractTour(html) {
  const block = html.match(/<script id="tapestry-data" type="application\/json">([\s\S]*?)<\/script>/);
  if (!block) throw new Error("Không tìm thấy tapestry-data.");
  const { t } = JSON.parse(block[1]);
  const set = t.threeJS_sets[t.threeJS.set_id];
  const vector = (value) => {
    if (value == null) return null;
    const xyz = value.split(",").map(Number);
    if (xyz.length !== 3 || !xyz.every(Number.isFinite)) throw new Error(`Tọa độ không hợp lệ: ${value}`);
    return xyz;
  };
  const voice = (v) => ({
    id: v.voice_id, name: v.voice_name, title: v.voice_title, bio: v.voice_bio,
    headshot_url: v.voice_headshot, intro_video_url: v.voice_intro_video,
  });
  const playback = {};
  function scene(s, overview = false) {
    const id = overview ? s.overview_id : s.scene_id;
    const sequence = overview ? -1 : Number(s.scene_sequence) - 1;
    const slug = `s${sequence + 1}`;
    const highlightMeta = overview ? t.sceneHighlights_overview[id] : t.sceneHighlights[id];
    const highlightModels = overview ? t.threeJS_scene_highlights_overview[id] : t.threeJS_scene_highlights[id];
    const highlights = (highlightMeta ?? []).map((h) => {
      const model = highlightModels?.[h.scene_highlight_id];
      if (!model) throw new Error(`Thiếu model highlight ${h.scene_highlight_id}`);
      return {
        id: h.scene_highlight_id, model_url: model.highlight_model_url,
        position: vector(model.highlight_position), rotation: vector(model.highlight_rotation), scale: vector(model.highlight_scale),
        animation_type: model.animation_type, startSeconds: h.start_time, endSeconds: h.end_time,
      };
    });
    const interactives = overview ? [] : t.interactives.filter((i) => i.interactive_id === s.interactive_id);
    playback[slug] = {
      narrationUrl: s.audio_narration_1, captionsUrl: s.narration_cc_1, timedHighlights: highlights,
      exploreArea: interactives[0]?.explore_area ? JSON.parse(interactives[0].explore_area) : null,
    };
    return {
      id, slug, title: overview ? s.title : s.scene_title,
      description: overview ? s.description : s.scene_desciption, sequence, sky: null,
      camera: {
        node_name: null, start_position: vector(overview ? s.camera_position : s.start_camera_position),
        start_target: vector(overview ? s.camera_target : s.start_camera_target),
        zoom_position: vector(s.zoom_camera_position), zoom_target: vector(s.zoom_camera_target), instant_move: !!s.instant_move,
      },
      voice_clips: (overview ? [] : t.sceneVoices.filter((v) => v.scene_id === id)).map((v, index) => ({
        id: v.voice_clip_id, video_url: v.voice_video ?? null, audio_url: null,
        bubble_text: v.voice_bubble_text, sort_order: index, voice: voice(v),
      })),
      models: [],
      media: (overview ? [] : t.mediaItems.filter((m) => m.scene_id === id)).map((m) => ({
        id: m.media_id, type: m.media_type, title: m.media_title, caption: m.media_caption,
        asset_url: m.media_asset_link, thumb_url: m.media_asset_thumb_link, credit: m.media_credit, sort_order: m.media_order ?? 0,
      })),
      interactive: interactives.map((i) => ({
        id: i.interactive_id, mode: i.interactive_mode, cam_pos: vector(i.camera_position), cam_target: vector(i.camera_target),
        explore_area: null, // OBB nguồn được giữ trong playback.exploreArea; controller chưa áp collision.
        highlights: t.interactiveHighlights.filter((h) => h.interactive_id === i.interactive_id).map((h) => {
          const lens = t.threeJS_int_highlights[h.interactive_highlight_id];
          return {
            id: h.interactive_highlight_id, popup_title: h.popup_title, popup_text: h.popup_text,
            thumb_url: h.highlight_thumbnail ?? null,
            media_type: h.popup_media_type ?? null, media_alt: h.popup_media_alt_desc ?? null,
            media_credit: h.popup_media_credit ?? null, captions_url: h.popup_video_cc_1 ?? null,
            audio_url: h.popup_audio_link ?? null,
            media_url: h.popup_media_link, cam_pos: vector(h.camera_position), cam_target: vector(h.camera_target),
            lens_pos: vector(lens?.lens_position), lens_rot: vector(lens?.lens_rotation), lens_scale: vector(lens?.lens_scale),
            sort_order: h.highlight_order,
          };
        }),
      })),
      highlights: highlights.map(({ startSeconds, endSeconds, ...model }) => model),
    };
  }
  const overview = scene(t.overview, true);
  const scenes = [...t.scenes].sort((a, b) => Number(a.scene_sequence) - Number(b.scene_sequence)).map((s) => scene(s));
  return {
    source: "Tapestry/CyArk — tapestry.html, chỉ dùng kiểm thử; asset vẫn nằm trên CDN nguồn",
    modelUrl: set.asset,
    payload: {
      heritage: {
        id: t.tapestry.tapestry_id, slug: "tapestry-test", title: t.tapestryTitle, tagline: t.tapestryTagline,
        description: t.tapestrySnippet, region: t.tapestryLocation, lat: t.tapestryLatitude, lng: t.tapestryLongitude,
        duration_seconds: t.tapestryDuration * 60, launch_date: t.tapestry.launch_date,
        publish_state: "preview", publish_date: null, headline: t.tapestryHeadline, map_zoom: t.tapestryMapZoom,
        hover_video_url: t.tapestryHoverVideo, community_made: !!t.communityMade, presented_by_logo_url: t.presentedByLogo,
        display_map: !!t.displayMap, splash_image_url: t.splashImage, card_image_url: t.tapestryCardImage,
        language1: { code: "en", name: "English" }, language2: { code: "ar", name: "Arabic" },
        voices: t.voices.map(voice), voice_length: t.voices.length,
      },
      overview, scenes,
    },
    playback,
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const html = await readFile(new URL("../features/tour/tapestry.html", import.meta.url), "utf8");
  const tour = extractTour(html);
  await writeFile(new URL("../features/tour/tour.json", import.meta.url), `${JSON.stringify(tour, null, 2)}\n`);
  console.log(`Đã tạo tour.json: ${tour.payload.scenes.length} scene, model ${tour.modelUrl}`);
}
