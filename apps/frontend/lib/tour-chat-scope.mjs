// Explicit route identities mirror the backend's server-owned area registry.
// Never infer scope from a free-form tour title or the visitor's question.
const AREAS = [
  { id: "khiem-lang", title: "Khiêm Lăng (Lăng Tự Đức)", slugs: ["khiem-lang", "lang-tu-duc", "tu-duc-tomb"] },
  { id: "lang-minh-mang", title: "Lăng Minh Mạng", slugs: ["lang-minh-mang", "minh-mang-tomb"] },
  { id: "dai-noi-hue", title: "Đại Nội Huế", slugs: ["dai-noi-hue", "forbidden-city", "imperial-city"] },
  { id: "lang-khai-dinh", title: "Lăng Khải Định", slugs: ["lang-khai-dinh", "khai-dinh-tomb"] },
  { id: "chua-thien-mu", title: "Chùa Thiên Mụ", slugs: ["chua-thien-mu", "thien-mu-pagoda"] },
];

// Extra display-name aliases supplement the route identities above. The backend
// remains the enforcement boundary; this guard avoids offering misleading chips
// when a story's metadata explicitly describes a different destination.
const PLACE_ALIASES = {
  "khiem-lang": ["Khiêm Cung", "Vạn Niên Cơ"],
  "lang-minh-mang": ["Lăng Minh Mệnh", "Hiếu Lăng"],
  "dai-noi-hue": ["Đại Nội", "Hoàng thành Huế", "Hoàng thành Nhà Nguyễn", "Hue Imperial City"],
  "lang-khai-dinh": ["Ứng Lăng"],
  "chua-thien-mu": ["Chùa Linh Mụ"],
};

function normalizedPlace(value) {
  return ` ${value.toLowerCase().replaceAll("đ", "d").normalize("NFKD")
    .replace(/[\u0300-\u036f\u200b-\u200f\ufeff]/g, "").replace(/[^a-z0-9]+/g, " ").trim()} `;
}

/** @param {string} text @param {string} activeAreaId */
export function mentionsOtherTourArea(text, activeAreaId) {
  const content = normalizedPlace(text);
  return AREAS.filter((area) => area.id !== activeAreaId).some((area) => (
    [area.title, ...area.slugs, ...PLACE_ALIASES[area.id]].some((name) => content.includes(normalizedPlace(name)))
  ));
}

/** @param {string} slug */
export function resolveTourArea(slug) {
  return AREAS.find((area) => area.slugs.includes(slug.toLowerCase())) ?? null;
}

/** @param {{title: string}} area */
export function tourQuestions(area) {
  return [
    `Giới thiệu tổng quan về ${area.title}.`,
    `Lịch sử hình thành ${area.title} như thế nào?`,
    `Kiến trúc của ${area.title} có gì đặc sắc?`,
  ];
}

/**
 * Reject old deployments that silently ignore active_area_id, and responses
 * from another tour. Sources also need explicit area provenance.
 * @param {Record<string, unknown>} data
 * @param {string} expectedArea
 * @returns {string[]}
 */
export function validateTourReply(data, expectedArea) {
  if (data.active_area_id !== expectedArea || !AREAS.some((area) => area.id === expectedArea)) {
    throw new Error("Máy chủ chưa xác nhận đúng khu vực tham quan. Vui lòng cập nhật backend hỗ trợ khóa khu vực.");
  }
  const kinds = ["answered", "conversation", "insufficient_evidence", "out_of_scope"];
  if (typeof data.answer_type !== "string" || !kinds.includes(data.answer_type)
      || !Array.isArray(data.sources) || !Array.isArray(data.follow_up_questions)
      || data.follow_up_questions.length > 3
      || data.sources.some((source) => !source || source.active_area_id !== expectedArea)
      || (data.answer_type === "answered" ? data.sources.length === 0 : data.sources.length > 0)) {
    throw new Error("Phản hồi hướng dẫn viên không có phạm vi hoặc trích dẫn hợp lệ.");
  }
  /** @type {string[]} */
  const questions = [];
  for (const value of data.follow_up_questions) {
    if (typeof value !== "string" || !value.trim() || value.length > 200) {
      throw new Error("Câu hỏi gợi ý không đúng định dạng.");
    }
    questions.push(value);
  }
  return questions;
}
