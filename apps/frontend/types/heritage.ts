/**
 * Shared types for the Heritage 3D tour.
 *
 * Mirrors 1:1 the backend response schemas in
 * `apps/backend/schemas/heritage.py` (HeritageContentOut).
 *
 * Contract — `GET /api/heritages/{slug}` returns:
 *   { heritage, overview, scenes[] }
 *   - overview  : the intro scene (sequence -1), slug "s0"
 *   - scenes    : regular scenes (sequence 0..N-1), slug "s1".."sN"
 */

// ── Leaf types (no forward refs) ─────────────────────────────────────────────

export interface HeritageLanguage {
  code: string;
  name: string;
}

export interface HeritageVoice {
  id: number;
  name: string;
  title: string | null;
  bio: string | null;
  headshot_url: string | null;
  intro_video_url: string | null;
}

export interface HeritageModelAsset {
  id: number;
  file_url: string;
  format: string;
  lod_level: number;
  compression: string | null;
  file_size_bytes: number | null;
}

export interface HeritageSkyPreset {
  id: number;
  name: string;
  turbidity: number | null;
  rayleigh: number | null;
  elevation: number | null;
  azimuth: number | null;
  exposure: number | null;
  /**
   * Các tham số tán xạ bổ sung của shader Sky (bản gốc có trong `threeJS_skySet`
   * nhưng bảng `sky_preset` chưa lưu ⇒ để optional, thiếu thì dùng mặc định của
   * three.js). `mieDirectionalG` bị đánh vần sai (`mieDirctionalG`) trong dữ liệu
   * nguồn nên bộ nạp dữ liệu phải chấp nhận cả hai khoá.
   */
  mieCoefficient?: number | null;
  mieDirectionalG?: number | null;
  /** Mây — `Sky` của three r186 dựng được trực tiếp từ hai tham số này. */
  cloudCoverage?: number | null;
  cloudDensity?: number | null;
  /** Sao đêm: shader riêng của bản gốc, chưa dựng lại — giữ để dành. */
  stars?: number | null;
  /**
   * Mật độ sương mù (`FogExp2`). Bản gốc để ở `threeJS_sets.fog_density` chứ
   * không nằm trong preset; thiếu thì không dựng sương mù.
   */
  fogDensity?: number | null;
  light_settings: Record<string, unknown> | null;
}

export interface HeritageCamera {
  node_name: string | null;
  start_position: number[] | Record<string, number> | null;
  start_target: number[] | Record<string, number> | null;
  zoom_position: number[] | Record<string, number> | null;
  zoom_target: number[] | Record<string, number> | null;
  instant_move: boolean;
}

export interface HeritageVoiceClip {
  id: number;
  video_url: string | null;
  audio_url: string | null;
  bubble_text: string | null;
  sort_order: number;
  voice: HeritageVoice;
}

export interface HeritageMediaItem {
  id: number;
  type: string;
  title: string | null;
  caption: string | null;
  asset_url: string;
  thumb_url: string | null;
  credit: string | null;
  sort_order: number;
}

export interface HeritageInteractiveHighlight {
  id: number;
  popup_title: string | null;
  popup_text: string | null;
  /** Thumbnail từ tour nguồn; API backend hiện chưa trả trường này. */
  thumb_url?: string | null;
  media_url: string | null;
  /** Metadata popup từ tour nguồn; optional để tương thích API backend cũ. */
  media_type?: string | null;
  media_alt?: string | null;
  media_credit?: string | null;
  captions_url?: string | null;
  audio_url?: string | null;
  cam_pos: number[] | Record<string, number> | null;
  cam_target: number[] | Record<string, number> | null;
  lens_pos: number[] | Record<string, number> | null;
  lens_rot: number[] | Record<string, number> | null;
  lens_scale: number[] | Record<string, number> | null;
  sort_order: number;
}


export interface ExploreArea {
  center: number[];
  extents: number[];
  rotation: number[];
}

export interface HeritageInteractive {
  id: number;
  mode: string;
  cam_pos: number[] | Record<string, number> | null;
  cam_target: number[] | Record<string, number> | null;
  explore_area: ExploreArea | string | null;
  explore_title?: string | null;
  explore_description?: string | null;
  highlights: HeritageInteractiveHighlight[];
}

export interface HeritageSceneHighlight {
  id: number;
  model_url: string;
  position: number[] | Record<string, number>;
  rotation: number[] | Record<string, number>;
  scale: number[] | Record<string, number>;
  animation_type: string | null;
}


export interface HeritageScene {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  sequence: number;
  sky: HeritageSkyPreset | null;
  camera: HeritageCamera;
  voice_clips: HeritageVoiceClip[];
  models: HeritageModelAsset[];
  media: HeritageMediaItem[];
  interactive: HeritageInteractive[];
  highlights: HeritageSceneHighlight[];
}


export interface HeritageSummary {
  id: number;
  slug: string;
  title: string;
  tagline: string | null;
  description: string | null;
  region: string | null;
  lat: number | null;
  lng: number | null;
  duration_seconds: number | null;
  launch_date: string | null;
  publish_state: string;
  publish_date: string | null;
  headline: string | null;
  map_zoom: number | null;
  hover_video_url: string | null;
  community_made: boolean;
  presented_by_logo_url: string | null;
  display_map: boolean;
  splash_image_url: string | null;
  card_image_url: string | null;
  language1: HeritageLanguage | null;
  language2: HeritageLanguage | null;
  voices: HeritageVoice[];
  voice_length: number;
}


export interface HeritagePayload {
  heritage: HeritageSummary;
  overview: HeritageScene | null;
  scenes: HeritageScene[];
}
