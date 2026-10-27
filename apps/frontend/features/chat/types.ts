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
}

export interface MessageCitation {
  id: string;
  message_id: string;
  source_title: string;
  source_url: string | null;
  relevance_score: number | null;
}

export interface ChatResponse {
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

export interface StoredMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  citations: MessageCitation[];
}
