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

export interface ConnectorTestResult {
  status: string;
  healthy: boolean;
  latency_ms: number;
  message: string;
}

export interface ConnectorLog {
  id: string;
  timestamp: string;
  level: string;
  message: string;
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
  text?: string | null;
}

export interface ChunkDetail {
  id: string;
  chunk_index: number;
  text: string;
  token_count: number;
  qdrant_id: string | null;
  created_at: string | null;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[];
  linked_doc_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "document" | "note" | "connector" | "tag";
  val: number;
  color: string;
  group: string;
  details: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  value: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_nodes: number;
    total_edges: number;
    documents: number;
    notes: number;
    connectors: number;
    tags: number;
  };
}

export interface AuditLog {
  id: string;
  user_id: string;
  query?: string;
  answer_preview?: string;
  query_text?: string;
  response_text?: string;
  created_at: string;
}

export type ThemeMode = "dark" | "light" | "system";

export interface Stats {
  total_documents: number;
  total_chunks?: number;
  total_queries: number;
  active_connectors: number;
  qdrant_status?: string;
  llm_provider?: string;
  system_status?: string;
}

export interface ApiResponse<T> {
  data: T;
  error: string | null;
}
