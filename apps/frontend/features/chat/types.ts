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
  sources?: Source[];
  correctedFrom?: string;
  correctedTo?: string;
}

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export interface ChatMessageRequest {
  message: string;
  conversation_id?: string | null;
  heritage_context?: string | Record<string, JsonValue> | null;
  scene_context?: string | Record<string, JsonValue> | null;
  heritage_id?: number | null;
  conversation_context?: { role: "user" | "assistant"; content: string }[];
}

export interface ChatSuggestion {
  original?: string;
  suggested?: string;
  label?: string;
  title?: string;
  name?: string;
  score?: number;
}

export interface ChatOutcome {
  corrected_from?: string;
  corrected_to?: string;
  needs_user_choice?: boolean;
  suggestions?: ChatSuggestion[];
  entity_id?: string | null;
  intent?: string | null;
  resolution_status?: string | null;
  answer_type?: string | null;
  abstained?: boolean;
  abstention_reason?: "insufficient_evidence" | "service_unavailable" | null;
}

export interface MessageCitation {
  id: string;
  message_id: string;
  source_title: string;
  source_url: string | null;
  relevance_score: number | null;
}

export interface ChatResponse extends ChatOutcome {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: MessageCitation[];
}

export interface Conversation {
  id: string;
  account_id: number | null;
  title: string;
  heritage_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface StoredMessage extends ChatOutcome {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  citations: MessageCitation[];
}

export interface ConversationDetail extends Conversation {
  messages: StoredMessage[];
}
