export type ApiResponse<T> = {
  success: boolean;
  data: T;
  message: string;
};

export type Resource = {
  id: string;
  title: string;
  type: string;
  status: string;
  decay_status: string;
  source_platform?: string;
  original_url?: string;
  summary?: string;
  heat_score: number;
  estimated_minutes: number;
  created_at: string;
  last_touched_at: string;
};

export type Task = {
  id: string;
  title: string;
  task_type: string;
  priority: number;
  status: string;
  estimated_minutes: number;
  resource_id?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  if (!res.ok) {
    throw new Error(`请求失败：${res.status}`);
  }
  const json = (await res.json()) as ApiResponse<T>;
  if (!json.success) {
    throw new Error(json.message);
  }
  return json.data;
}

export const api = {
  dashboard: (mode: string) => request<any>(`/session/dashboard?energy_mode=${mode}`),
  resources: (status?: string) => request<Resource[]>(`/resources${status ? `?status=${status}` : ""}`),
  createResource: (payload: { title: string; type: string; original_url?: string; source_platform?: string; summary?: string }) =>
    request<Resource>("/resources", { method: "POST", body: JSON.stringify(payload) }),
  nextInbox: () => request<Resource | null>("/inbox/next"),
  decideInbox: (id: string, payload: { keep: boolean; purpose: string; estimated_minutes: number }) =>
    request<{ task_id?: string }>(`/inbox/${id}/decide`, { method: "POST", body: JSON.stringify(payload) }),
  deferInbox: (id: string) => request<Resource>(`/inbox/${id}/defer`, { method: "POST", body: "{}" }),
  tasks: () => request<Task[]>("/tasks"),
  completeTask: (id: string) => request<{ id: string }>(`/tasks/${id}/complete`, { method: "POST", body: "{}" }),
  summarize: (id: string) => request<any>(`/resources/${id}/summarize`, { method: "POST", body: "{}" }),
  generateAnki: (id: string) => request<any>(`/resources/${id}/generate-anki`, { method: "POST", body: "{}" }),
  projects: () => request<any[]>("/projects"),
  createProject: (payload: { name: string; description?: string }) => request<any>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  reviews: () => request<any[]>("/reviews/today"),
  completeReview: (id: string, quality: string) => request<any>(`/reviews/${id}/complete?quality=${quality}`, { method: "POST", body: "{}" }),
  search: (q: string) => request<any[]>(`/search?q=${encodeURIComponent(q)}`)
};
