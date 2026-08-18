import axios, { type AxiosInstance } from "axios";
import { useAuthStore } from "./store";
import type {
  ApiResponse,
  AuditLog,
  ChunkDetail,
  Connector,
  ConnectorLog,
  ConnectorTestResult,
  Document,
  GraphData,
  Note,
  QueryHistoryItem,
  QueryResult,
  Stats,
  User,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function createClient(): AxiosInstance {
  const client = axios.create({
    baseURL: `${BASE_URL}/api/v1`,
    withCredentials: true,
  });

  client.interceptors.request.use((config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (res) => res,
    async (error) => {
      if (error.response?.status === 401 && !error.config._retry) {
        error.config._retry = true;
        try {
          const res = await axios.post(
            `${BASE_URL}/api/v1/auth/refresh`,
            {},
            { withCredentials: true }
          );
          const { access_token } = res.data;
          const { user } = useAuthStore.getState();
          if (user) {
            useAuthStore.getState().setAuth(user, access_token);
          }
          error.config.headers.Authorization = `Bearer ${access_token}`;
          return client(error.config);
        } catch {
          useAuthStore.getState().clearAuth();
          window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

export const api = createClient();

export const authApi = {
  login: async (email: string, password: string): Promise<{ access_token: string; token_type: string; user?: User }> => {
    const res = await api.post<any>("/auth/login", { email, password });
    return res.data?.data || res.data;
  },
  logout: async () => {
    await api.post("/auth/logout");
    useAuthStore.getState().clearAuth();
  },
  me: async (tokenOverride?: string): Promise<User> => {
    const headers: Record<string, string> = {};
    if (tokenOverride) {
      headers.Authorization = `Bearer ${tokenOverride}`;
    }
    const res = await api.get<any>("/auth/me", { headers });
    return res.data?.data || res.data;
  },
};

export const connectorsApi = {
  list: async (): Promise<Connector[]> => {
    const res = await api.get<ApiResponse<Connector[]>>("/connectors");
    return res.data.data;
  },
  getAuthUrl: async (type: string) => {
    const res = await api.get<ApiResponse<{ url: string; message?: string; webhook_url?: string; verify_token?: string }>>(
      `/connectors/${type}/auth-url`
    );
    return res.data.data;
  },
  disconnect: async (type: string) => {
    await api.delete(`/connectors/${type}`);
  },
  sync: async (type: string) => {
    await api.post(`/connectors/${type}/sync`);
  },
  cancelSync: async (type: string) => {
    await api.post(`/connectors/${type}/cancel-sync`);
  },
  status: async (type: string): Promise<Connector> => {
    const res = await api.get<ApiResponse<Connector>>(`/connectors/${type}/status`);
    return res.data.data;
  },
  test: async (type: string): Promise<ConnectorTestResult> => {
    const res = await api.post<ApiResponse<ConnectorTestResult>>(`/connectors/${type}/test`);
    return res.data.data;
  },
  logs: async (type: string): Promise<ConnectorLog[]> => {
    const res = await api.get<ApiResponse<ConnectorLog[]>>(`/connectors/${type}/logs`);
    return res.data.data;
  },
};

export const queryApi = {
  ask: async (question: string, top_k = 5, source_type?: string): Promise<QueryResult> => {
    const payload: { question: string; top_k: number; source_type?: string } = { question, top_k };
    if (source_type && source_type !== "all") {
      payload.source_type = source_type;
    }
    const res = await api.post<QueryResult>("/query", payload);
    return res.data;
  },
  history: async (limit = 20): Promise<QueryHistoryItem[]> => {
    const res = await api.get<ApiResponse<QueryHistoryItem[]>>(`/query/history?limit=${limit}`);
    return res.data.data;
  },
};

export const documentsApi = {
  list: async (connector?: string, limit = 50, offset = 0): Promise<Document[]> => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (connector && connector !== "all") params.set("connector", connector);
    const res = await api.get<ApiResponse<Document[]>>(`/documents?${params}`);
    return res.data.data;
  },
  get: async (id: string): Promise<Document> => {
    const res = await api.get<ApiResponse<Document>>(`/documents/${id}`);
    return res.data.data;
  },
  update: async (id: string, data: { title?: string; author?: string; source_url?: string }) => {
    await api.put(`/documents/${id}`, data);
  },
  delete: async (id: string) => {
    await api.delete(`/documents/${id}`);
  },
  reindex: async (id: string) => {
    await api.post(`/documents/${id}/reindex`);
  },
  listChunks: async (docId: string): Promise<ChunkDetail[]> => {
    const res = await api.get<ApiResponse<ChunkDetail[]>>(`/documents/${docId}/chunks`);
    return res.data.data;
  },
  updateChunk: async (docId: string, chunkId: string, text: string) => {
    await api.put(`/documents/${docId}/chunks/${chunkId}`, { text });
  },
  deleteChunk: async (docId: string, chunkId: string) => {
    await api.delete(`/documents/${docId}/chunks/${chunkId}`);
  },
  uploadExcel: async (file: File): Promise<string> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post<ApiResponse<string>>("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data.data;
  },
};

export const notesApi = {
  list: async (): Promise<Note[]> => {
    const res = await api.get<ApiResponse<Note[]>>("/notes");
    return res.data.data;
  },
  get: async (id: string): Promise<Note> => {
    const res = await api.get<ApiResponse<Note>>(`/notes/${id}`);
    return res.data.data;
  },
  create: async (title: string, content: string, tags: string[] = []): Promise<Note> => {
    const res = await api.post<ApiResponse<Note>>("/notes", { title, content, tags });
    return res.data.data;
  },
  update: async (id: string, title?: string, content?: string, tags?: string[]): Promise<Note> => {
    const res = await api.put<ApiResponse<Note>>(`/notes/${id}`, { title, content, tags });
    return res.data.data;
  },
  delete: async (id: string) => {
    await api.delete(`/notes/${id}`);
  },
};

export const graphApi = {
  get: async (): Promise<GraphData> => {
    const res = await api.get<ApiResponse<GraphData>>("/graph");
    return res.data.data;
  },
};

export const adminApi = {
  auditLogs: async (limit = 50): Promise<AuditLog[]> => {
    const res = await api.get<ApiResponse<AuditLog[]>>(`/admin/audit-logs?limit=${limit}`);
    return res.data.data;
  },
  stats: async (): Promise<Stats> => {
    const res = await api.get<ApiResponse<Stats>>("/admin/stats");
    return res.data.data;
  },
  reindex: async () => {
    await api.post("/admin/reindex");
  },
};
