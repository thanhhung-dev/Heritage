export interface TourArea {
  id: string;
  title: string;
  slugs: string[];
}

// Explicit route identities mirror the backend's server-owned area registry.
// Never infer scope from a free-form tour title or the visitor's question.
const AREAS: TourArea[] = [
  { id: "khiem-lang", title: "Khiêm Lăng (Lăng Tự Đức)", slugs: ["khiem-lang", "lang-tu-duc", "tu-duc-tomb"] },
  { id: "lang-minh-mang", title: "Lăng Minh Mạng", slugs: ["lang-minh-mang", "minh-mang-tomb"] },
  { id: "dai-noi-hue", title: "Đại Nội Huế", slugs: ["dai-noi-hue", "forbidden-city", "imperial-city"] },
  { id: "lang-khai-dinh", title: "Lăng Khải Định", slugs: ["lang-khai-dinh", "khai-dinh-tomb"] },
  { id: "chua-thien-mu", title: "Chùa Thiên Mụ", slugs: ["chua-thien-mu", "thien-mu-pagoda"] },
];

// Extra display-name aliases supplement the route identities above. The backend
// remains the enforcement boundary; this guard avoids offering misleading chips
// when a story's metadata explicitly describes a different destination.
const PLACE_ALIASES: Record<string, string[]> = {
  "khiem-lang": ["Khiêm Cung", "Vạn Niên Cơ"],
  "lang-minh-mang": ["Lăng Minh Mệnh", "Hiếu Lăng"],
  "dai-noi-hue": ["Đại Nội", "Hoàng thành Huế", "Hoàng thành Nhà Nguyễn", "Hue Imperial City"],
  "lang-khai-dinh": ["Ứng Lăng"],
  "chua-thien-mu": ["Chùa Linh Mụ"],
};

function normalizedPlace(value: string): string {
  return ` ${value
    .toLowerCase()
    .replaceAll("đ", "d")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f\u200b-\u200f\ufeff]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()} `;
}

export function mentionsOtherTourArea(text: string, activeAreaId: string): boolean {
  const content = normalizedPlace(text);
  return AREAS.filter((area) => area.id !== activeAreaId).some((area) => {
    const aliases = PLACE_ALIASES[area.id] ?? [];
    return [area.title, ...area.slugs, ...aliases].some((name) =>
      content.includes(normalizedPlace(name)),
    );
  });
}

export function resolveTourArea(slug: string): TourArea | null {
  return AREAS.find((area) => area.slugs.includes(slug.toLowerCase())) ?? null;
}

export function tourQuestions(area: Pick<TourArea, "title">): string[] {
  return [
    `Giới thiệu tổng quan về ${area.title}.`,
    `Lịch sử hình thành ${area.title} như thế nào?`,
    `Kiến trúc của ${area.title} có gì đặc sắc?`,
  ];
}

export interface TourReplySource {
  active_area_id?: string;
  [key: string]: unknown;
}

export interface TourReplyData {
  active_area_id?: unknown;
  answer_type?: unknown;
  sources?: unknown;
  follow_up_questions?: unknown;
  [key: string]: unknown;
}

/**
 * Reject old deployments that silently ignore active_area_id, and responses
 * from another tour. Sources also need explicit area provenance.
 */
export function validateTourReply(
  data: TourReplyData | Record<string, unknown>,
  expectedArea: string,
): string[] {
  if (data.active_area_id !== expectedArea || !AREAS.some((area) => area.id === expectedArea)) {
    throw new Error(
      "Máy chủ chưa xác nhận đúng khu vực tham quan. Vui lòng cập nhật backend hỗ trợ khóa khu vực.",
    );
  }
  const kinds = [
    "answered",
    "conversation",
    "clarification",
    "suggestion",
    "insufficient_evidence",
    "out_of_scope",
  ];
  if (
    typeof data.answer_type !== "string" ||
    !kinds.includes(data.answer_type) ||
    !Array.isArray(data.sources) ||
    !Array.isArray(data.follow_up_questions) ||
    data.follow_up_questions.length > 3 ||
    data.sources.some(
      (source: unknown) =>
        !source ||
        typeof source !== "object" ||
        (source as TourReplySource).active_area_id !== expectedArea,
    ) ||
    (data.answer_type === "answered" ? data.sources.length === 0 : data.sources.length > 0)
  ) {
    throw new Error("Phản hồi hướng dẫn viên không có phạm vi hoặc trích dẫn hợp lệ.");
  }

  const questions: string[] = [];
  for (const value of data.follow_up_questions) {
    if (typeof value !== "string" || !value.trim() || value.length > 200) {
      throw new Error("Câu hỏi gợi ý không đúng định dạng.");
    }
    questions.push(value);
  }
  return questions;
}
