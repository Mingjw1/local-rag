/** API 客户端 */

const BASE = "/api/v1";

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
  document_id: string;
  document_title: string;
  content: string;
  score: number;
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

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return resp.json();
}

export const api = {
  // 知识库
  listKBs: () => request<KB[]>("/knowledge-bases"),
  getKB: (id: string) => request<KB>(`/knowledge-bases/${id}`),
  createKB: (name: string, description: string) =>
    request<KB>("/knowledge-bases", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  deleteKB: (id: string) =>
    request<{ status: string }>(`/knowledge-bases/${id}`, { method: "DELETE" }),

  // 文档
  listDocuments: (kbId: string) =>
    request<Document[]>(`/knowledge-bases/${kbId}/documents`),
  uploadDocument: async (kbId: string, file: File, title?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (title) form.append("title", title);
    const resp = await fetch(`${BASE}/knowledge-bases/${kbId}/documents`, {
      method: "POST",
      body: form,
    });
    if (!resp.ok) throw new Error(`Upload failed: ${await resp.text()}`);
    return resp.json() as Promise<Document>;
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
