export interface AskRequest {
  question: string;
  session_id?: string;
  rag_enabled: boolean;
  tools_enabled: boolean;
}

export interface Citation {
  source: string;
  page?: string;
  [key: string]: unknown;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  source_type: 'rag' | 'web' | 'direct' | 'fallback';
  used_fallback: boolean;
  session_id?: string;
  error?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  rag_ready: boolean;
  web_search_ready: boolean;
}

export interface IngestResponse {
  files_processed: number;
  chunks_created: number;
}

export interface SessionResponse {
  id: string;
  title: string;
  created_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  source_type?: string;
  timestamp: Date;
  isStreaming?: boolean;
}
