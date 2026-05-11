/** API 客户端 — 带 JWT 认证支持 */

const BASE = "/api/v1";
const TOKEN_KEY = "ragkb_token";
const USER_KEY = "ragkb_user";

// ===== Token Management =====

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export function logout() {
  clearToken();
  window.location.reload();
}

// ===== HTTP Helpers =====

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeaders(),
    ...(options?.headers as Record<string, string> || {}),
  };
  const resp = await fetch(`${BASE}${url}`, { ...options, headers });
  if (resp.status === 401) {
    clearToken();
    throw new Error("Unauthorized");
  }
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return resp.json();
}

export interface UserInfo {
  id: string;
  username: string;
  email: string | null;
  display_name: string;
  role: string;
  department_id: string | null;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface KB {
  id: string;
  name: string;
  description: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
}

export interface Document {
  id: string;
  title: string;
  content_type: string;
  status: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface SearchResult {
  chunk_id: string;
  chunk_index: number;
  document_id: string;
  document_title: string;
  content: string;
  score: number;
  updated_at?: string;
  metadata?: Record<string, any>;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query_time_ms: number;
}

export interface QueryResponse {
  answer: string;
  sources: SearchResult[];
  tokens_used: number;
  query_time_ms: number;
}

export interface WikiPage {
  id: string;
  path: string;
  category: string;
  size: number;
  modified: string;
}

async function requestWithFile<T>(url: string, form: FormData): Promise<T> {
  const headers = { ...authHeaders() };
  const resp = await fetch(`${BASE}${url}`, {
    method: "POST",
    headers,
    body: form,
  });
  if (resp.status === 401) {
    clearToken();
    throw new Error("Unauthorized");
  }
  if (!resp.ok) throw new Error(`Upload failed: ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

export const api = {
  // ===== 认证 =====
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const resp = await request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setToken(resp.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
    return resp;
  },
  getMe: () => request<UserInfo>("/auth/me"),

  // ===== 知识库 =====
  listKBs: () => request<KB[]>("/knowledge-bases"),
  getKB: (id: string) => request<KB>(`/knowledge-bases/${id}`),
  createKB: (name: string, description: string) =>
    request<KB>("/knowledge-bases", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  deleteKB: (id: string) =>
    request<{ status: string }>(`/knowledge-bases/${id}`, { method: "DELETE" }),

  // ===== 文档 =====
  listDocuments: (kbId: string) =>
    request<Document[]>(`/knowledge-bases/${kbId}/documents`),
  uploadDocument: (kbId: string, file: File, title?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (title) form.append("title", title);
    return requestWithFile<Document>(`/knowledge-bases/${kbId}/documents`, form);
  },
  deleteDocument: (kbId: string, docId: string) =>
    request<{ status: string }>(`/knowledge-bases/${kbId}/documents/${docId}`, {
      method: "DELETE",
    }),

  // 搜索
  search: (kbId: string, query: string, topK = 5) =>
    request<SearchResponse>(`/knowledge-bases/${kbId}/search`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    }),

  // 问答（非流式）
  query: (kbId: string, query: string, topK = 5) =>
    request<QueryResponse>(`/knowledge-bases/${kbId}/query`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    }),

  // 问答（流式）
  queryStream: (
    kbId: string,
    query: string,
    callbacks: {
      onToken: (text: string) => void;
      onSources: (sources: SearchResult[]) => void;
      onDone: () => void;
      onError: (err: Error) => void;
    },
    topK = 5,
  ) => {
    const controller = new AbortController();
    fetch(`${BASE}/knowledge-bases/${kbId}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK }),
      signal: controller.signal,
    }).then(async (resp) => {
      if (!resp.ok) {
        callbacks.onError(new Error(`HTTP ${resp.status}`));
        return;
      }
      const reader = resp.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Parse SSE events from buffer
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (eventType === "token") {
              callbacks.onToken(data);
            } else if (eventType === "sources") {
              try {
                callbacks.onSources(JSON.parse(data));
              } catch {}
            } else if (eventType === "done") {
              callbacks.onDone();
            }
          }
        }
      }
      callbacks.onDone();
    }).catch((err) => {
      if (err.name !== "AbortError") callbacks.onError(err);
    });
    return controller; // 调用方可调用 controller.abort() 取消请求
  },

  // Wiki
  listWikiPages: (kbId: string) =>
    request<{ pages: WikiPage[]; total: number }>(`/knowledge-bases/${kbId}/wiki/pages`),
  getWikiPage: (kbId: string, pageId: string) =>
    request<{ id: string; content: string }>(`/knowledge-bases/${kbId}/wiki/pages/${pageId}`),
  triggerLint: (kbId: string) =>
    request<{ issues: any[] }>(`/knowledge-bases/${kbId}/wiki/lint`, { method: "POST" }),
};
