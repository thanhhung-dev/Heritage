import type { HeritagePayload, HeritageScene } from "@/types/heritage";

/**
 * Demo payload embededed in the frontend so the tour UI renders immediately
 * during development, without needing the backend API / database.
 *
 * The real payload (fetched in the background) replaces this once available.
 */
const demoQuotes = [
  "Chúng ta bắt đầu hành trình khám phá di sản.",
  "Chi tiết này kể một câu chuyện dài hơn.",
  "Hãy nhìn thật kỹ vào từng đường nét.",
];

function demoScene(
  sequence: number,
  title: string,
  description: string,
  bubble: string
): HeritageScene {
  const index = sequence < 0 ? 0 : sequence;
  return {
    id: 1000 + sequence,
    slug: sequence === -1 ? "s0" : `s${sequence + 1}`,
    title,
    description,
    sequence,
    sky: {
      id: 1,
      name: "midday",
      turbidity: 10.0,
      rayleigh: 2.0,
      elevation: 45.0,
      azimuth: 180.0,
      exposure: 1.0,
      light_settings: null,
    },
    camera: {
      node_name: "Camera_Main",
      start_position: [1.0, 1.5, 6.0],
      start_target: [0.0, 1.0, 0.0],
      zoom_position: [0.5, 1.0, 3.0],
      zoom_target: [0.0, 1.0, 0.0],
      instant_move: sequence === -1,
    },
    voice_clips: [
      {
        id: 2000 + sequence,
        video_url: null,
        audio_url: null,
        bubble_text: bubble,
        sort_order: 0,
        voice: {
          id: 1,
          name: "Nguyen Minh Anh",
          title: "Hue Heritage Guide",
          bio: "A local heritage guide.",
          headshot_url: "https://i.pravatar.cc/120?img=11",
          intro_video_url: null,
        },
      },
      {
        id: 2001 + sequence,
        video_url: null,
        audio_url: null,
        bubble_text: `${bubble} (2)`,
        sort_order: 1,
        voice: {
          id: 2,
          name: "Dr. Tran Quoc Bao",
          title: "Historian & Heritage Researcher",
          bio: "Researcher of Nguyen dynasty history.",
          headshot_url: "https://i.pravatar.cc/120?img=25",
          intro_video_url: null,
        },
      },
    ],
    models: [
      {
        id: 3000 + sequence,
        file_url: "https://cdn.example.com/models/scene.glb",
        format: "glb",
        lod_level: 0,
        compression: null,
        file_size_bytes: null,
      },
    ],
    media: [
      {
        id: 4000 + sequence,
        type: "image",
        title: `${title} photo`,
        caption: null,
        asset_url: "https://picsum.photos/seed/scene3840/1600/900",
        thumb_url: "https://picsum.photos/seed/scene320/220",
        credit: null,
        sort_order: 0,
      },
    ],
    interactive: [],
    highlights: [],
  };
}

export const DEMO_HERITAGE_PAYLOAD: HeritagePayload = {
  heritage: {
    id: 1,
    slug: "demo",
    title: "Lăng Tự Đức",
    tagline: "Một ốc đảo thơ mộng giữa lòng Huế",
    description:
      "Lăng Tự Đức là khu lăng của vua Tự Đức, được xây vào thế kỷ 19.",
    region: "Huế, Việt Nam",
    lat: 16.4359,
    lng: 107.5652,
    duration_seconds: 2400,
    launch_date: "2026-01-01",
    publish_state: "published",
    publish_date: "2026-01-01",
    headline: "Bước vào nơi vua Tự Đức làm thơ",
    map_zoom: 12,
    hover_video_url: null,
    community_made: false,
    presented_by_logo_url: null,
    display_map: true,
    splash_image_url: "https://picsum.photos/seed/tuduc1600/1600/900",
    card_image_url: "https://picsum.photos/seed/tuduc800/800/600",
    language1: { code: "vi", name: "Vietnamese" },
    language2: null,
    voices: [
      {
        id: 1,
        name: "Nguyen Minh Anh",
        title: "Hue Heritage Guide",
        bio: "A local heritage guide.",
        headshot_url: "https://i.pravatar.cc/120?img=11",
        intro_video_url: null,
      },
      {
        id: 2,
        name: "Dr. Tran Quoc Bao",
        title: "Historian & Heritage Researcher",
        bio: "Researcher of Nguyen dynasty history.",
        headshot_url: "https://i.pravatar.cc/120?img=25",
        intro_video_url: null,
      },
    ],
    voice_length: 2,
  },
  overview: demoScene(
    -1,
    "Lăng Tự Đức",
    "Giới thiệu toàn cảnh khu lăng mộ thơ mộng của vua Tự Đức.",
    demoQuotes[0]
  ),
  scenes: [
    demoScene(0, "Hồ Lưu Khiêm", "Mặt hồ tĩnh lặng soi bóng thuyền câu.", demoQuotes[1]),
    demoScene(1, "Điện Hòa Khiêm", "Nơi vua ngự trị và làm thơ.", demoQuotes[2]),
    demoScene(2, "Xung Khiêm Tạ", "Ngôi nhà nhỏ giữa vườn thông.", demoQuotes[0]),
    demoScene(3, "Khiêm Cung Môn", "Cổng vào khu vực mộ.", demoQuotes[1]),
  ],
};