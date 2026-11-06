import { tourQuestions } from "./tour-chat-scope.mjs";

/** @typedef {{ label: string, value: string }} SceneSuggestion */
/** @typedef {{ id: string, title: string }} TourArea */
/** @typedef {{ title: string, description?: string | null }} Story */

function plainText(value, limit) {
  if (typeof value !== "string") return "";
  return value.replace(/<[^>]*>/g, " ").replace(/https?:\/\/\S+/gi, "")
    .replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, limit);
}

function folded(value) {
  return value.toLowerCase().replaceAll("đ", "d").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

// These templates ask about topics present in the story metadata; they do not
// assert dates, people, construction details or other unverified historical facts.
const TOPICS = [
  { matches: /\b(bia da|van bia|khiem cung ky|stele|inscription)\b/,
    label: "Ý nghĩa văn bia", question: "Văn bia được nhắc đến có ý nghĩa gì" },
  { matches: /\b(nha vua|tu duc|cuoc doi|nhan vat|hoang de|emperor|king)\b/,
    label: "Nhân vật trong chuyện", question: "Nhân vật được nhắc đến có vai trò gì" },
  { matches: /\b(kien truc|cong|dien|cot|mai|architecture|gate|pavilion)\b/,
    label: "Chi tiết kiến trúc", question: "Có những chi tiết kiến trúc nào đáng chú ý" },
  { matches: /\b(ho|sen|dao|canh quan|vuon|lake|garden|landscape)\b/,
    label: "Cảnh quan nơi này", question: "Cảnh quan có vai trò gì" },
  { matches: /\b(lich su|hinh thanh|xay dung|history|construction)\b/,
    label: "Bối cảnh lịch sử", question: "Bối cảnh lịch sử được giải thích như thế nào" },
  { matches: /\b(bao ton|giu gin|preservation|conservation)\b/,
    label: "Gìn giữ di sản", question: "Việc gìn giữ di sản được nhắc đến như thế nào" },
];

/**
 * Produce render-time suggestions from the active story, independent of model
 * response state. An old response can never restore an earlier story's chips.
 * @param {TourArea | null} area
 * @param {Story | null} scene
 * @param {string} sceneKey
 * @returns {{ contextLabel: string | null, suggestions: SceneSuggestion[] }}
 */
export function buildSceneChatSuggestions(area, scene, sceneKey) {
  if (!area) return { contextLabel: null, suggestions: [] };
  if (!scene) return {
    contextLabel: null,
    suggestions: tourQuestions(area).map((value) => ({ label: value, value })),
  };

  const key = plainText(sceneKey, 12);
  const title = plainText(scene.title, 64) || `Câu chuyện ${key || "hiện tại"}`;
  const shortTitle = title.length > 28 ? `${title.slice(0, 27).trimEnd()}…` : title;
  const subject = `mẩu chuyện “${title}” tại ${area.title}`;
  const content = folded(`${title} ${plainText(scene.description, 1200)}`);
  const topics = TOPICS.filter((topic) => topic.matches.test(content)).slice(0, 2);
  const details = topics.map((topic) => ({
    label: topic.label,
    value: `${topic.question} trong ${subject}?`,
  }));
  if (details.length < 2) details.push({
    label: "Chi tiết đáng chú ý", value: `Tôi nên chú ý những chi tiết nào trong ${subject}?`,
  });
  if (details.length < 2) details.push({
    label: "Ý nghĩa câu chuyện", value: `Ý nghĩa chính của ${subject} là gì?`,
  });
  return {
    contextLabel: `${key ? `${key} · ` : ""}${title}`,
    suggestions: [
      { label: `Về ${shortTitle}`, value: `Tóm tắt nội dung ${subject}.` },
      ...details,
      { label: "Giải thích thêm", value: `Giải thích thêm ${subject}, dựa trên các nguồn hiện có.` },
    ],
  };
}
