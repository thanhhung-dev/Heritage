export type TourMode = "scene" | "standard" | "free" | "walk";
export type NarrationStatus = "unavailable" | "not_started" | "partial" | "completed" | "skipped";

export interface TourChatContext {
  scene_id: number;
  mode: TourMode;
  highlight_id?: number | null;
  story_id?: string | null;
  completed_story_ids?: string[];
  narration: NarrationStatus;
}

export interface TourReplyContext {
  scene_id: number;
  scene_key: string;
  scene_title: string;
  mode: TourMode;
  highlight_id?: number | null;
  highlight_title?: string | null;
  story_id?: string | null;
}

export interface Source {
  text?: string;
  doc?: string;
  url?: string;
  heading?: string;
  chunk_id?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt?: string;
  sources?: Source[];
  correctedFrom?: string;
  correctedTo?: string;
  answerType?: string;
  needsUserChoice?: boolean;
  abstained?: boolean;
  replyContext?: TourReplyContext;
}
