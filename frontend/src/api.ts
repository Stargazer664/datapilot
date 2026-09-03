import type { DatabaseConfig, ProviderConfig, ProviderName, QueryResult } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(error.detail ?? "请求失败");
  }
  return response.json() as Promise<T>;
}

export const api = {
  getSettings: () => request<{ database: DatabaseConfig | null; providers: ProviderConfig[]; default_provider: ProviderName }>("/api/settings"),
  saveDatabase: (config: DatabaseConfig) => request<DatabaseConfig>("/api/settings/database", { method: "PUT", body: JSON.stringify(config) }),
  testDatabase: (config: DatabaseConfig) => request<{ status: string }>("/api/settings/database/test", { method: "POST", body: JSON.stringify(config) }),
  saveProvider: (provider: ProviderName, config: { api_key?: string; base_url: string; model: string; timeout_seconds: number }) =>
    request<ProviderConfig>(`/api/settings/providers/${provider}`, { method: "PUT", body: JSON.stringify(config) }),
  testProvider: (provider: ProviderName, config: { api_key?: string; base_url: string; model: string; timeout_seconds: number }) =>
    request<{ status: string }>(`/api/settings/providers/${provider}/test`, { method: "POST", body: JSON.stringify(config) }),
  createSession: () => request<{ id: string }>("/api/sessions", { method: "POST", body: JSON.stringify({ title: "数据分析" }) }),
  createQuery: (payload: { session_id: string; question: string; provider: ProviderName; model?: string }) =>
    request<{ query_id: string }>("/api/queries", { method: "POST", body: JSON.stringify(payload) }),
  getQuery: (id: string) => request<QueryResult>(`/api/queries/${id}`),
  cancelQuery: (id: string) => request<{ status: string }>(`/api/queries/${id}/cancel`, { method: "POST" }),
};
