/** SFX giao diện dùng chung; ambience vẫn lấy từ dữ liệu từng di sản. */
export const TOUR_SFX = {
  transition: {
    url: "https://tapestry.cyark.org/audio/general/new_whoosh.mp3",
    volume: 1,
  },
  exploreReveal: {
    url: "https://tapestry.cyark.org/audio/general/explore_more.mp3",
    volume: 0.2,
    delayMs: 700,
  },
} as const;
