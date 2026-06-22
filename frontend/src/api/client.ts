const BASE = "/api";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail || body?.error || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

import type { ChatRequest, ChatResponse, HistoryListResponse } from "@/types";

export const api = {
  chat: (req: ChatRequest) =>
    http<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(req) }),

  history: (limit = 50) => http<HistoryListResponse>(`/history?limit=${limit}`),

  threadHistory: (threadId: string) =>
    http<HistoryListResponse>(`/history/${threadId}`),
};
