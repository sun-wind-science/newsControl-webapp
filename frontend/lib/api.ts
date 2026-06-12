export type ApiResponse<T> = {
  success: boolean;
  data: T;
  message: string;
};

export type Resource = {
  id: string;
  project_id?: string;
  project_name?: string;
  title: string;
  type: string;
  status: string;
  decay_status: string;
  source_platform?: string;
  original_url?: string;
  file_url?: string;
  source_description?: string;
  summary?: string;
  tags: string[];
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

export type Note = {
  id: string;
  title: string;
  content: string;
  note_type: string;
  source_range?: string;
  created_at: string;
};

export type ResourceChunk = {
  id: string;
  resource_id: string;
  chunk_index: number;
  chunk_type: string;
  content: string;
  page_number?: number;
  start_time?: number;
  end_time?: number;
  heading?: string;
};

export type StoredFile = {
  id: string;
  resource_id?: string;
  file_name: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  download_url: string;
};

export type ResourceDetail = {
  resource: Resource;
  notes: Note[];
  chunks: ResourceChunk[];
  files: StoredFile[];
  tasks: Task[];
  ai_outputs: Array<{ id: string; output_type: string; content: string; verification_status: string; created_at: string }>;
  anki_cards: Array<{ id: string; front: string; back: string; tags?: string; exported: boolean; created_at: string }>;
};

export type Project = {
  id: string;
  name: string;
  description?: string;
  status: string;
  resource_count: number;
  note_count: number;
  task_count: number;
};

export type ProjectDetail = {
  project: Project;
  resources: Resource[];
  notes: Note[];
  tasks: Task[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...(init?.headers ?? {}) };
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });
  const text = await res.text();
  let json: ApiResponse<T> | undefined;
  try {
    json = text ? (JSON.parse(text) as ApiResponse<T>) : undefined;
  } catch {
    json = undefined;
  }
  if (!res.ok) {
    throw new Error(json?.message || `请求失败：${res.status}`);
  }
  if (!json?.success) {
    throw new Error(json?.message || "请求失败");
  }
  return json.data;
}

export const api = {
  dashboard: (mode: string) => request<any>(`/session/dashboard?energy_mode=${mode}`),
  capture: (payload: {
    content: string;
    capture_type: string;
    title?: string;
    summary?: string;
    source_platform?: string;
    process_goal?: string;
    estimated_minutes?: number;
    priority?: number;
    tags?: string;
    project_id?: string;
    next_action?: string;
  }) => request<ResourceDetail>("/capture", { method: "POST", body: JSON.stringify(payload) }),
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ResourceDetail>("/uploads/file", { method: "POST", body: form });
  },
  resources: (status?: string, resourceType?: string, projectId?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (resourceType && resourceType !== "all") params.set("resource_type", resourceType);
    if (projectId) params.set("project_id", projectId);
    const query = params.toString();
    return request<Resource[]>(`/resources${query ? `?${query}` : ""}`);
  },
  resourceDetail: (id: string) => request<ResourceDetail>(`/resources/${id}`),
  updateResource: (id: string, payload: Partial<Omit<Pick<Resource, "title" | "summary" | "status" | "type" | "source_platform" | "original_url" | "estimated_minutes" | "heat_score" | "project_id">, "project_id">> & { tags?: string; priority?: number; project_id?: string | null }) =>
    request<Resource>(`/resources/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  archiveResource: (id: string) => request<Resource>(`/resources/${id}/archive`, { method: "POST", body: "{}" }),
  discardResource: (id: string) => request<{ id: string }>(`/resources/${id}/discard`, { method: "POST", body: "{}" }),
  createAnnotation: (id: string, payload: { note_type: string; content: string; source_range?: string; title?: string }) =>
    request<Note>(`/resources/${id}/annotations`, { method: "POST", body: JSON.stringify(payload) }),
  completeResourceProcess: (id: string) => request<Resource>(`/resources/${id}/process/complete`, { method: "POST", body: "{}" }),
  nextInbox: () => request<ResourceDetail | null>("/inbox/next"),
  decideInbox: (id: string, payload: { keep: boolean; purpose: string; estimated_minutes: number }) =>
    request<{ task_id?: string }>(`/inbox/${id}/decide`, { method: "POST", body: JSON.stringify(payload) }),
  deferInbox: (id: string) => request<Resource>(`/inbox/${id}/defer`, { method: "POST", body: "{}" }),
  tasks: () => request<Task[]>("/tasks"),
  completeTask: (id: string) => request<{ id: string }>(`/tasks/${id}/complete`, { method: "POST", body: "{}" }),
  summarize: (id: string) => request<any>(`/resources/${id}/summarize`, { method: "POST", body: "{}" }),
  generateAnki: (id: string) => request<any>(`/resources/${id}/generate-anki`, { method: "POST", body: "{}" }),
  projects: () => request<Project[]>("/projects"),
  projectDetail: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  createProject: (payload: { name: string; description?: string }) => request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  updateProject: (id: string, payload: Partial<Pick<Project, "name" | "description" | "status">>) =>
    request<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  reviews: () => request<any[]>("/reviews/today"),
  completeReview: (id: string, quality: string) => request<any>(`/reviews/${id}/complete?quality=${quality}`, { method: "POST", body: "{}" }),
  search: (q: string) => request<any[]>(`/search?q=${encodeURIComponent(q)}`)
};
