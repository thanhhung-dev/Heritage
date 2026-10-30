export interface ChatOverlayCitation {
  id: string;
  message_id: string;
  source_title: string;
  source_url: string | null;
  relevance_score: number | null;
}

export interface ChatOverlaySuggestion {
  label: string;
  value: string;
}

export interface ChatOverlayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations: ChatOverlayCitation[];
  needsUserChoice?: boolean;
  abstained?: boolean;
  answerType?: string | null;
  suggestions?: ChatOverlaySuggestion[];
}

export interface ChatOverlayWidgetState {
  mode: "closed" | "open" | "expanded";
  input: string;
  messages: ChatOverlayMessage[];
  sending: boolean;
  error: string | null;
}
