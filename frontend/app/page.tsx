"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  BookOpenCheck,
  Check,
  Clock3,
  FileText,
  Flame,
  FolderKanban,
  Inbox,
  Library,
  Loader2,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Settings,
  Upload,
  Zap
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { QueryProvider } from "@/components/query-provider";
import { Resource, ResourceDetail, Task, api } from "@/lib/api";
import { useAppStore } from "@/lib/store";

const navItems = [
  { id: "dashboard", label: "工作台", icon: Flame },
  { id: "inbox", label: "Inbox", icon: Inbox },
  { id: "resources", label: "资源库", icon: Library },
  { id: "processing", label: "处理台", icon: Zap },
  { id: "projects", label: "项目", icon: FolderKanban },
  { id: "review", label: "复习", icon: BookOpenCheck },
  { id: "search", label: "搜索", icon: Search },
  { id: "settings", label: "设置", icon: Settings }
];

const statusColor: Record<string, string> = {
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
  const { activeView, setActiveView, selectedResourceId, setSelectedResourceId } = useAppStore();
  const [toast, setToast] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const syncFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const view = params.get("view") || "dashboard";
      const id = params.get("id") || undefined;
      if (navItems.some((item) => item.id === view) || view === "resource") setActiveView(view);
      setSelectedResourceId(id);
    };
    syncFromUrl();
    window.addEventListener("popstate", syncFromUrl);
    return () => window.removeEventListener("popstate", syncFromUrl);
  }, [setActiveView, setSelectedResourceId]);

  const navigate = (view: string, id?: string) => {
    const params = new URLSearchParams();
    if (view !== "dashboard") params.set("view", view);
    if (id) params.set("id", id);
    const url = params.toString() ? `/?${params.toString()}` : "/";
    window.history.pushState({ view, id }, "", url);
    setActiveView(view);
    setSelectedResourceId(id);
  };

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  };

  return (
    <main className="flex min-h-screen min-w-0 flex-col bg-paper text-ink md:flex-row">
      <aside
        className={`fixed inset-x-0 bottom-0 z-40 shrink-0 border-t border-line bg-white transition-all md:static md:order-1 md:flex md:flex-col md:border-r md:border-t-0 md:py-4 ${
          sidebarOpen ? "md:w-[220px]" : "md:w-[74px] md:hover:w-[220px]"
        }`}
      >
        <div className="hidden items-center justify-between px-4 md:flex">
          <div className="truncate font-serif text-[22px]">消化</div>
          <button className="rounded-md p-1 text-muted hover:bg-panel" onClick={() => setSidebarOpen(!sidebarOpen)} title="展开导航">
            {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
        </div>
        <nav className="grid grid-cols-4 gap-1 p-2 md:mt-5 md:flex md:flex-1 md:flex-col">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => navigate(item.id)}
                title={item.label}
                className={`group flex min-h-12 flex-col items-center justify-center gap-1 rounded-md px-2 text-[12px] transition md:h-11 md:flex-row md:justify-start md:text-[13px] ${
                  active ? "bg-ink text-white" : "text-muted hover:bg-panel hover:text-ink"
                }`}
              >
                <Icon size={18} className="shrink-0" />
                <span className={`max-w-full truncate md:${sidebarOpen ? "inline" : "hidden"} md:group-hover:inline`}>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="order-1 flex min-w-0 flex-1 flex-col md:order-2">
        <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto p-3 pb-28 sm:p-5 md:pb-5">
          {activeView === "dashboard" && <Dashboard navigate={navigate} showToast={showToast} />}
          {activeView === "inbox" && <InboxView navigate={navigate} showToast={showToast} />}
          {activeView === "resources" && <ResourceLibrary navigate={navigate} />}
          {activeView === "resource" && selectedResourceId && <ResourceDetailView resourceId={selectedResourceId} showToast={showToast} />}
          {activeView === "processing" && <ProcessingDesk navigate={navigate} showToast={showToast} />}
          {activeView === "projects" && <ProjectsView showToast={showToast} />}
          {activeView === "review" && <ReviewView showToast={showToast} />}
          {activeView === "search" && <SearchView navigate={navigate} />}
          {activeView === "settings" && <SettingsView />}
        </div>
      </section>

      {toast && <div className="fixed bottom-24 left-3 right-3 z-50 rounded-md bg-ink px-4 py-3 text-[14px] text-white shadow-soft md:bottom-5 md:left-auto md:right-5 md:max-w-sm">{toast}</div>}
    </main>
  );
}

function Dashboard({ navigate, showToast }: { navigate: (view: string, id?: string) => void; showToast: (message: string) => void }) {
  const { energyMode, setEnergyMode, setSelectedTaskId } = useAppStore();
  const { data, isLoading } = useQuery({ queryKey: ["dashboard", energyMode], queryFn: () => api.dashboard(energyMode), placeholderData: keepPreviousData });
  const tasks = data?.tasks ?? [];

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-5">
      <header className="grid gap-2">
        <h1 className="font-serif text-[28px]">今日工作台</h1>
        <p className="text-[14px] text-muted">把看到但暂时处理不了的信息，送进一个必须流转的系统。</p>
      </header>

      <CapturePanel navigate={navigate} showToast={showToast} />

      <section className="grid gap-3 sm:grid-cols-3">
        {[
          ["focus", "专注深处理", "锁定 1-2 个长资源"],
          ["scan", "快速扫过", "清理 Inbox 与速看"],
          ["review", "只想复习", "主动复述，不摄入新资源"]
        ].map(([id, title, desc]) => (
          <button key={id} onClick={() => setEnergyMode(id)} className={`rounded-md border p-4 text-left ${energyMode === id ? "border-accent bg-white shadow-soft" : "border-line bg-panel hover:bg-white"}`}>
            <div className="font-semibold">{title}</div>
            <div className="mt-1 text-[13px] text-muted">{desc}</div>
          </button>
        ))}
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {Object.entries(data?.stats ?? { pending_tasks: 0, inbox: 0, captured_today: 0, processed_today: 0, stale: 0, reviews: 0, annotated: 0 }).map(([key, value]) => (
          <div key={key} className="rounded-md border border-line bg-white p-4">
            <div className="font-mono text-[24px]">{String(value)}</div>
            <div className="mt-1 text-[13px] text-muted">{statName(key)}</div>
          </div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_.9fr]">
        <div className="rounded-md border border-line bg-white p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-[18px] font-semibold">优先处理</h2>
              <p className="text-[13px] text-muted">{isLoading ? "正在同步任务" : data?.recommended}</p>
            </div>
            <button
              onClick={() => {
                if (tasks[0]) setSelectedTaskId(tasks[0].id);
                navigate("processing");
              }}
              className="rounded-md bg-ink px-3 py-2 text-[13px] text-white"
            >
              开始处理
            </button>
          </div>
          <TaskList tasks={tasks} emptyText="暂无任务。先采集资源，完成确认后会生成处理任务。" />
        </div>
        <div className="rounded-md border border-line bg-white p-4">
          <h2 className="text-[18px] font-semibold">为什么不用便签/Obsidian？</h2>
          <div className="mt-3 grid gap-3 text-[14px] text-muted">
            <p>便签负责临时记一下，Obsidian 负责长期知识库；这里负责强制流转：每条信息都要说明保存原因、设定处理计划、产生批注或输出。</p>
            <p>你不是在收藏东西，而是在减少未来的“不知道这是什么”。</p>
          </div>
        </div>
      </section>
    </div>
  );
}

function CapturePanel({ navigate, showToast }: { navigate: (view: string, id?: string) => void; showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"link" | "text" | "file">("link");
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [goal, setGoal] = useState("学习");
  const [minutes, setMinutes] = useState(20);
  const [priority, setPriority] = useState(3);
  const [tags, setTags] = useState("");
  const [pendingDetail, setPendingDetail] = useState<ResourceDetail | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadingFileName, setUploadingFileName] = useState("");

  const capture = useMutation({
    mutationFn: () => api.capture({ content, capture_type: mode === "link" ? "webpage" : "text", title, summary, process_goal: goal, estimated_minutes: minutes, priority, tags, next_action: "triage" }),
    onSuccess: async (detail) => {
      setPendingDetail(detail);
      await qc.invalidateQueries();
      showToast("已采集，请确认保存原因和处理计划");
    },
    onError: (error) => showToast(error instanceof Error ? error.message : "采集失败")
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadFile(file),
    onSuccess: async (detail) => {
      setUploadingFileName("");
      setPendingDetail(detail);
      await qc.invalidateQueries();
      showToast("文件已上传，请补充保存原因");
    },
    onError: (error) => {
      setUploadingFileName("");
      showToast(error instanceof Error ? error.message : "上传失败");
    }
  });

  function handleFile(file?: File) {
    if (!file) return;
    setUploadingFileName(file.name);
    upload.mutate(file);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (mode !== "file" && !content.trim()) {
      showToast("请输入链接或文本内容");
      return;
    }
    capture.mutate();
  }

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-[18px] font-semibold">统一采集入口</h2>
          <p className="text-[13px] text-muted">链接、文本、PDF、Word、视频都先进入确认卡，不再丢进黑洞。</p>
        </div>
        <div className="flex rounded-md border border-line bg-panel p-1">
          {[
            ["link", "链接"],
            ["text", "文本"],
            ["file", "文件"]
          ].map(([id, label]) => (
            <button key={id} onClick={() => setMode(id as "link" | "text" | "file")} className={`rounded px-3 py-2 text-[13px] ${mode === id ? "bg-white shadow-sm" : "text-muted"}`} type="button">
              {label}
            </button>
          ))}
        </div>
      </div>

      {mode === "file" ? (
        <label
          className={`flex cursor-pointer flex-col items-center justify-center rounded-md border border-dashed p-6 text-center hover:border-accent ${dragActive ? "border-accent bg-white" : "border-line bg-paper"}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            handleFile(e.dataTransfer.files?.[0]);
          }}
        >
          <Upload className="text-accent" />
          <span className="mt-2 font-medium">{upload.isPending ? `正在上传：${uploadingFileName}` : "选择或拖入文件"}</span>
          <span className="mt-1 text-[13px] text-muted">支持 PDF、Word、TXT、Markdown、MP4、MOV、MKV</span>
          <input className="hidden" type="file" accept=".pdf,.doc,.docx,.txt,.md,.markdown,.mp4,.mov,.mkv,.webm" onChange={(e) => handleFile(e.target.files?.[0])} />
        </label>
      ) : (
        <form onSubmit={submit} className="grid gap-3">
          <textarea value={content} onChange={(e) => setContent(e.target.value)} className="min-h-[96px] rounded-md border border-line bg-paper p-3 outline-none focus:border-accent" placeholder={mode === "link" ? "粘贴网页、B站、YouTube、论文链接..." : "粘贴文章片段、课程文字、想法..."} />
          <div className="grid gap-3 md:grid-cols-2">
            <input value={title} onChange={(e) => setTitle(e.target.value)} className="h-11 rounded-md border border-line px-3 outline-none focus:border-accent" placeholder="标题，可留空自动生成" />
            <input value={summary} onChange={(e) => setSummary(e.target.value)} className="h-11 rounded-md border border-line px-3 outline-none focus:border-accent" placeholder="为什么保存它？" />
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <select value={goal} onChange={(e) => setGoal(e.target.value)} className="h-11 rounded-md border border-line bg-white px-3">
              {["学习", "答辩素材", "论文证据", "工具 SOP", "英语", "临时参考"].map((item) => <option key={item}>{item}</option>)}
            </select>
            <select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} className="h-11 rounded-md border border-line bg-white px-3">
              <option value={10}>10 分钟</option>
              <option value={30}>30 分钟</option>
              <option value={60}>1 小时+</option>
            </select>
            <select value={priority} onChange={(e) => setPriority(Number(e.target.value))} className="h-11 rounded-md border border-line bg-white px-3">
              <option value={2}>低优先级</option>
              <option value={3}>中优先级</option>
              <option value={4}>高优先级</option>
            </select>
            <input value={tags} onChange={(e) => setTags(e.target.value)} className="h-11 rounded-md border border-line px-3 outline-none focus:border-accent" placeholder="标签，用空格分隔" />
          </div>
          <button className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-accent px-4 text-white disabled:opacity-60" disabled={capture.isPending}>
            {capture.isPending ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            采集并生成确认卡
          </button>
        </form>
      )}

      {pendingDetail && <CaptureConfirmCard detail={pendingDetail} navigate={navigate} showToast={showToast} />}
    </section>
  );
}

function CaptureConfirmCard({ detail, navigate, showToast }: { detail: ResourceDetail; navigate: (view: string, id?: string) => void; showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const { setSelectedTaskId } = useAppStore();
  const [title, setTitle] = useState(detail.resource.title);
  const [summary, setSummary] = useState(detail.resource.summary || "");
  const [goal, setGoal] = useState("active_learning");
  const [minutes, setMinutes] = useState(detail.resource.estimated_minutes || 30);
  const [priority, setPriority] = useState(Math.max(2, Math.min(4, Math.round(detail.resource.heat_score || 3))));
  const [tags, setTags] = useState((detail.resource.tags ?? []).join(" "));
  const [saving, setSaving] = useState(false);

  async function saveThen(action: "detail" | "process" | "reference") {
    if (!summary.trim() || summary.includes("请补充")) {
      showToast("请先写清楚为什么保存它");
      return;
    }
    setSaving(true);
    try {
      await api.updateResource(detail.resource.id, { title: title.trim(), summary: summary.trim(), estimated_minutes: minutes, priority, tags });
      if (action === "process") {
        const result = await api.decideInbox(detail.resource.id, { keep: true, purpose: goal, estimated_minutes: minutes });
        setSelectedTaskId(result.task_id);
        showToast("已确认并生成处理任务");
        navigate("processing");
      } else if (action === "reference") {
        await api.decideInbox(detail.resource.id, { keep: true, purpose: "reference", estimated_minutes: minutes });
        showToast("已作为参考资料留存");
        navigate("resources");
      } else {
        showToast("确认卡已保存，可以继续批注");
        navigate("resource", detail.resource.id);
      }
      await qc.invalidateQueries();
    } catch (error) {
      showToast(error instanceof Error ? error.message : "确认失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-4 rounded-md border border-accent bg-paper p-4">
      <div className="mb-3">
        <div className="font-semibold">录入确认 + 快判</div>
        <p className="mt-1 text-[13px] text-muted">先把“这是什么、为什么保存、多久处理”补齐，再决定去向。</p>
      </div>
      {detail.resource.source_description && (
        <div className="mb-3 rounded-md border border-line bg-white p-3">
          <div className="font-mono text-[12px] text-accent">网页识别描述</div>
          <p className="mt-1 break-words text-[13px] leading-5 text-muted">{detail.resource.source_description}</p>
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        <input value={title} onChange={(e) => setTitle(e.target.value)} className="h-11 rounded-md border border-line px-3" placeholder="标题" />
        <input value={tags} onChange={(e) => setTags(e.target.value)} className="h-11 rounded-md border border-line px-3" placeholder="标签：论文 英语 项目A" />
        <textarea value={summary} onChange={(e) => setSummary(e.target.value)} className="min-h-[92px] rounded-md border border-line p-3 md:col-span-2" placeholder="为什么保存它？后面再看时，你希望自己立刻明白什么？" />
        <select value={goal} onChange={(e) => setGoal(e.target.value)} className="h-11 rounded-md border border-line bg-white px-3">
          <option value="active_learning">深处理：学习/论文/答辩素材</option>
          <option value="preview">速看：先判断价值</option>
        </select>
        <select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} className="h-11 rounded-md border border-line bg-white px-3">
          <option value={10}>10 分钟速看</option>
          <option value={30}>30 分钟处理</option>
          <option value={60}>1 小时+</option>
        </select>
        <select value={priority} onChange={(e) => setPriority(Number(e.target.value))} className="h-11 rounded-md border border-line bg-white px-3">
          <option value={2}>低优先级</option>
          <option value={3}>中优先级</option>
          <option value={4}>高优先级</option>
        </select>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button disabled={saving} onClick={() => saveThen("process")} className="rounded-md bg-ink px-4 py-2 text-white disabled:opacity-60">确认并进入处理</button>
        <button disabled={saving} onClick={() => saveThen("detail")} className="rounded-md border border-line px-4 py-2 disabled:opacity-60">先打开详情批注</button>
        <button disabled={saving} onClick={() => saveThen("reference")} className="rounded-md border border-line px-4 py-2 disabled:opacity-60">只作参考留存</button>
      </div>
    </div>
  );
}

function InboxView({ navigate, showToast }: { navigate: (view: string, id?: string) => void; showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const [minutes, setMinutes] = useState(30);
  const { data: detail, isLoading } = useQuery({ queryKey: ["inbox-next"], queryFn: api.nextInbox, placeholderData: keepPreviousData });
  const resource = detail?.resource;
  const decide = useMutation({
    mutationFn: (payload: { keep: boolean; purpose: string }) => api.decideInbox(resource!.id, { ...payload, estimated_minutes: minutes }),
    onSuccess: async (_, payload) => {
      await qc.invalidateQueries();
      showToast(payload.keep ? "已生成处理任务" : "资源已删除");
    }
  });
  if (isLoading && !detail) return <Loading />;
  if (!resource) return <Empty title="Inbox 已清空" action="继续从工作台采集新资源。" />;
  return (
    <div className="mx-auto grid max-w-4xl gap-4">
      <h1 className="font-serif text-[28px]">Inbox 快判</h1>
      <ResourceCard resource={resource} onOpen={() => navigate("resource", resource.id)} />
      <div className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 text-[14px] text-muted">先确认用途和预计处理时间，再决定它是否值得进入任务台。</div>
        <select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} className="mb-3 h-11 rounded-md border border-line bg-white px-3">
          <option value={10}>10 分钟速看</option>
          <option value={30}>30 分钟深处理</option>
          <option value={60}>1 小时+</option>
        </select>
        <div className="grid gap-3 sm:grid-cols-4">
          <button onClick={() => decide.mutate({ keep: true, purpose: "active_learning" })} className="rounded-md bg-success px-4 py-3 text-white">留下并处理</button>
          <button onClick={() => decide.mutate({ keep: true, purpose: "reference" })} className="rounded-md border border-line px-4 py-3">只作参考</button>
          <button onClick={() => navigate("resource", resource.id)} className="rounded-md border border-line px-4 py-3">先批注</button>
          <button onClick={() => decide.mutate({ keep: false, purpose: "discard" })} className="rounded-md border border-danger px-4 py-3 text-danger">删除</button>
        </div>
      </div>
    </div>
  );
}

function ResourceLibrary({ navigate }: { navigate: (view: string, id?: string) => void }) {
  const [type, setType] = useState("all");
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const { data, isLoading } = useQuery({ queryKey: ["resources", type, status], queryFn: () => api.resources(status || undefined, type), placeholderData: keepPreviousData });
  const filtered = (data ?? []).filter((resource) => {
    const needle = q.trim().toLowerCase();
    if (!needle) return true;
    return [resource.title, resource.summary, resource.source_platform, resource.original_url, ...(resource.tags ?? [])].filter(Boolean).join(" ").toLowerCase().includes(needle);
  });
  if (isLoading && !data) return <Loading />;
  return (
    <div className="mx-auto grid max-w-7xl gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-serif text-[28px]">资源库</h1>
        <div className="grid w-full gap-2 sm:w-auto sm:grid-cols-[180px_160px_240px]">
          <select value={type} onChange={(e) => setType(e.target.value)} className="h-10 min-w-0 rounded-md border border-line bg-white px-3">
            <option value="all">全部类型</option>
            <option value="webpage">网页</option>
            <option value="text">文本</option>
            <option value="pdf">PDF</option>
            <option value="word">Word</option>
            <option value="video">视频</option>
          </select>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="h-10 min-w-0 rounded-md border border-line bg-white px-3">
            <option value="">全部状态</option>
            <option value="inbox">Inbox</option>
            <option value="to_preview">速看</option>
            <option value="to_process">深处理</option>
            <option value="reviewing">复习中</option>
            <option value="archived">归档</option>
          </select>
          <input value={q} onChange={(e) => setQ(e.target.value)} className="h-10 min-w-0 rounded-md border border-line bg-white px-3" placeholder="筛标题、原因、标签" />
        </div>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {filtered.map((resource) => <ResourceCard key={resource.id} resource={resource} onOpen={() => navigate("resource", resource.id)} />)}
        {!filtered.length && <Empty title="没有匹配资源" action="换一个筛选条件，或先从工作台采集新资源。" />}
      </div>
    </div>
  );
}

function ResourceDetailView({ resourceId, showToast }: { resourceId: string; showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const { setSelectedTaskId, setActiveView } = useAppStore();
  const { data, isLoading } = useQuery({ queryKey: ["resource", resourceId], queryFn: () => api.resourceDetail(resourceId), placeholderData: keepPreviousData });
  const [noteType, setNoteType] = useState("annotation");
  const [noteContent, setNoteContent] = useState("");
  const [sourceRange, setSourceRange] = useState("");
  const annotation = useMutation({
    mutationFn: () => api.createAnnotation(resourceId, { note_type: noteType, content: noteContent, source_range: sourceRange }),
    onSuccess: async () => {
      setNoteContent("");
      setSourceRange("");
      await qc.invalidateQueries({ queryKey: ["resource", resourceId] });
      showToast("批注已保存");
    },
    onError: (error) => showToast(error instanceof Error ? error.message : "批注失败")
  });
  const update = useMutation({
    mutationFn: (payload: Parameters<typeof api.updateResource>[1]) => api.updateResource(resourceId, payload),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["resource", resourceId] });
      showToast("资源已更新");
    }
  });
  const startProcessing = useMutation({
    mutationFn: () => api.decideInbox(resourceId, { keep: true, purpose: "active_learning", estimated_minutes: data?.resource.estimated_minutes ?? 30 }),
    onSuccess: async (result) => {
      setSelectedTaskId(result.task_id);
      await qc.invalidateQueries();
      showToast("已生成处理任务");
      setActiveView("processing");
      window.history.pushState({ view: "processing" }, "", "/?view=processing");
    },
    onError: (error) => showToast(error instanceof Error ? error.message : "生成处理任务失败")
  });
  const summarize = useMutation({
    mutationFn: () => api.summarize(resourceId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["resource", resourceId] });
      showToast("摘要草稿已生成，请人工确认后再使用");
    },
    onError: (error) => showToast(error instanceof Error ? error.message : "摘要生成失败")
  });
  const generateAnki = useMutation({
    mutationFn: () => api.generateAnki(resourceId),
    onSuccess: () => showToast("Anki 草稿卡已生成"),
    onError: (error) => showToast(error instanceof Error ? error.message : "Anki 草稿生成失败")
  });
  if (isLoading || !data) return <Loading />;
  const resource = data.resource;
  return (
    <div className="grid gap-4 xl:grid-cols-[280px_1fr_360px]">
      <aside className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 font-semibold">资源信息</div>
        <input className="mb-2 h-10 w-full rounded-md border border-line px-3" defaultValue={resource.title} onBlur={(e) => e.target.value !== resource.title && update.mutate({ title: e.target.value })} />
        <textarea className="mb-2 min-h-[100px] w-full rounded-md border border-line p-3" defaultValue={resource.summary || ""} placeholder="为什么保存它？" onBlur={(e) => e.target.value !== resource.summary && update.mutate({ summary: e.target.value })} />
        <input className="mb-2 h-10 w-full rounded-md border border-line px-3" defaultValue={(resource.tags ?? []).join(" ")} placeholder="标签，用空格分隔" onBlur={(e) => update.mutate({ tags: e.target.value })} />
        <select className="mb-2 h-10 w-full rounded-md border border-line bg-white px-3" defaultValue={resource.status} onChange={(e) => update.mutate({ status: e.target.value })}>
          <option value="inbox">Inbox 待判</option>
          <option value="to_preview">速看</option>
          <option value="to_process">深处理</option>
          <option value="processing">处理中</option>
          <option value="reviewing">复习中</option>
          <option value="archived">已归档</option>
          <option value="discarded">已放弃</option>
        </select>
        <div className="mb-2 grid grid-cols-2 gap-2">
          <select className="h-10 rounded-md border border-line bg-white px-3" defaultValue={resource.estimated_minutes} onChange={(e) => update.mutate({ estimated_minutes: Number(e.target.value) })}>
            <option value={10}>10 分钟</option>
            <option value={30}>30 分钟</option>
            <option value={60}>1 小时+</option>
          </select>
          <select className="h-10 rounded-md border border-line bg-white px-3" defaultValue={Math.max(2, Math.min(4, Math.round(resource.heat_score || 3)))} onChange={(e) => update.mutate({ priority: Number(e.target.value) })}>
            <option value={2}>低优先级</option>
            <option value={3}>中优先级</option>
            <option value={4}>高优先级</option>
          </select>
        </div>
        <InfoLine label="类型" value={resource.type} />
        <InfoLine label="来源" value={resource.source_platform || resource.original_url || "本地"} />
        {resource.source_description && <InfoLine label="来源描述" value={resource.source_description} />}
        <InfoLine label="最近触碰" value={new Date(resource.last_touched_at).toLocaleString()} />
        <button onClick={() => startProcessing.mutate()} className="mt-3 w-full rounded-md bg-ink px-3 py-2 text-[14px] text-white">送入处理台</button>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <button onClick={() => summarize.mutate()} className="rounded-md border border-line px-3 py-2 text-[13px] hover:bg-panel">摘要草稿</button>
          <button onClick={() => generateAnki.mutate()} className="rounded-md border border-line px-3 py-2 text-[13px] hover:bg-panel">Anki 草稿</button>
        </div>
        {data.files[0] && <a className="mt-3 block rounded-md border border-line px-3 py-2 text-[14px] hover:bg-panel" href={data.files[0].download_url} target="_blank">打开/下载文件</a>}
        {data.files[0] && (
          <div className="mt-3 rounded-md border border-line bg-paper p-3 text-[13px]">
            <div className="font-semibold">文件信息</div>
            <InfoLine label="文件名" value={data.files[0].file_name} />
            <InfoLine label="格式" value={data.files[0].file_type} />
            <InfoLine label="大小" value={formatFileSize(data.files[0].file_size)} />
          </div>
        )}
      </aside>
      <section className="min-w-0 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-center gap-2 font-semibold"><FileText size={18} /> 阅读区</div>
        {resource.type === "video" && data.files[0] ? (
          <video className="mb-4 max-h-[420px] w-full rounded-md bg-black" src={data.files[0].download_url} controls />
        ) : null}
        <div className="grid gap-3">
          {data.chunks.length ? data.chunks.map((chunk) => (
            <article key={chunk.id} className="rounded-md border border-line bg-paper p-3">
              <div className="mb-2 font-mono text-[12px] text-accent">{chunk.heading || chunk.chunk_type}{chunk.page_number ? ` · 第 ${chunk.page_number} 页` : ""}</div>
              <p className="whitespace-pre-wrap break-words text-[14px] leading-6">{chunk.content}</p>
            </article>
          )) : <Empty title="暂无可预览内容" action="你仍然可以先写批注、设置处理计划。" />}
        </div>
      </section>
      <aside className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 font-semibold">批注与输出</div>
        <div className="grid gap-2">
          <select value={noteType} onChange={(e) => setNoteType(e.target.value)} className="h-10 rounded-md border border-line bg-white px-3">
            <option value="annotation">普通备注</option>
            <option value="excerpt">摘录</option>
            <option value="question">问题</option>
            <option value="evidence">证据</option>
            <option value="action">行动项</option>
            <option value="anki_candidate">Anki 候选</option>
            <option value="project_material">项目素材</option>
          </select>
          <input value={sourceRange} onChange={(e) => setSourceRange(e.target.value)} className="h-10 rounded-md border border-line px-3" placeholder={resource.type === "video" ? "时间点，如 03:20" : resource.type === "pdf" ? "页码，如 第 3 页" : "页码/时间点/文本范围，可选"} />
          <textarea value={noteContent} onChange={(e) => setNoteContent(e.target.value)} className="min-h-[120px] rounded-md border border-line p-3" placeholder="写批注、问题、证据或下一步动作..." />
          <button onClick={() => annotation.mutate()} className="rounded-md bg-accent px-4 py-2 text-white">保存批注</button>
        </div>
        <div className="mt-4 grid gap-2">
          {data.notes.map((note) => (
            <div key={note.id} className="rounded-md border border-line bg-paper p-3">
              <div className="text-[13px] font-semibold">{note.title}</div>
              <div className="mt-1 whitespace-pre-wrap break-words text-[13px] text-muted">{note.content}</div>
              {note.source_range && <div className="mt-1 font-mono text-[12px] text-accent">{note.source_range}</div>}
            </div>
          ))}
        </div>
        {(data.ai_outputs.length > 0 || data.anki_cards.length > 0) && (
          <div className="mt-5 grid gap-2">
            <div className="font-semibold">草稿输出</div>
            {data.ai_outputs.map((output) => (
              <div key={output.id} className="rounded-md border border-line bg-paper p-3">
                <div className="font-mono text-[12px] text-accent">{output.output_type} · {output.verification_status}</div>
                <p className="mt-1 whitespace-pre-wrap break-words text-[13px] text-muted">{output.content}</p>
              </div>
            ))}
            {data.anki_cards.map((card) => (
              <div key={card.id} className="rounded-md border border-line bg-paper p-3">
                <div className="font-mono text-[12px] text-accent">Anki 草稿</div>
                <div className="mt-1 text-[13px] font-semibold">{card.front}</div>
                <p className="mt-1 whitespace-pre-wrap break-words text-[13px] text-muted">{card.back}</p>
              </div>
            ))}
          </div>
        )}
      </aside>
    </div>
  );
}

function ProcessingDesk({ navigate, showToast }: { navigate: (view: string, id?: string) => void; showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const { selectedTaskId, setSelectedTaskId } = useAppStore();
  const { data: tasks } = useQuery({ queryKey: ["tasks"], queryFn: api.tasks, placeholderData: keepPreviousData });
  const [processOutput, setProcessOutput] = useState("");
  const task = useMemo(() => {
    const pending = (tasks ?? []).filter((item) => item.status === "pending");
    return pending.find((item) => item.id === selectedTaskId) ?? pending[0];
  }, [selectedTaskId, tasks]);
  const { data: detail } = useQuery({
    queryKey: ["processing-resource", task?.resource_id],
    queryFn: () => api.resourceDetail(task!.resource_id!),
    enabled: Boolean(task?.resource_id),
    placeholderData: keepPreviousData
  });
  const complete = useMutation({
    mutationFn: async (id: string) => {
      if (task?.resource_id && processOutput.trim()) {
        await api.createAnnotation(task.resource_id, {
          note_type: "project_material",
          title: "处理台输出",
          content: processOutput.trim()
        });
      }
      return api.completeTask(id);
    },
    onSuccess: async () => {
      setProcessOutput("");
      await qc.invalidateQueries();
      showToast("任务完成，已进入复习沉淀");
    }
  });
  if (!task) return <Empty title="没有待处理任务" action="先采集资源并完成快判，它会生成处理任务。" />;
  return (
    <div className="grid gap-4">
      <header className="rounded-md border border-line bg-ink p-5 text-white">
        <div className="text-[13px] text-white/70">单任务锁定模式</div>
        <h1 className="mt-1 break-words font-serif text-[26px]">{task.title}</h1>
        <div className="mt-2 flex flex-wrap gap-3 text-[13px] text-white/70">
          <span>{task.task_type}</span>
          <span>{task.estimated_minutes} 分钟</span>
          <span>P{task.priority}</span>
        </div>
      </header>
      <section className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <div className="grid gap-4">
          <div className="rounded-md border border-line bg-white p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="font-semibold">当前资源</h2>
              {task.resource_id && <button onClick={() => navigate("resource", task.resource_id)} className="rounded-md border border-line px-3 py-2 text-[13px]">详情/批注</button>}
            </div>
            {detail?.resource.type === "video" && detail.files[0] ? <video className="mb-4 max-h-[340px] w-full rounded-md bg-black" src={detail.files[0].download_url} controls /> : null}
            <div className="grid max-h-[460px] gap-3 overflow-y-auto pr-1">
              {detail?.chunks.length ? detail.chunks.slice(0, 8).map((chunk) => (
                <article key={chunk.id} className="rounded-md border border-line bg-paper p-3">
                  <div className="mb-1 font-mono text-[12px] text-accent">{chunk.heading || chunk.chunk_type}{chunk.page_number ? ` · 第 ${chunk.page_number} 页` : ""}</div>
                  <p className="whitespace-pre-wrap break-words text-[14px] leading-6">{chunk.content}</p>
                </article>
              )) : <Empty title="暂无可预览内容" action="可以先根据标题、来源和保存原因写处理判断。" />}
            </div>
          </div>
          <div className="rounded-md border border-line bg-white p-4">
            <h2 className="mb-3 font-semibold">本轮处理输出</h2>
            <textarea value={processOutput} onChange={(e) => setProcessOutput(e.target.value)} className="h-[260px] w-full resize-none rounded-md border border-line bg-paper p-4" placeholder="写一句核心价值、3 个知识点、1 个疑问，以及下一步动作。完成任务时会保存为批注/项目素材。" />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-4">
          <h2 className="font-semibold">完成标准</h2>
          <div className="mt-3 grid gap-2 text-[14px]">
            <label><input type="checkbox" /> 核心价值已写明</label>
            <label><input type="checkbox" /> 3 个知识点已提取</label>
            <label><input type="checkbox" /> 1 个疑问或证据点已记录</label>
            <label><input type="checkbox" /> 下一步动作已设置</label>
          </div>
          <div className="mt-4 grid gap-2">
            {task.resource_id && <button onClick={() => navigate("resource", task.resource_id)} className="rounded-md border border-line px-4 py-2">打开资源详情</button>}
            <button onClick={() => complete.mutate(task.id)} className="rounded-md bg-success px-4 py-2 text-white">标记完成</button>
          </div>
          {detail?.notes.length ? (
            <div className="mt-5">
              <h3 className="mb-2 text-[14px] font-semibold">已有批注</h3>
              <div className="grid gap-2">
                {detail.notes.slice(0, 4).map((note) => <div key={note.id} className="rounded-md bg-panel p-3 text-[13px]"><div className="font-semibold">{note.title}</div><p className="mt-1 break-words text-muted">{note.content}</p></div>)}
              </div>
            </div>
          ) : null}
        </div>
      </section>
      <TaskList tasks={tasks ?? []} onPick={(item) => setSelectedTaskId(item.id)} emptyText="暂无任务。" />
    </div>
  );
}

function ProjectsView({ showToast }: { showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const { data } = useQuery({ queryKey: ["projects"], queryFn: api.projects, placeholderData: keepPreviousData });
  const create = useMutation({ mutationFn: () => api.createProject({ name: name.trim() }), onSuccess: async () => { setName(""); await qc.invalidateQueries({ queryKey: ["projects"] }); showToast("项目已创建"); } });
  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <h1 className="font-serif text-[28px]">项目空间</h1>
      <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) create.mutate(); }} className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="输入项目标题，10 秒创建" className="h-11 rounded-md border border-line bg-white px-3" />
        <button className="rounded-md bg-ink px-4 text-white">创建</button>
      </form>
      <div className="grid gap-3 sm:grid-cols-2">
        {data?.map((item) => <div key={item.id} className="rounded-md border border-line bg-white p-4"><h2 className="font-semibold">{item.name}</h2><p className="mt-2 text-[14px] text-muted">{item.description || "等待资源、批注、任务和输出自然长出来。"}</p></div>)}
      </div>
    </div>
  );
}

function ReviewView({ showToast }: { showToast: (message: string) => void }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["reviews"], queryFn: api.reviews, placeholderData: keepPreviousData });
  const item = data?.[0];
  const complete = useMutation({ mutationFn: (quality: string) => api.completeReview(item.id, quality), onSuccess: async () => { await qc.invalidateQueries(); showToast("复习已记录"); } });
  if (!item) return <Empty title="今天没有复习项" action="处理台完成任务后会生成新的复习提醒。" />;
  return (
    <div className="mx-auto grid max-w-3xl gap-4">
      <h1 className="font-serif text-[28px]">主动复述</h1>
      <div className="rounded-md border border-line bg-white p-5">
        <h2 className="text-[20px] font-semibold">{item.prompt}</h2>
        <textarea className="mt-4 h-48 w-full resize-none rounded-md border border-line bg-paper p-4" placeholder="先自己回答，再决定熟悉程度。" />
        <div className="mt-4 flex gap-2">
          <button onClick={() => complete.mutate("known")} className="rounded-md bg-success px-4 py-2 text-white">知道</button>
          <button onClick={() => complete.mutate("fuzzy")} className="rounded-md border border-line px-4 py-2">模糊</button>
          <button onClick={() => complete.mutate("unknown")} className="rounded-md border border-danger px-4 py-2 text-danger">不会</button>
        </div>
      </div>
    </div>
  );
}

function SearchView({ navigate }: { navigate: (view: string, id?: string) => void }) {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const { data, isFetching } = useQuery({ queryKey: ["search", submitted], queryFn: () => api.search(submitted), enabled: Boolean(submitted), placeholderData: keepPreviousData });
  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <h1 className="font-serif text-[28px]">跨资源搜索</h1>
      <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) setSubmitted(q.trim()); }} className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索标题、保存原因、批注、正文片段" className="h-12 rounded-md border border-line bg-white px-4" />
        <button className="rounded-md bg-ink px-5 text-white">{isFetching ? "搜索中" : "搜索"}</button>
      </form>
      <div className="grid gap-3">
        {data?.map((item) => (
          <button key={`${item.kind}-${item.id}`} onClick={() => item.resource_id ? navigate("resource", item.resource_id) : item.kind === "resource" && navigate("resource", item.id)} className="rounded-md border border-line bg-white p-4 text-left hover:border-accent">
            <div className="font-mono text-[13px] text-accent">{item.kind} · {item.location || "资源"}</div>
            <h2 className="mt-1 font-semibold">{item.title}</h2>
            <p className="mt-2 break-words text-[14px] text-muted">{item.snippet}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

function SettingsView() {
  return (
    <div className="mx-auto grid max-w-3xl gap-4">
      <h1 className="font-serif text-[28px]">设置</h1>
      <div className="rounded-md border border-line bg-white p-5 text-[14px] text-muted">
        当前版本优先保证本地可用：SQLite 本地库、storage 本地文件、基础 PDF/Word/TXT 提取、视频保存播放。后续可切换 PostgreSQL、MinIO、Meilisearch。
      </div>
    </div>
  );
}

function ResourceCard({ resource, onOpen }: { resource: Resource; onOpen: () => void }) {
  return (
    <button onClick={onOpen} className="status-edge rounded-md border border-line bg-white p-4 pl-5 text-left shadow-sm hover:border-accent" style={{ "--edge": statusColor[resource.status] ?? "#D8D5CE" } as React.CSSProperties}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-mono text-[12px] text-muted">{resource.source_platform || "本地"} · {resource.type} · {resource.status}</div>
          <h2 className="mt-1 break-words text-[18px] font-semibold">{displayTitle(resource.title)}</h2>
        </div>
        <div className="rounded-md bg-panel px-3 py-2 font-mono text-[13px]">热度 {resource.heat_score.toFixed(1)}</div>
      </div>
      <p className="mt-3 break-words text-[14px] leading-6 text-muted">{resource.summary}</p>
      {resource.source_description && <p className="mt-2 line-clamp-2 break-words text-[13px] leading-5 text-muted">来源：{resource.source_description}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {(resource.tags ?? []).map((tag) => <span key={tag} className="rounded bg-panel px-2 py-1 text-[12px] text-muted">#{tag}</span>)}
        <span className="rounded bg-panel px-2 py-1 text-[12px] text-muted">{resource.estimated_minutes} 分钟</span>
      </div>
      {resource.original_url && <p className="mt-2 break-all text-[12px] text-cold">{resource.original_url}</p>}
    </button>
  );
}

function TaskList({ tasks, onPick, emptyText }: { tasks: Task[]; onPick?: (task: Task) => void; emptyText: string }) {
  if (!tasks.length) return <div className="rounded-md bg-panel p-4 text-[14px] text-muted">{emptyText}</div>;
  return <div className="grid gap-2">{tasks.map((task) => <button key={task.id} onClick={() => onPick?.(task)} className="rounded-md border border-line bg-white p-3 text-left hover:border-accent"><div className="flex justify-between gap-3"><span className="break-words font-medium">{task.title}</span><span className="shrink-0 font-mono text-[12px] text-muted">{task.estimated_minutes}m</span></div><div className="mt-1 text-[13px] text-muted">{task.task_type} · P{task.priority} · {task.status}</div></button>)}</div>;
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return <div className="mb-2 text-[13px]"><span className="text-muted">{label}：</span><span className="break-words">{value}</span></div>;
}

function Empty({ title, action }: { title: string; action: string }) {
  return <div className="rounded-md border border-line bg-white p-6 text-center"><Archive className="mx-auto text-cold" /><h2 className="mt-3 font-semibold">{title}</h2><p className="mt-2 text-[14px] text-muted">{action}</p></div>;
}

function Loading() {
  return <div className="flex h-64 items-center justify-center text-muted"><Loader2 className="mr-2 animate-spin" size={18} />正在加载</div>;
}

function displayTitle(value: string) {
  if (!value.startsWith("http")) return value;
  try {
    const url = new URL(value);
    return url.hostname;
  } catch {
    return value;
  }
}

function formatFileSize(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function statName(key: string) {
  return ({ pending_tasks: "待处理", inbox: "Inbox", captured_today: "今日入库", processed_today: "今日处理", stale: "积压 7 天", ai_drafts: "AI 草稿", reviews: "复习", cold: "冷存", annotated: "已批注" }[key] ?? key);
}

export default function Page() {
  return <QueryProvider><Shell /></QueryProvider>;
}
