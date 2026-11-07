import { mentionsOtherTourArea, type TourArea } from "./tour-chat-scope";
import type { GuideStory } from "../types/heritage";

export interface SceneSuggestion {
  label: string;
  value: string;
  storyId?: string;
}

export interface Story {
  title: string;
  description?: string | null;
  guide_stories?: GuideStory[];
}

function plainText(value: unknown, limit: number): string {
  if (typeof value !== "string") return "";
  return value
    .replace(/<[^>]*>/g, " ")
    .replace(/https?:\/\/\S+/gi, "")
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

function questionsFor(subject: string): SceneSuggestion[] {
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
 */
export function buildSceneChatSuggestions(
  area: Pick<TourArea, "id" | "title"> | null,
  scene: Story | null,
  sceneKey: string,
  selectedPoint?: { popup_title: string | null; guide_stories?: GuideStory[] } | null,
  completedStoryIds: readonly string[] = [],
): { contextLabel: string | null; suggestions: SceneSuggestion[] } {
  if (!area) return { contextLabel: null, suggestions: [] };
  if (!scene || mentionsOtherTourArea(`${scene.title} ${scene.description ?? ""}`, area.id)) {
    return {
      contextLabel: null,
      suggestions: questionsFor(`di sản ${area.title}`),
    };
  }

  const key = plainText(sceneKey, 12);
  const title = plainText(scene.title, 64) || `Câu chuyện ${key || "hiện tại"}`;
  const pointTitle = plainText(selectedPoint?.popup_title, 80);
  const point = pointTitle && !mentionsOtherTourArea(pointTitle, area.id) ? selectedPoint : null;
  const stories = point ? point.guide_stories : scene.guide_stories;
  if (stories?.length) {
    return {
      contextLabel: `${key ? `${key} · ` : ""}${title}${point ? ` · ${pointTitle}` : ""}`,
      suggestions: stories.filter((story) => !completedStoryIds.includes(story.id)
        && story.source_ids.length > 0 && !mentionsOtherTourArea(story.question, area.id))
        .slice(0, 3).map((story) => ({ label: story.label, value: story.question, storyId: story.id })),
    };
  }
  if (point) {
    return {
      contextLabel: `${key ? `${key} · ` : ""}${title} · ${pointTitle}`,
      suggestions: questionsFor(`điểm “${pointTitle}” tại ${area.title}`).slice(0, 3),
    };
  }
  const subject = `mẩu chuyện “${title}” tại ${area.title}`;
  return {
    contextLabel: `${key ? `${key} · ` : ""}${title}`,
    suggestions: questionsFor(subject),
  };
}
