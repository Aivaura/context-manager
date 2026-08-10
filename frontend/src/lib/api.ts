import axios, { type AxiosInstance } from "axios";
import { useAuthStore } from "./store";
import type {
  ApiResponse,
  AuditLog,
  Connector,
  Document,
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
  login: async (email: string, password: string) => {
    const res = await api.post<{ access_token: string; token_type: string }>(
      "/auth/login",
      { email, password }
    );
    return res.data;
  },
  logout: async () => {
    await api.post("/auth/logout");
    useAuthStore.getState().clearAuth();
  },
  me: async (): Promise<User> => {
    const res = await api.get<ApiResponse<User>>("/auth/me");
    return res.data.data;
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
  status: async (type: string): Promise<Connector> => {
    const res = await api.get<ApiResponse<Connector>>(`/connectors/${type}/status`);
    return res.data.data;
  },
};

export const queryApi = {
  ask: async (question: string, top_k = 5): Promise<QueryResult> => {
    const res = await api.post<QueryResult>("/query", { question, top_k });
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
    if (connector) params.set("connector", connector);
    const res = await api.get<ApiResponse<Document[]>>(`/documents?${params}`);
    return res.data.data;
  },
  get: async (id: string): Promise<Document> => {
    const res = await api.get<ApiResponse<Document>>(`/documents/${id}`);
    return res.data.data;
  },
  delete: async (id: string) => {
    await api.delete(`/documents/${id}`);
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
