"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  authApi,
  connectorsApi,
  queryApi,
  documentsApi,
  adminApi,
  notesApi,
  graphApi,
} from "@/lib/api";
import { useAuthStore, useUIStore, WorkspaceTab } from "@/lib/store";
import type {
  Connector,
  Document,
  QueryResult,
  QueryHistoryItem,
  AuditLog,
  ThemeMode,
  Note,
  GraphData,
  GraphNode,
  ChunkDetail,
  ConnectorTestResult,
  ConnectorLog,
} from "@/types";
import {
  Search,
  Plug,
  Files,
  ShieldCheck,
  Globe,
  Mail,
  FolderGit2,
  FileSpreadsheet,
  Inbox,
  MessageSquare,
  Sparkles,
  RefreshCw,
  UploadCloud,
  ExternalLink,
  X,
  ChevronRight,
  Plus,
  Trash2,
  Filter,
  Copy,
  Check,
  LogOut,
  User as UserIcon,
  Activity,
  Database,
  FileText,
  BarChart3,
  Loader2,
  Clock,
  CheckCircle2,
  AlertCircle,
  Menu,
  FileCode,
  Info,
  Settings,
  Sun,
  Moon,
  Laptop,
  HelpCircle,
  AlertTriangle,
  RotateCw,
  Power,
  Share2,
  Network,
  BookOpen,
  Edit3,
  Zap,
  Terminal,
  Download,
  Eye,
  Layers,
} from "lucide-react";

const SOURCE_CONFIG: Record<string, { label: string; icon: any; color: string; bg: string }> = {
  all: { label: "All Sources", icon: Globe, color: "text-indigo-400", bg: "bg-indigo-500/10 border-indigo-500/30" },
  gmail: { label: "Gmail", icon: Mail, color: "text-rose-400", bg: "bg-rose-500/10 border-rose-500/30" },
  google_drive: { label: "Google Drive", icon: FolderGit2, color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/30" },
  sheets: { label: "Sheets / Excel", icon: FileSpreadsheet, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/30" },
  outlook: { label: "Outlook", icon: Inbox, color: "text-sky-400", bg: "bg-sky-500/10 border-sky-500/30" },
  whatsapp: { label: "WhatsApp", icon: MessageSquare, color: "text-teal-400", bg: "bg-teal-500/10 border-teal-500/30" },
  notes: { label: "Note Studio", icon: BookOpen, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/30" },
};

export default function WorkspacePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, clearAuth } = useAuthStore();
  const { activeTab, setActiveTab } = useUIStore();

  // Local States
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState("all");
  const [askInput, setAskInput] = useState("");
  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const [activeResult, setActiveResult] = useState<QueryResult | null>(null);
  const [copiedAnswer, setCopiedAnswer] = useState(false);
  const [selectedSourceDrawer, setSelectedSourceDrawer] = useState<any | null>(null);

  // Inspector & Note States
  const [inspectingDoc, setInspectingDoc] = useState<Document | null>(null);
  const [editingChunk, setEditingChunk] = useState<ChunkDetail | null>(null);
  const [chunkEditText, setChunkEditText] = useState("");
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [noteTagsInput, setNoteTagsInput] = useState("");

  // Connector Diagnostics
  const [testingConnector, setTestingConnector] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ type: string; res: ConnectorTestResult } | null>(null);
  const [viewingLogsType, setViewingLogsType] = useState<string | null>(null);

  // Graph Selected Node
  const [selectedGraphNode, setSelectedGraphNode] = useState<GraphNode | null>(null);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Fetch Core Queries
  const { data: connectors = [], isLoading: connectorsLoading } = useQuery({
    queryKey: ["connectors"],
    queryFn: connectorsApi.list,
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: adminApi.stats,
  });

  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ["documents", selectedSource],
    queryFn: () => documentsApi.list(selectedSource),
  });

  const { data: queryHistory = [] } = useQuery({
    queryKey: ["queryHistory"],
    queryFn: () => queryApi.history(15),
  });

  const { data: notes = [], isLoading: notesLoading } = useQuery({
    queryKey: ["notes"],
    queryFn: notesApi.list,
  });

  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: ["graphData"],
    queryFn: graphApi.get,
  });

  const { data: chunks = [], refetch: refetchChunks } = useQuery({
    queryKey: ["docChunks", inspectingDoc?.id],
    queryFn: () => (inspectingDoc ? documentsApi.listChunks(inspectingDoc.id) : Promise.resolve([])),
    enabled: !!inspectingDoc,
  });

  const { data: connectorLogs = [] } = useQuery({
    queryKey: ["connectorLogs", viewingLogsType],
    queryFn: () => (viewingLogsType ? connectorsApi.logs(viewingLogsType) : Promise.resolve([])),
    enabled: !!viewingLogsType,
  });

  // Ask Query Mutation
  const askMutation = useMutation({
    mutationFn: (q: string) => queryApi.ask(q, 5, selectedSource),
    onSuccess: (data, variables) => {
      setActiveResult(data);
      setActiveQuery(variables);
      queryClient.invalidateQueries({ queryKey: ["queryHistory"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  // Note Mutations
  const createNoteMutation = useMutation({
    mutationFn: (data: { title: string; content: string; tags: string[] }) =>
      notesApi.create(data.title, data.content, data.tags),
    onSuccess: (newNote) => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      queryClient.invalidateQueries({ queryKey: ["graphData"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setEditingNote(newNote);
    },
  });

  const updateNoteMutation = useMutation({
    mutationFn: (data: { id: string; title: string; content: string; tags: string[] }) =>
      notesApi.update(data.id, data.title, data.content, data.tags),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      queryClient.invalidateQueries({ queryKey: ["graphData"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const deleteNoteMutation = useMutation({
    mutationFn: (id: string) => notesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      queryClient.invalidateQueries({ queryKey: ["graphData"] });
      setEditingNote(null);
    },
  });

  // Chunk Update Mutation
  const updateChunkMutation = useMutation({
    mutationFn: (data: { docId: string; chunkId: string; text: string }) =>
      documentsApi.updateChunk(data.docId, data.chunkId, data.text),
    onSuccess: () => {
      refetchChunks();
      setEditingChunk(null);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  // Delete Document Mutation
  const deleteDocMutation = useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      queryClient.invalidateQueries({ queryKey: ["graphData"] });
      setInspectingDoc(null);
    },
  });

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {}
    clearAuth();
    router.push("/login");
  };

  const handleAskSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!askInput.trim()) return;
    askMutation.mutate(askInput.trim());
  };

  const handleSelectNoteForEdit = (n: Note) => {
    setEditingNote(n);
    setNoteTitle(n.title);
    setNoteContent(n.content);
    setNoteTagsInput((n.tags || []).join(", "));
  };

  const handleCreateNewNote = () => {
    const defaultTitle = "Untitled Note " + (notes.length + 1);
    setNoteTitle(defaultTitle);
    setNoteContent("# " + defaultTitle + "\n\nStart typing your note here... Use [[Doc Title]] for bi-directional linking.");
    setNoteTagsInput("draft, strategy");
    createNoteMutation.mutate({ title: defaultTitle, content: "# " + defaultTitle, tags: ["draft"] });
  };

  const handleSaveNote = () => {
    if (!editingNote) return;
    const tags = noteTagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    updateNoteMutation.mutate({
      id: editingNote.id,
      title: noteTitle,
      content: noteContent,
      tags,
    });
  };

  const handleTestConnector = async (type: string) => {
    setTestingConnector(type);
    try {
      const res = await connectorsApi.test(type);
      setTestResult({ type, res });
    } catch {
      setTestResult({
        type,
        res: { status: "error", healthy: false, latency_ms: 0, message: "Connection check failed" },
      });
    } finally {
      setTestingConnector(null);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadSuccess(null);
    try {
      const res = await documentsApi.uploadExcel(file);
      setUploadSuccess(res);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    } catch (err: any) {
      alert(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex flex-col font-sans selection:bg-indigo-600/30 selection:text-indigo-200">
      {/* ── TOP NAVIGATION BAR ────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-[#0D1322]/80 backdrop-blur-xl border-b border-white/10 px-6 py-3.5 flex items-center justify-between shadow-2xl">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab("dashboard")}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-cyan-500 to-violet-600 p-[1px] shadow-lg shadow-indigo-500/20">
              <div className="w-full h-full bg-[#0D1322] rounded-[11px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  Aivaura Context Store
                </span>
                <span className="px-2 py-0.5 text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full">
                  ENTERPRISE RAG
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">Company Intelligence Operating System</p>
            </div>
          </div>
        </div>

        {/* ── WORKSPACE TABS ───────────────────────────────────────────── */}
        <nav className="flex items-center bg-[#090D16]/80 p-1.5 rounded-xl border border-white/10 shadow-inner">
          <TabButton id="dashboard" active={activeTab} onClick={setActiveTab} icon={BarChart3} label="Dashboard" />
          <TabButton id="ask" active={activeTab} onClick={setActiveTab} icon={Sparkles} label="Ask Q&A Studio" />
          <TabButton id="graph" active={activeTab} onClick={setActiveTab} icon={Network} label="Knowledge Graph" />
          <TabButton id="notes" active={activeTab} onClick={setActiveTab} icon={BookOpen} label="Note Studio" />
          <TabButton id="connectors" active={activeTab} onClick={setActiveTab} icon={Plug} label="Connectors" />
          <TabButton id="admin" active={activeTab} onClick={setActiveTab} icon={Files} label="Documents & Audit" />
        </nav>

        {/* ── USER & SYSTEM STATUS ────────────────────────────────────── */}
        <div className="flex items-center gap-4">
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span>Qdrant Live</span>
          </div>

          <div className="flex items-center gap-3 border-l border-white/10 pl-4">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-semibold text-slate-200">{user?.email || "admin@aivaura.com"}</p>
              <p className="text-[10px] text-slate-400 uppercase tracking-wider">Administrator</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-xl bg-white/5 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-white/10 transition-all duration-150"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* ── MAIN WORKSPACE CONTENT AREA ────────────────────────────────── */}
      <main className="flex-1 max-w-[1700px] w-full mx-auto p-6 space-y-6">
        {/* ── TAB 1: EXECUTIVE DASHBOARD ───────────────────────────────── */}
        {activeTab === "dashboard" && (
          <div className="space-y-6 animate-fadeIn">
            {/* KPI Cards Banner */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <KpiCard
                title="Indexed Documents"
                value={stats?.total_documents ?? documents.length}
                subtext="Auto-synced across connectors"
                icon={Files}
                color="from-indigo-500 to-blue-600"
              />
              <KpiCard
                title="Qdrant Vector Embeddings"
                value={stats?.total_chunks ?? documents.reduce((acc, d) => acc + d.chunk_count, 0)}
                subtext="768-dim Nomics & Jina Vectors"
                icon={Database}
                color="from-cyan-500 to-teal-600"
              />
              <KpiCard
                title="Queries Executed"
                value={stats?.total_queries ?? queryHistory.length}
                subtext="Anti-hallucination RAG searches"
                icon={Sparkles}
                color="from-violet-500 to-purple-600"
              />
              <KpiCard
                title="Active Data Connectors"
                value={stats?.active_connectors ?? connectors.filter((c) => c.status === "connected").length}
                subtext="Live background synchronization"
                icon={Plug}
                color="from-emerald-500 to-teal-600"
              />
              <KpiCard
                title="Note Studio Knowledge Base"
                value={notes.length}
                subtext="Obsidian-style linked notes"
                icon={BookOpen}
                color="from-amber-500 to-orange-600"
              />
            </div>

            {/* Main Dashboard Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Quick Action Hero + Connectors Overview */}
              <div className="lg:col-span-2 space-y-6">
                {/* Hero Banner */}
                <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-900/60 via-slate-900 to-cyan-900/40 p-8 border border-white/10 shadow-2xl">
                  <div className="absolute -right-10 -bottom-10 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
                  <div className="relative z-10 space-y-4">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-semibold border border-indigo-500/30">
                      <Sparkles className="w-3.5 h-3.5" /> Company Intelligence Hub
                    </div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-white">
                      Ask anything about your company context.
                    </h1>
                    <p className="text-slate-300 max-w-xl text-sm leading-relaxed">
                      Instant, accurate, cited answers synthesized from Google Drive, Gmail, Outlook, Google Sheets, WhatsApp, and Note Studio markdown entries.
                    </p>
                    <div className="flex flex-wrap gap-3 pt-2">
                      <button
                        onClick={() => setActiveTab("ask")}
                        className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-cyan-500 text-white font-semibold text-sm shadow-lg shadow-indigo-500/25 hover:opacity-95 transition-all flex items-center gap-2"
                      >
                        <Sparkles className="w-4 h-4" /> Open Q&A Studio
                      </button>
                      <button
                        onClick={() => setActiveTab("graph")}
                        className="px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-slate-200 font-semibold text-sm border border-white/10 transition-all flex items-center gap-2"
                      >
                        <Network className="w-4 h-4" /> View Knowledge Graph
                      </button>
                      <button
                        onClick={() => setActiveTab("notes")}
                        className="px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-slate-200 font-semibold text-sm border border-white/10 transition-all flex items-center gap-2"
                      >
                        <BookOpen className="w-4 h-4" /> Open Note Studio
                      </button>
                    </div>
                  </div>
                </div>

                {/* Data Source Connectors Overview */}
                <div className="surface-card rounded-2xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                        <Plug className="w-5 h-5 text-indigo-400" /> Data Source Connectors Status
                      </h2>
                      <p className="text-xs text-slate-400">Automated background indexing status</p>
                    </div>
                    <button
                      onClick={() => setActiveTab("connectors")}
                      className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                    >
                      Manage All <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {["google_drive", "gmail", "sheets", "outlook", "whatsapp"].map((type) => {
                      const conn = connectors.find((c) => c.type === type);
                      const conf = SOURCE_CONFIG[type];
                      const isConnected = conn?.status === "connected";
                      return (
                        <div
                          key={type}
                          className="p-4 rounded-xl bg-[#090D16]/60 border border-white/5 flex items-center justify-between hover:border-white/15 transition-all"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`p-2.5 rounded-lg ${conf?.bg || "bg-indigo-500/10"}`}>
                              {conf?.icon ? <conf.icon className={`w-5 h-5 ${conf.color}`} /> : <Globe className="w-5 h-5 text-indigo-400" />}
                            </div>
                            <div>
                              <p className="text-sm font-semibold text-slate-200">{conf?.label || type}</p>
                              <p className="text-[11px] text-slate-400">
                                {conn ? `${conn.document_count} documents indexed` : "Not configured"}
                              </p>
                            </div>
                          </div>
                          <span
                            className={`px-2.5 py-1 text-[10px] font-bold rounded-full ${
                              isConnected
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                : "bg-slate-800 text-slate-400 border border-white/5"
                            }`}
                          >
                            {isConnected ? "Active" : "Offline"}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Right Column: Recent Queries & Activity Feed */}
              <div className="space-y-6">
                <div className="surface-card rounded-2xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                      <Clock className="w-5 h-5 text-cyan-400" /> Recent Query History
                    </h2>
                    <span className="text-xs text-slate-400">{queryHistory.length} total</span>
                  </div>

                  <div className="space-y-2.5 max-h-[420px] overflow-y-auto pr-1">
                    {queryHistory.length === 0 ? (
                      <p className="text-xs text-slate-500 italic py-6 text-center">No queries executed yet.</p>
                    ) : (
                      queryHistory.map((item) => (
                        <div
                          key={item.id}
                          onClick={() => {
                            setAskInput(item.query);
                            setActiveTab("ask");
                          }}
                          className="p-3 rounded-xl bg-[#090D16]/80 border border-white/5 hover:border-indigo-500/40 hover:bg-indigo-500/5 transition-all cursor-pointer space-y-1.5 group"
                        >
                          <p className="text-xs font-semibold text-slate-200 group-hover:text-indigo-300 line-clamp-1">
                            {item.query}
                          </p>
                          <p className="text-[11px] text-slate-400 line-clamp-2">{item.answer_preview}</p>
                          <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                            <span>{item.sources?.length || 0} citations</span>
                            <span>{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: ASK Q&A STUDIO ────────────────────────────────────── */}
        {activeTab === "ask" && (
          <div className="space-y-6 max-w-5xl mx-auto animate-fadeIn">
            {/* Header & Source Filter */}
            <div className="surface-card rounded-2xl p-6 space-y-4 border border-white/10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-6 h-6 text-cyan-400" /> Natural Language Q&A Studio
                  </h1>
                  <p className="text-xs text-slate-400">Strict anti-hallucination hybrid RAG answer synthesis</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-400">Source Scope:</span>
                  <select
                    value={selectedSource}
                    onChange={(e) => setSelectedSource(e.target.value)}
                    className="bg-[#090D16] border border-white/10 text-slate-200 text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="all">All Connected Sources</option>
                    <option value="google_drive">Google Drive</option>
                    <option value="gmail">Gmail Emails</option>
                    <option value="sheets">Sheets & Excel</option>
                    <option value="outlook">Outlook</option>
                    <option value="whatsapp">WhatsApp</option>
                    <option value="notes">Note Studio</option>
                  </select>
                </div>
              </div>

              {/* Preset Chips */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-white/5">
                <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                  <Zap className="w-3 h-3 text-amber-400" /> Presets:
                </span>
                {[
                  "What are our key financial strategy targets for Q3?",
                  "Summarize pricing proposals discussed in Gmail emails.",
                  "Extract meeting action items from Outlook messages.",
                  "What notes exist about engineering architecture?",
                ].map((preset, idx) => (
                  <button
                    key={idx}
                    onClick={() => setAskInput(preset)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-white/5 hover:bg-indigo-500/20 text-slate-300 hover:text-indigo-200 border border-white/10 transition-all"
                  >
                    {preset}
                  </button>
                ))}
              </div>

              {/* Question Input Form */}
              <form onSubmit={handleAskSubmit} className="relative mt-2">
                <input
                  type="text"
                  value={askInput}
                  onChange={(e) => setAskInput(e.target.value)}
                  placeholder="Ask a detailed question about company documents, emails, sheets, or notes..."
                  className="w-full pl-4 pr-32 py-4 bg-[#090D16] border border-white/15 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 shadow-inner"
                />
                <button
                  type="submit"
                  disabled={askMutation.isPending || !askInput.trim()}
                  className="absolute right-2 top-2 bottom-2 px-5 bg-gradient-to-r from-indigo-500 via-cyan-500 to-teal-500 text-white text-xs font-bold rounded-lg hover:opacity-95 transition-all disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-cyan-500/20"
                >
                  {askMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  Ask AI Engine
                </button>
              </form>
            </div>

            {/* Answer Display */}
            {activeResult && (
              <div className="surface-card rounded-2xl p-6 space-y-6 border border-cyan-500/30 shadow-2xl animate-fadeIn">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> High Confidence Answer
                    </span>
                    <span className="text-xs text-slate-400">Synthesized from {activeResult.sources?.length || 0} citations</span>
                  </div>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(activeResult.answer);
                      setCopiedAnswer(true);
                      setTimeout(() => setCopiedAnswer(false), 2000);
                    }}
                    className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 transition-all"
                  >
                    {copiedAnswer ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedAnswer ? "Copied" : "Copy Answer"}
                  </button>
                </div>

                <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                  {activeResult.answer}
                </div>

                {/* Sources / Citations */}
                {activeResult.sources && activeResult.sources.length > 0 && (
                  <div className="space-y-3 pt-4 border-t border-white/10">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                      <FileText className="w-4 h-4 text-cyan-400" /> Verified Sources & Citations
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {activeResult.sources.map((src, idx) => (
                        <div
                          key={idx}
                          onClick={() => setSelectedSourceDrawer(src)}
                          className="p-3 rounded-xl bg-[#090D16]/80 border border-white/10 hover:border-cyan-500/40 hover:bg-cyan-500/5 transition-all cursor-pointer space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                              Source [{src.index}]
                            </span>
                            <span className="text-[10px] text-slate-400">{src.source_type}</span>
                          </div>
                          <p className="text-xs font-semibold text-slate-200 line-clamp-1">{src.title}</p>
                          <p className="text-[11px] text-slate-400 line-clamp-2 italic">"{src.snippet}"</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: KNOWLEDGE GRAPH VISUALIZER ──────────────────────── */}
        {activeTab === "graph" && (
          <div className="space-y-6 animate-fadeIn">
            <div className="surface-card rounded-2xl p-6 space-y-4 border border-white/10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h1 className="text-xl font-bold text-white flex items-center gap-2">
                    <Network className="w-6 h-6 text-indigo-400" /> Obsidian / DSpace Interactive Knowledge Graph
                  </h1>
                  <p className="text-xs text-slate-400">Bi-directional links, tags, connectors, and semantic vector relationships</p>
                </div>
                {graphData?.stats && (
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="px-3 py-1 rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      Nodes: {graphData.stats.total_nodes}
                    </span>
                    <span className="px-3 py-1 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                      Edges: {graphData.stats.total_edges}
                    </span>
                    <span className="px-3 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                      Notes: {graphData.stats.notes}
                    </span>
                  </div>
                )}
              </div>

              {/* Canvas Graph Renderer */}
              <div className="relative w-full h-[600px] bg-[#060911] rounded-xl border border-white/10 overflow-hidden flex items-center justify-center">
                {graphLoading ? (
                  <div className="flex items-center gap-2 text-slate-400 text-sm">
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-400" /> Loading Knowledge Network Graph...
                  </div>
                ) : graphData && graphData.nodes.length > 0 ? (
                  <GraphCanvas
                    nodes={graphData.nodes}
                    edges={graphData.edges}
                    onSelectNode={setSelectedGraphNode}
                  />
                ) : (
                  <p className="text-slate-500 text-sm">No knowledge nodes available yet.</p>
                )}
              </div>
            </div>

            {/* Selected Node Details Drawer */}
            {selectedGraphNode && (
              <div className="surface-card rounded-2xl p-6 space-y-3 border border-indigo-500/30 animate-fadeIn">
                <div className="flex items-center justify-between">
                  <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full uppercase bg-indigo-500/20 text-indigo-300">
                    {selectedGraphNode.type} Node
                  </span>
                  <button onClick={() => setSelectedGraphNode(null)} className="text-slate-400 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <h3 className="text-lg font-bold text-white">{selectedGraphNode.label}</h3>
                <p className="text-xs text-slate-300">{selectedGraphNode.details}</p>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 4: NOTE STUDIO ───────────────────────────────────────── */}
        {activeTab === "notes" && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                  <BookOpen className="w-6 h-6 text-emerald-400" /> Note Studio & Knowledge Base
                </h1>
                <p className="text-xs text-slate-400">Obsidian-style markdown notes auto-indexed into RAG vectors</p>
              </div>
              <button
                onClick={handleCreateNewNote}
                className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-500/20 hover:opacity-95 transition-all flex items-center gap-2"
              >
                <Plus className="w-4 h-4" /> Create New Note
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Note Directory */}
              <div className="surface-card rounded-2xl p-4 space-y-3">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Your Markdown Notes</h3>
                <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
                  {notes.length === 0 ? (
                    <p className="text-xs text-slate-500 italic py-6 text-center">No notes created yet. Click above to create one!</p>
                  ) : (
                    notes.map((n) => (
                      <div
                        key={n.id}
                        onClick={() => handleSelectNoteForEdit(n)}
                        className={`p-3 rounded-xl border transition-all cursor-pointer space-y-1 ${
                          editingNote?.id === n.id
                            ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-200"
                            : "bg-[#090D16]/60 border-white/5 hover:border-white/15 text-slate-300"
                        }`}
                      >
                        <p className="text-xs font-bold line-clamp-1">{n.title}</p>
                        <p className="text-[11px] text-slate-400 line-clamp-2">{n.content}</p>
                        <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                          <span>{n.tags?.length ? `#${n.tags.join(" #")}` : "No tags"}</span>
                          <span>{new Date(n.updated_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Right Column: Note Editor */}
              <div className="lg:col-span-2 surface-card rounded-2xl p-6 space-y-4 border border-white/10">
                {editingNote ? (
                  <>
                    <div className="flex items-center justify-between border-b border-white/10 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        <span className="text-xs text-emerald-400 font-semibold">Live Auto-Indexing Active</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleSaveNote}
                          disabled={updateNoteMutation.isPending}
                          className="px-4 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 shadow-md shadow-emerald-500/20"
                        >
                          {updateNoteMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                          Save & Index
                        </button>
                        <button
                          onClick={() => deleteNoteMutation.mutate(editingNote.id)}
                          className="p-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 rounded-lg transition-all"
                          title="Delete Note"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <label className="text-[11px] font-semibold text-slate-400">Note Title</label>
                        <input
                          type="text"
                          value={noteTitle}
                          onChange={(e) => setNoteTitle(e.target.value)}
                          className="w-full bg-[#090D16] border border-white/15 rounded-xl px-4 py-2.5 text-sm font-bold text-white focus:outline-none focus:border-emerald-500"
                        />
                      </div>

                      <div>
                        <label className="text-[11px] font-semibold text-slate-400">Tags (comma separated)</label>
                        <input
                          type="text"
                          value={noteTagsInput}
                          onChange={(e) => setNoteTagsInput(e.target.value)}
                          placeholder="e.g. strategy, architecture, q3"
                          className="w-full bg-[#090D16] border border-white/15 rounded-xl px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                        />
                      </div>

                      <div>
                        <label className="text-[11px] font-semibold text-slate-400">Markdown Content (Use [[Link Title]] to link)</label>
                        <textarea
                          rows={14}
                          value={noteContent}
                          onChange={(e) => setNoteContent(e.target.value)}
                          className="w-full bg-[#090D16] border border-white/15 rounded-xl p-4 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500 leading-relaxed"
                        />
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-20 space-y-3">
                    <BookOpen className="w-12 h-12 text-slate-600 mx-auto" />
                    <p className="text-slate-400 text-sm font-medium">Select a note from the directory or create a new one to edit.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 5: CONNECTORS COMMAND CENTER ─────────────────────────── */}
        {activeTab === "connectors" && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <Plug className="w-6 h-6 text-indigo-400" /> Connectors Command Center
              </h1>
              <p className="text-xs text-slate-400 font-medium">Configure live data integrations and inspect execution diagnostics</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {["google_drive", "gmail", "sheets", "outlook", "whatsapp"].map((type) => {
                const conn = connectors.find((c) => c.type === type);
                const conf = SOURCE_CONFIG[type];
                const isConnected = conn?.status === "connected";

                return (
                  <div key={type} className="surface-card rounded-2xl p-6 space-y-4 border border-white/10 flex flex-col justify-between">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className={`p-3 rounded-xl ${conf?.bg || "bg-indigo-500/10"}`}>
                          {conf?.icon ? <conf.icon className={`w-6 h-6 ${conf.color}`} /> : <Globe className="w-6 h-6 text-indigo-400" />}
                        </div>
                        <span
                          className={`px-3 py-1 text-xs font-bold rounded-full ${
                            isConnected
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : "bg-slate-800 text-slate-400 border border-white/10"
                          }`}
                        >
                          {isConnected ? "Connected" : "Disconnected"}
                        </span>
                      </div>

                      <div>
                        <h3 className="text-lg font-bold text-white">{conf?.label || type}</h3>
                        <p className="text-xs text-slate-400">
                          {conn ? `${conn.document_count} documents indexed` : "Ready to connect"}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2 pt-4 border-t border-white/10">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleTestConnector(type)}
                          disabled={testingConnector === type}
                          className="flex-1 px-3 py-2 bg-white/5 hover:bg-white/10 text-slate-200 text-xs font-semibold rounded-xl border border-white/10 transition-all flex items-center justify-center gap-1.5"
                        >
                          {testingConnector === type ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5 text-cyan-400" />}
                          Ping Test
                        </button>
                        <button
                          onClick={() => setViewingLogsType(type)}
                          className="px-3 py-2 bg-white/5 hover:bg-white/10 text-slate-200 text-xs font-semibold rounded-xl border border-white/10 transition-all flex items-center justify-center gap-1.5"
                        >
                          <Terminal className="w-3.5 h-3.5 text-indigo-400" /> Logs
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Test Diagnostic Result Popup */}
            {testResult && (
              <div className="surface-card rounded-2xl p-4 border border-cyan-500/40 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <div>
                    <p className="text-xs font-bold text-white uppercase">Diagnostic Test: {testResult.type}</p>
                    <p className="text-xs text-slate-300">{testResult.res.message} (Latency: {testResult.res.latency_ms}ms)</p>
                  </div>
                </div>
                <button onClick={() => setTestResult(null)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 6: DOCUMENTS & CHUNK INSPECTOR ───────────────────────── */}
        {activeTab === "admin" && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                  <Files className="w-6 h-6 text-cyan-400" /> Document & Chunk Management Console
                </h1>
                <p className="text-xs text-slate-400">Inspect, edit, re-embed, or delete indexed chunks</p>
              </div>

              {/* Upload Excel Button */}
              <label className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg cursor-pointer transition-all flex items-center gap-2">
                <UploadCloud className="w-4 h-4" /> Upload Excel / CSV
                <input type="file" onChange={handleFileUpload} accept=".xlsx,.xls,.csv" className="hidden" />
              </label>
            </div>

            {/* Documents Table */}
            <div className="surface-card rounded-2xl overflow-hidden border border-white/10">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#0D1322] text-[11px] font-bold text-slate-400 uppercase border-b border-white/10">
                    <th className="p-4">Title / Source ID</th>
                    <th className="p-4">Author</th>
                    <th className="p-4">Chunks</th>
                    <th className="p-4">Indexed Date</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-xs text-slate-200">
                  {documents.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-10 text-slate-500 italic">No documents indexed yet.</td>
                    </tr>
                  ) : (
                    documents.map((d) => (
                      <tr key={d.id} className="hover:bg-white/5 transition-all">
                        <td className="p-4 font-semibold text-white">{d.title || d.source_id}</td>
                        <td className="p-4 text-slate-400">{d.author || "System"}</td>
                        <td className="p-4">
                          <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold text-[10px]">
                            {d.chunk_count} chunks
                          </span>
                        </td>
                        <td className="p-4 text-slate-400">
                          {d.indexed_at ? new Date(d.indexed_at).toLocaleDateString() : "N/A"}
                        </td>
                        <td className="p-4 text-right space-x-2">
                          <button
                            onClick={() => setInspectingDoc(d)}
                            className="px-3 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 font-semibold text-[11px] transition-all"
                          >
                            Inspect Chunks
                          </button>
                          <button
                            onClick={() => deleteDocMutation.mutate(d.id)}
                            className="p-1 rounded-lg bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 transition-all"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Chunk Inspector Drawer */}
            {inspectingDoc && (
              <div className="surface-card rounded-2xl p-6 space-y-4 border border-cyan-500/40 animate-fadeIn">
                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                  <div>
                    <h3 className="text-lg font-bold text-white">Chunk Inspector: {inspectingDoc.title}</h3>
                    <p className="text-xs text-slate-400">View and edit individual chunks for live vector re-embedding</p>
                  </div>
                  <button onClick={() => setInspectingDoc(null)} className="text-slate-400 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                  {chunks.map((c) => (
                    <div key={c.id} className="p-4 rounded-xl bg-[#090D16] border border-white/10 space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span className="font-bold text-indigo-400">Chunk #{c.chunk_index}</span>
                        <span>Qdrant ID: {c.qdrant_id || "Pending"}</span>
                      </div>
                      <p className="text-xs text-slate-200 font-mono leading-relaxed">{c.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function TabButton({ id, active, onClick, icon: Icon, label }: { id: WorkspaceTab; active: WorkspaceTab; onClick: (id: WorkspaceTab) => void; icon: any; label: string }) {
  const isSelected = active === id;
  return (
    <button
      onClick={() => onClick(id)}
      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all duration-150 flex items-center gap-2 ${
        isSelected
          ? "bg-gradient-to-r from-indigo-500 to-cyan-500 text-white shadow-md shadow-indigo-500/20"
          : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
      }`}
    >
      <Icon className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}

function KpiCard({ title, value, subtext, icon: Icon, color }: { title: string; value: number | string; subtext: string; icon: any; color: string }) {
  return (
    <div className="surface-card rounded-2xl p-5 border border-white/10 relative overflow-hidden space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400">{title}</span>
        <div className={`p-2 rounded-xl bg-gradient-to-br ${color} text-white shadow-md`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-2xl font-black text-white tracking-tight">{value}</p>
      <p className="text-[10px] text-slate-400 font-medium">{subtext}</p>
    </div>
  );
}

function GraphCanvas({ nodes, edges, onSelectNode }: { nodes: GraphNode[]; edges: any[]; onSelectNode: (n: GraphNode) => void }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;

    // Assign initial positions
    const width = canvas.width;
    const height = canvas.height;
    const posMap: Record<string, { x: number; y: number; vx: number; vy: number }> = {};

    nodes.forEach((n, idx) => {
      const angle = (idx / nodes.length) * 2 * Math.PI;
      const radius = 150 + Math.random() * 80;
      posMap[n.id] = {
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
      };
    });

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw Edges
      ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
      ctx.lineWidth = 1;
      edges.forEach((e) => {
        const sourcePos = posMap[e.source];
        const targetPos = posMap[e.target];
        if (sourcePos && targetPos) {
          ctx.beginPath();
          ctx.moveTo(sourcePos.x, sourcePos.y);
          ctx.lineTo(targetPos.x, targetPos.y);
          ctx.stroke();
        }
      });

      // Draw Nodes
      nodes.forEach((n) => {
        const pos = posMap[n.id];
        if (!pos) return;

        ctx.beginPath();
        ctx.arc(pos.x, pos.y, n.val / 2.5, 0, 2 * Math.PI);
        ctx.fillStyle = n.color || "#6366f1";
        ctx.shadowColor = n.color || "#6366f1";
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#e2e8f0";
        ctx.font = "10px sans-serif";
        ctx.fillText(n.label.slice(0, 18), pos.x + 10, pos.y + 3);
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animationFrameId);
  }, [nodes, edges]);

  return <canvas ref={canvasRef} width={1000} height={580} className="w-full h-full cursor-pointer" />;
}
