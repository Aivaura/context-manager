export interface User {
  id: string;
  email: string;
  role: string;
}

export interface Connector {
  type: string;
  status: "connected" | "disconnected" | "syncing" | "error";
  last_sync_at: string | null;
  document_count: number;
  error_message: string | null;
}

export interface Source {
  index: number;
  title: string;
  url: string | null;
  date: string | null;
  author: string | null;
  source_type: string;
  snippet: string;
}

export interface QueryResult {
  answer: string;
  sources: Source[];
  query_id: string;
}

export interface QueryHistoryItem {
  id: string;
  query: string;
  answer_preview: string;
  sources: string[];
  created_at: string;
}

export interface Document {
  id: string;
  title: string;
  source_url: string | null;
  author: string | null;
  chunk_count: number;
  indexed_at: string | null;
  source_id: string;
}

export interface AuditLog {
  id: string;
  user_id: string;
  query: string;
  answer_preview: string;
  created_at: string;
}

export interface Stats {
  total_documents: number;
  total_queries: number;
  active_connectors: number;
}

export interface ApiResponse<T> {
  data: T;
  error: string | null;
}
