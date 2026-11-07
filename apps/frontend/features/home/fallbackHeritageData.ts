import type { HeritageItem } from "@/services/heritage.service";

export const FALLBACK_HERITAGE_ITEMS: HeritageItem[] = [
  {
    id: 1,
    slug: "lang-tu-duc",
    title: "Lăng Tự Đức",
    region: "Huế",
    card_image_url:
      "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1200&q=80",
    splash_image_url:
      "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1200&q=80",
    publish_date: "2025-01-01T00:00:00Z",
    language1: { code: "vi", name: "Tiếng Việt" },
    description:
      "Khám phá Khiêm Lăng, công trình gắn liền với vua Tự Đức, thông qua không gian 3D, văn bia Khiêm Cung Ký và khu lăng mộ.",
    voices: [
      {
        id: 101,
        name: "Ngọc Ngân",
        title: "Người thuyết minh tiếng Việt",
        headshot_url:
          "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 102,
        name: "Lê Văn Hùng",
        title: "Nhà nghiên cứu văn hóa Huế",
        headshot_url:
          "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 103,
        name: "Trần Mai Phương",
        title: "Nghệ nhân nhã nhạc cung đình",
        headshot_url:
          "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&h=100&q=80",
      },
    ],
  },
  {
    id: 2,
    slug: "cung-an-dinh",
    title: "Cung An Định",
    region: "Huế",
    card_image_url:
      "https://images.unsplash.com/photo-1583417319070-4a69db38a482?auto=format&fit=crop&w=1200&q=80",
    splash_image_url:
      "https://images.unsplash.com/photo-1583417319070-4a69db38a482?auto=format&fit=crop&w=1200&q=80",
    publish_date: "2025-01-01T00:00:00Z",
    language1: { code: "vi", name: "Tiếng Việt" },
    description:
      "Cung An Định được vua Khải Định cho xây dựng đầu thế kỷ 20 bên bờ sông An Cựu, mang kiến trúc cung đình kết hợp phong cách châu Âu. Sau này cung gắn liền với cuộc đời Nam Phương hoàng hậu – vị hoàng hậu cuối cùng của Việt Nam.",
    voices: [
      {
        id: 201,
        name: "Nguyễn Hoàng Nam",
        title: "Chuyên viên bảo tồn di tích Cố đô",
        headshot_url:
          "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 202,
        name: "Lê Văn Hùng",
        title: "Nhà nghiên cứu văn hóa Huế",
        headshot_url:
          "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 203,
        name: "Trần Mai Phương",
        title: "Nghệ nhân nhã nhạc cung đình",
        headshot_url:
          "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&h=100&q=80",
      },
    ],
  },
  {
    id: 3,
    slug: "ngu-hanh-son",
    title: "Ngũ Hành Sơn",
    region: "Đà Nẵng",
    card_image_url:
      "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80",
    splash_image_url:
      "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80",
    publish_date: "2025-01-01T00:00:00Z",
    language1: { code: "vi", name: "Tiếng Việt" },
    description:
      "Quần thể gồm sáu ngọn núi đá vôi nhô lên trên một bãi cát ven biển, nổi tiếng với các hang động huyền bí và làng đá mỹ nghệ truyền thống Non Nước.",
    voices: [
      {
        id: 301,
        name: "Phạm Quốc Bảo",
        title: "Thuyết minh viên danh thắng Non Nước",
        headshot_url:
          "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 302,
        name: "Lê Văn Hùng",
        title: "Nhà nghiên cứu văn hóa dân gian",
        headshot_url:
          "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
      },
    ],
  },
];
