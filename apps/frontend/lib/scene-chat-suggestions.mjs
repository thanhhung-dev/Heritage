import { mentionsOtherTourArea } from "./tour-chat-scope.mjs";

/** @typedef {{ label: string, value: string }} SceneSuggestion */
/** @typedef {{ id: string, title: string }} TourArea */
/** @typedef {{ title: string, description?: string | null }} Story */

function plainText(value, limit) {
  if (typeof value !== "string") return "";
  return value.replace(/<[^>]*>/g, " ").replace(/https?:\/\/\S+/gi, "")
    .replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, limit);
}

/** @param {string} subject @returns {SceneSuggestion[]} */
function questionsFor(subject) {
  // Keep the four compact labels from the reference UI. The full question,
  // rather than its display label, carries the active story/heritage context.
  return [
    { label: "Giới thiệu tổng quan", value: `Giới thiệu tổng quan về ${subject}.` },
    { label: "Lịch sử hình thành", value: `Lịch sử và bối cảnh của ${subject} có gì đáng chú ý?` },
    { label: "Kiến trúc đặc sắc", value: `Những chi tiết kiến trúc nào nổi bật trong ${subject}?` },
    { label: "Khám phá cảnh này", value: `Tôi đang nhìn thấy gì trong cảnh của ${subject}?` },
  ];
}

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
  if (!scene || mentionsOtherTourArea(`${scene.title} ${scene.description ?? ""}`, area.id)) return {
    contextLabel: null,
    suggestions: questionsFor(`di sản ${area.title}`),
  };

  const key = plainText(sceneKey, 12);
  const title = plainText(scene.title, 64) || `Câu chuyện ${key || "hiện tại"}`;
  const subject = `mẩu chuyện “${title}” tại ${area.title}`;
  return {
    contextLabel: `${key ? `${key} · ` : ""}${title}`,
    suggestions: questionsFor(subject),
  };
}
