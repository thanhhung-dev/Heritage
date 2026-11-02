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
}
