"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  BookOpenCheck,
  Check,
  Clock3,
  FilePlus2,
  Flame,
  FolderKanban,
  Inbox,
  Library,
  Loader2,
  Search,
  Settings,
  Zap
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { QueryProvider } from "@/components/query-provider";
import { Resource, Task, api } from "@/lib/api";
import { useAppStore } from "@/lib/store";

const navItems = [
  { id: "dashboard", label: "工作台", icon: Flame },
  { id: "inbox", label: "Inbox", icon: Inbox },
  { id: "resources", label: "资源", icon: Library },
  { id: "processing", label: "处理", icon: Zap },
  { id: "projects", label: "项目", icon: FolderKanban },
  { id: "review", label: "复习", icon: BookOpenCheck },
  { id: "search", label: "搜索", icon: Search },
  { id: "settings", label: "设置", icon: Settings }
];

const edgeColor: Record<string, string> = {
  inbox: "#D8D5CE",
  to_preview: "#C4622D",
  to_process: "#C4622D",
  processing: "#4A7C59",
  reviewing: "#4A7C59",
  archived: "#D8D5CE",
  cold_stored: "#A09D96",
  discarded: "#B0390E"
};

function Shell() {
  const { activeView, setActiveView } = useAppStore();
  const [toast, setToast] = useState("");

  useEffect(() => {
    const syncFromUrl = () => {
      const view = new URLSearchParams(window.location.search).get("view") || "dashboard";
      if (navItems.some((item) => item.id === view)) setActiveView(view);
    };
    syncFromUrl();
    window.addEventListener("popstate", syncFromUrl);
    return () => window.removeEventListener("popstate", syncFromUrl);
  }, [setActiveView]);

  const navigate = (view: string) => {
    const url = view === "dashboard" ? "/" : `/?view=${view}`;
    window.history.pushState({ view }, "", url);
    setActiveView(view);
  };

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2800);
  };

  return (
    <main className="flex min-h-screen min-w-0 flex-col bg-paper text-ink md:flex-row">
      <aside className="order-2 shrink-0 border-t border-line bg-white md:order-1 md:flex md:w-[74px] md:flex-col md:border-r md:border-t-0 md:py-4">
        <div className="hidden px-4 font-serif text-[22px] leading-none md:block">消化</div>
        <nav className="grid grid-cols-4 gap-1 p-2 md:mt-5 md:flex md:flex-1 md:flex-col">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeView === item.id;
            return (
              <button
                key={item.id}
                title={item.label}
                onClick={() => navigate(item.id)}
                className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-md px-2 text-[12px] transition md:h-11 md:flex-row md:text-[13px] ${
                  active ? "bg-ink text-white" : "text-muted hover:bg-panel hover:text-ink"
                }`}
              >
                <Icon size={18} />
                <span className="max-w-full truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="order-1 flex min-w-0 flex-1 flex-col md:order-2">
        <CaptureBar navigate={navigate} showToast={showToast} />
        <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto p-3 pb-28 sm:p-5 md:pb-5">
          {activeView === "dashboard" && <Dashboard navigate={navigate} />}
          {activeView === "inbox" && <InboxView showToast={showToast} />}
          {activeView === "resources" && <ResourcesView />}
          {activeView === "processing" && <ProcessingDesk showToast={showToast} />}
          {activeView === "projects" && <ProjectsView showToast={showToast} />}
          {activeView === "review" && <ReviewView showToast={showToast} />}
          {activeView === "search" && <SearchView />}
          {activeView === "settings" && <SettingsView />}
        </div>
      </section>

      {toast && (
        <div className="fixed bottom-24 left-3 right-3 z-50 rounded-md bg-ink px-4 py-3 text-[14px] text-white shadow-soft md:bottom-5 md:left-auto md:right-5 md:max-w-sm">
          {toast}
        </div>
      )}
    </main>
  );
}

function CaptureBar({ navigate, showToast }: { navigate: (view: string) => void; showToast: (message: string) => void }) {
  const [value, setValue] = useState("");
  const [type, setType] = useState("webpage");
  const [error, setError] = useState("");
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => {
      const trimmed = value.trim();
      return api.createResource({
        title: trimmed.startsWith("http") ? summarizeUrl(trimmed) : trimmed.slice(0, 80),
        type,
        original_url: trimmed.startsWith("http") ? trimmed : undefined,
        source_platform: trimmed.startsWith("http") ? "链接导入" : "手动粘贴",
        summary: trimmed.startsWith("http") ? "链接已采集，等待解析与快判。" : trimmed
      });
    },
    onSuccess: async () => {
      setValue("");
      setError("");
      await qc.invalidateQueries();
      showToast("已入库，已切换到 Inbox 等待快判");
      navigate("inbox");
    },
    onError: (err) => showToast(err instanceof Error ? err.message : "入库失败")
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!value.trim()) {
      setError("请输入内容");
      showToast("请输入内容后再入库");
      return;
    }
    mutation.mutate();
  }

  return (
    <form onSubmit={submit} className="grid gap-2 border-b border-line bg-white p-3 sm:grid-cols-[auto_1fr_auto_auto] sm:items-center sm:px-5">
      <div className="flex items-center gap-2 text-[14px] font-medium text-accent">
        <FilePlus2 size={18} />
        <span className="sm:hidden">快速入库</span>
      </div>
      <div className="min-w-0">
        <input
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError("");
          }}
          placeholder="粘贴链接、文章片段或资源标题"
          className={`h-11 w-full min-w-0 border-b bg-transparent text-[15px] outline-none focus:border-accent ${error ? "border-danger" : "border-line"}`}
        />
        {error && <div className="mt-1 text-[12px] text-danger">{error}</div>}
      </div>
      <select value={type} onChange={(e) => setType(e.target.value)} className="h-11 min-w-0 rounded-md border border-line bg-paper px-3 text-[14px]">
        <option value="webpage">网页</option>
        <option value="article">文章</option>
        <option value="pdf">PDF</option>
        <option value="video">视频</option>
        <option value="note">文本</option>
      </select>
      <button
        className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-accent px-4 text-[14px] font-medium text-white disabled:opacity-60"
        disabled={mutation.isPending}
      >
        {mutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
        入库
      </button>
    </form>
  );
}

function Dashboard({ navigate }: { navigate: (view: string) => void }) {
  const { energyMode, setEnergyMode, setSelectedTaskId } = useAppStore();
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["dashboard", energyMode],
    queryFn: () => api.dashboard(energyMode),
    placeholderData: keepPreviousData
  });

  const tasks = data?.tasks ?? [];

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-5">
      <header className="min-w-0">
        <h1 className="font-serif text-[26px] sm:text-[28px]">今日处理台</h1>
        <p className="mt-1 text-[14px] text-muted">{isLoading ? "正在加载任务状态" : data?.recommended}</p>
        {isFetching && !isLoading && <p className="mt-1 text-[12px] text-muted">正在后台更新数据...</p>}
      </header>

      <section className="grid min-w-0 gap-3 sm:grid-cols-3">
        {[
          ["focus", "专注深处理", "锁定 1-2 个长资源"],
          ["scan", "快速扫过", "清理 Inbox 与速看"],
          ["review", "只想复习", "主动复述，不摄入新资源"]
        ].map(([id, title, desc]) => (
          <button
            key={id}
            onClick={() => setEnergyMode(id)}
            className={`min-w-0 rounded-md border p-4 text-left transition ${energyMode === id ? "border-accent bg-white shadow-soft" : "border-line bg-panel hover:bg-white"}`}
          >
            <div className="truncate text-[16px] font-semibold">{title}</div>
            <div className="mt-1 text-[13px] text-muted">{desc}</div>
          </button>
        ))}
      </section>

      <section className="grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-5">
        {Object.entries(data?.stats ?? { pending_tasks: 0, inbox: 0, ai_drafts: 0, reviews: 0, cold: 0 }).map(([key, value]) => (
          <div key={key} className="min-w-0 rounded-md border border-line bg-white p-4">
            <div className="font-mono text-[24px]">{String(value)}</div>
            <div className="mt-1 truncate text-[13px] text-muted">{statName(key)}</div>
          </div>
        ))}
      </section>

      <section className="grid min-w-0 gap-4 lg:grid-cols-[1.2fr_.8fr]">
        <div className="min-w-0 rounded-md border border-line bg-white p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-[18px] font-semibold">优先处理</h2>
            <button
              onClick={() => {
                if (tasks[0]) setSelectedTaskId(tasks[0].id);
                navigate("processing");
              }}
              className="rounded-md border border-line px-3 py-2 text-[13px] hover:bg-panel"
            >
              开始处理
            </button>
          </div>
          <TaskList tasks={tasks} emptyText="暂无任务。先去 Inbox 留下一个资源，它会生成处理任务。" />
        </div>
        <div className="min-w-0 rounded-md border border-line bg-white p-4">
          <h2 className="text-[18px] font-semibold">快捷动作</h2>
          <div className="mt-3 grid gap-2">
            <button onClick={() => navigate("inbox")} className="rounded-md bg-ink px-4 py-3 text-left text-white">清理 Inbox</button>
            <button onClick={() => navigate("review")} className="rounded-md border border-line px-4 py-3 text-left hover:bg-panel">进入复习</button>
            <button onClick={() => navigate("search")} className="rounded-md border border-line px-4 py-3 text-left hover:bg-panel">查找知识片段</button>
          </div>
        </div>
      </section>
    </div>
  );
}

function InboxView({ showToast }: { showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const [step, setStep] = useState(1);
  const [purpose, setPurpose] = useState("active_learning");
  const [minutes, setMinutes] = useState(30);
  const { data: resource, isLoading } = useQuery({ queryKey: ["inbox-next"], queryFn: api.nextInbox, placeholderData: keepPreviousData });
  const decide = useMutation({
    mutationFn: (keep: boolean) => api.decideInbox(resource!.id, { keep, purpose, estimated_minutes: minutes }),
    onSuccess: async (_, keep) => {
      setStep(1);
      await qc.invalidateQueries();
      showToast(keep ? "已生成处理任务" : "资源已删除");
    }
  });
  const defer = useMutation({
    mutationFn: () => api.deferInbox(resource!.id),
    onSuccess: async () => {
      await qc.invalidateQueries();
      showToast("已延后 24 小时");
    }
  });

  if (isLoading && !resource) return <Loading />;
  if (!resource) return <Empty title="Inbox 已清空" action="继续从顶部采集栏添加新资源。" />;

  return (
    <div className="mx-auto grid w-full max-w-3xl gap-4">
      <h1 className="font-serif text-[26px] sm:text-[28px]">单卡快判</h1>
      <ResourceCard resource={resource} large />
      {step === 1 && (
        <div className="grid gap-3 sm:grid-cols-2">
          <button onClick={() => setStep(2)} className="rounded-md bg-success px-4 py-4 text-white">留下</button>
          <button onClick={() => decide.mutate(false)} className="rounded-md border border-danger px-4 py-4 text-danger">删除</button>
        </div>
      )}
      {step === 2 && (
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            ["active_learning", "主动学习"],
            ["reference", "备用参考"],
            ["unsure", "暂不确定"]
          ].map(([id, label]) => (
            <button key={id} onClick={() => { setPurpose(id); id === "unsure" ? defer.mutate() : setStep(3); }} className="rounded-md border border-line bg-white px-4 py-4 text-left hover:border-accent">
              {label}
            </button>
          ))}
        </div>
      )}
      {step === 3 && (
        <div className="grid gap-3 sm:grid-cols-3">
          {[10, 30, 60].map((m) => (
            <button key={m} onClick={() => { setMinutes(m); decide.mutate(true); }} className="rounded-md border border-line bg-white px-4 py-4 hover:border-accent">
              {m === 60 ? "1 小时+" : `${m} 分钟`}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ResourcesView() {
  const { data, isLoading } = useQuery({ queryKey: ["resources"], queryFn: () => api.resources(), placeholderData: keepPreviousData });
  if (isLoading && !data) return <Loading />;
  return (
    <div className="mx-auto grid w-full max-w-6xl gap-4">
      <h1 className="font-serif text-[26px] sm:text-[28px]">资源总库</h1>
      <div className="grid gap-3">
        {data?.map((resource) => <ResourceCard key={resource.id} resource={resource} />)}
      </div>
    </div>
  );
}

function ProcessingDesk({ showToast }: { showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const { selectedTaskId, setSelectedTaskId } = useAppStore();
  const { data: tasks } = useQuery({ queryKey: ["tasks"], queryFn: api.tasks, placeholderData: keepPreviousData });
  const task = useMemo(() => {
    const pending = (tasks ?? []).filter((item) => item.status === "pending");
    return pending.find((item) => item.id === selectedTaskId) ?? pending[0];
  }, [selectedTaskId, tasks]);

  const complete = useMutation({
    mutationFn: (id: string) => api.completeTask(id),
    onSuccess: async () => {
      await qc.invalidateQueries();
      showToast("任务完成，已进入复习沉淀");
    }
  });
  const summarize = useMutation({ mutationFn: (id: string) => api.summarize(id), onSuccess: () => showToast("AI 摘要草稿已生成") });
  const anki = useMutation({ mutationFn: (id: string) => api.generateAnki(id), onSuccess: () => showToast("Anki 草稿卡已生成") });

  if (!task) return <Empty title="没有待处理任务" action="先去 Inbox 留下一个资源，它会生成处理任务。" />;

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-4">
      <header className="min-w-0 rounded-md border border-line bg-ink p-4 text-white sm:p-5">
        <div className="text-[13px] text-white/70">锁定模式</div>
        <h1 className="mt-1 break-words font-serif text-[23px] sm:text-[28px]">{task.title}</h1>
        <div className="mt-2 flex flex-wrap gap-3 text-[13px] text-white/70">
          <span>类型：{task.task_type}</span>
          <span>预计：{task.estimated_minutes} 分钟</span>
          <span>优先级：{task.priority}</span>
        </div>
      </header>
      <section className="grid min-w-0 gap-4 lg:grid-cols-[1fr_380px]">
        <div className="min-h-[360px] min-w-0 rounded-md border border-line bg-white p-4 sm:p-5">
          <h2 className="text-[18px] font-semibold">内容区</h2>
          <textarea className="mt-4 h-[280px] w-full resize-none rounded-md border border-line bg-paper p-4 outline-none focus:border-accent sm:h-[330px]" placeholder="写一句话判断核心价值，再提取 3 个可复用知识点。" />
        </div>
        <div className="min-w-0 rounded-md border border-line bg-white p-4 sm:p-5">
          <h2 className="text-[18px] font-semibold">完成这一轮</h2>
          <div className="mt-4 grid gap-3">
            <label className="flex items-center gap-2"><input type="checkbox" /> 核心价值已写明</label>
            <label className="flex items-center gap-2"><input type="checkbox" /> 3 个知识点已提取</label>
            <label className="flex items-center gap-2"><input type="checkbox" /> 已选择输出形式</label>
            <button disabled={!task.resource_id || summarize.isPending} onClick={() => task.resource_id && summarize.mutate(task.resource_id)} className="rounded-md border border-line px-4 py-3 text-left hover:bg-panel disabled:opacity-50">
              生成 AI 摘要草稿
            </button>
            <button disabled={!task.resource_id || anki.isPending} onClick={() => task.resource_id && anki.mutate(task.resource_id)} className="rounded-md border border-line px-4 py-3 text-left hover:bg-panel disabled:opacity-50">
              生成 Anki 草稿
            </button>
            <button onClick={() => complete.mutate(task.id)} className="rounded-md bg-success px-4 py-3 text-white">
              标记完成
            </button>
          </div>
        </div>
      </section>
      <TaskList tasks={tasks ?? []} onPick={(item) => setSelectedTaskId(item.id)} emptyText="暂无任务。先去 Inbox 快判资源。" />
    </div>
  );
}

function ProjectsView({ showToast }: { showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const { data } = useQuery({ queryKey: ["projects"], queryFn: api.projects, placeholderData: keepPreviousData });
  const create = useMutation({
    mutationFn: () => api.createProject({ name: name.trim() }),
    onSuccess: async () => {
      setName("");
      await qc.invalidateQueries({ queryKey: ["projects"] });
      showToast("项目已创建");
    }
  });
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-4">
      <h1 className="font-serif text-[26px] sm:text-[28px]">项目空间</h1>
      <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) create.mutate(); }} className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="输入项目标题，10 秒创建" className="h-11 min-w-0 rounded-md border border-line bg-white px-3 outline-none focus:border-accent" />
        <button className="rounded-md bg-ink px-4 py-3 text-white sm:py-0">创建</button>
      </form>
      <div className="grid gap-3 sm:grid-cols-2">
        {data?.map((item) => (
          <div key={item.id} className="min-w-0 rounded-md border border-line bg-white p-4">
            <h2 className="break-words text-[18px] font-semibold">{item.name}</h2>
            <p className="mt-2 text-[14px] text-muted">{item.description || "等待资源、笔记、Anki 与证据库自然长出来。"}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReviewView({ showToast }: { showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const [answer, setAnswer] = useState("");
  const { data } = useQuery({ queryKey: ["reviews"], queryFn: api.reviews, placeholderData: keepPreviousData });
  const item = data?.[0];
  const complete = useMutation({
    mutationFn: (quality: string) => api.completeReview(item.id, quality),
    onSuccess: async () => {
      setAnswer("");
      await qc.invalidateQueries();
      showToast("复习已记录");
    }
  });
  if (!item) return <Empty title="今天没有复习项" action="处理台完成任务后会生成新的复习提醒。" />;
  return (
    <div className="mx-auto grid w-full max-w-3xl gap-4">
      <h1 className="font-serif text-[26px] sm:text-[28px]">主动复述</h1>
      <div className="min-w-0 rounded-md border border-line bg-white p-4 sm:p-5">
        <div className="font-mono text-[13px] text-muted">今日复习</div>
        <h2 className="mt-2 break-words text-[20px] font-semibold">{item.prompt}</h2>
        <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} className="mt-4 h-48 w-full resize-none rounded-md border border-line bg-paper p-4 outline-none focus:border-accent" placeholder="先自己回答，再决定熟悉程度。" />
        <div className="mt-4 flex flex-wrap gap-2">
          <button onClick={() => complete.mutate("known")} className="rounded-md bg-success px-4 py-2 text-white">知道</button>
          <button onClick={() => complete.mutate("fuzzy")} className="rounded-md border border-line px-4 py-2">模糊</button>
          <button onClick={() => complete.mutate("unknown")} className="rounded-md border border-danger px-4 py-2 text-danger">不会</button>
        </div>
      </div>
    </div>
  );
}

function SearchView() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const { data, isFetching } = useQuery({
    queryKey: ["search", submitted],
    queryFn: () => api.search(submitted),
    enabled: Boolean(submitted),
    placeholderData: keepPreviousData
  });
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-4">
      <h1 className="font-serif text-[26px] sm:text-[28px]">跨资源搜索</h1>
      <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) setSubmitted(q.trim()); }} className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索标题、摘要、字幕片段、PDF 段落" className="h-12 min-w-0 rounded-md border border-line bg-white px-4 outline-none focus:border-accent" />
        <button className="rounded-md bg-ink px-5 py-3 text-white sm:py-0">{isFetching ? "搜索中" : "搜索"}</button>
      </form>
      <div className="grid gap-3">
        {data?.map((item) => (
          <div key={`${item.kind}-${item.id}`} className="min-w-0 rounded-md border border-line bg-white p-4">
            <div className="break-all font-mono text-[13px] text-accent">{item.kind} · {item.location}</div>
            <h2 className="mt-1 break-words text-[17px] font-semibold">{item.title}</h2>
            <p className="mt-2 break-words text-[14px] text-muted">{item.snippet}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function SettingsView() {
  return (
    <div className="mx-auto grid w-full max-w-3xl gap-4">
      <h1 className="font-serif text-[26px] sm:text-[28px]">设置</h1>
      <div className="rounded-md border border-line bg-white p-5">
        <h2 className="text-[18px] font-semibold">本地 MVP 配置</h2>
        <div className="mt-4 grid gap-3 text-[14px] text-muted">
          <div>AI：通过后端 `.env` 的 `OPENAI_API_KEY` 和 `AI_MODEL` 替换。</div>
          <div>存储：MinIO 服务已在 Docker Compose 中预留；当前本地可用 SQLite 先跑通。</div>
          <div>搜索：当前 API 有关键词搜索，Meilisearch 已在基础设施中预留。</div>
          <div>迁移：正式结构使用 Alembic，开发启动会自动建表。</div>
        </div>
      </div>
    </div>
  );
}

function TaskList({ tasks, onPick, emptyText }: { tasks: Task[]; onPick?: (task: Task) => void; emptyText: string }) {
  if (!tasks.length) return <div className="rounded-md bg-panel p-4 text-[14px] text-muted">{emptyText}</div>;
  return (
    <div className="grid gap-2">
      {tasks.map((task) => (
        <button
          key={task.id}
          onClick={() => onPick?.(task)}
          className="status-edge min-w-0 rounded-md border border-line bg-white p-3 pl-4 text-left hover:border-accent"
          style={{ "--edge": task.status === "done" ? "#4A7C59" : "#C4622D" } as React.CSSProperties}
        >
          <div className="flex min-w-0 items-start justify-between gap-3">
            <span className="min-w-0 break-words font-medium">{task.title}</span>
            <span className="shrink-0 font-mono text-[12px] text-muted">{task.estimated_minutes}m</span>
          </div>
          <div className="mt-1 text-[13px] text-muted">{task.task_type} · P{task.priority} · {task.status}</div>
        </button>
      ))}
    </div>
  );
}

function ResourceCard({ resource, large = false }: { resource: Resource; large?: boolean }) {
  const color = edgeColor[resource.status] ?? "#D8D5CE";
  const sourceLabel = resource.original_url ? summarizeUrl(resource.original_url) : resource.source_platform || "本地";
  return (
    <article className={`status-edge min-w-0 rounded-md border border-line bg-white p-4 pl-5 shadow-sm ${large ? "min-h-[240px]" : ""}`} style={{ "--edge": color } as React.CSSProperties}>
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="break-words font-mono text-[12px] text-muted">{sourceLabel} · {resource.type} · {resource.status}</div>
          <h2 className={`${large ? "mt-3 text-[22px] sm:text-[24px]" : "mt-1 text-[18px]"} break-words font-semibold`}>{displayTitle(resource.title)}</h2>
        </div>
        <div className="shrink-0 rounded-md bg-panel px-3 py-2 font-mono text-[13px]">热度 {resource.heat_score.toFixed(1)}</div>
      </div>
      <p className="mt-3 break-words text-[14px] leading-6 text-muted">{resource.summary}</p>
      <div className="mt-4 flex min-w-0 flex-wrap gap-2 text-[13px] text-muted">
        <span className="inline-flex items-center gap-1"><Clock3 size={14} /> 预计 {resource.estimated_minutes} 分钟</span>
        {resource.original_url && <span className="max-w-full break-all text-[12px] text-cold">{resource.original_url}</span>}
      </div>
    </article>
  );
}

function Empty({ title, action }: { title: string; action: string }) {
  return (
    <div className="mx-auto mt-10 max-w-xl rounded-md border border-line bg-white p-6 text-center sm:mt-16 sm:p-8">
      <Archive className="mx-auto text-cold" />
      <h2 className="mt-4 text-[20px] font-semibold">{title}</h2>
      <p className="mt-2 text-[14px] text-muted">{action}</p>
    </div>
  );
}

function Loading() {
  return (
    <div className="flex h-64 items-center justify-center text-muted">
      <Loader2 className="mr-2 animate-spin" size={18} />
      正在加载
    </div>
  );
}

function summarizeUrl(value: string) {
  try {
    const url = new URL(value);
    const path = url.pathname === "/" ? "" : url.pathname.split("/").filter(Boolean).slice(0, 2).join("/");
    return `${url.hostname}${path ? `/${path}` : ""}`;
  } catch {
    return value;
  }
}

function displayTitle(value: string) {
  if (value.startsWith("http")) return summarizeUrl(value);
  return value;
}

function statName(key: string) {
  return (
    {
      pending_tasks: "今日待处理",
      inbox: "Inbox 待判",
      ai_drafts: "AI 待确认",
      reviews: "今日复习",
      cold: "冷存提醒"
    }[key] ?? key
  );
}

export default function Page() {
  return (
    <QueryProvider>
      <Shell />
    </QueryProvider>
  );
}
