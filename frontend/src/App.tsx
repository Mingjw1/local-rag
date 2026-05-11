import { useState, useEffect, useCallback, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { api, isLoggedIn, logout, KB, Document, UserInfo } from "./api";
import { AIPanel } from "./AIPanel";
import { SearchPage } from "./SearchPage";
import {
  Book,
  Search,
  Home,
  Layers,
  Sparkles,
  Clock,
  Star,
  Trash2,
  Plus,
  FileText,
  Zap,
  Import,
  UploadCloud,
  MessageSquare,
  PlusCircle,
  Folder,
  ChevronDown,
  Filter,
  ArrowUpDown,
  MoreHorizontal,
  Settings,
  Share2,
  Upload,
  File,
  Loader,
  CheckCircle2,
  AlertCircle,
  LogOut,
  User,
} from "lucide-react";

type NavItem = "home" | "documents" | "recent" | "favorites" | "trash" | "search";

// ===== Login Page =====
function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.login(username, password);
      window.location.reload();
    } catch (err: any) {
      setError(err.message || "登录失败");
    }
    setLoading(false);
  };

  return (
    <div className="h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-indigo-50">
      <div className="w-full max-w-sm mx-auto p-8">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Book className="w-8 h-8 text-indigo-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">AI 知识库</h1>
          <p className="text-sm text-gray-500 mt-1">请登录以继续</p>
        </div>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="用户名"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 transition-all"
              disabled={loading}
              autoFocus
            />
          </div>
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="密码"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 transition-all"
              disabled={loading}
            />
          </div>
          {error && (
            <div className="text-red-500 text-xs font-medium bg-red-50 px-3 py-2 rounded-lg">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !username || !password}
            className="w-full py-3 bg-indigo-600 text-white rounded-xl font-semibold text-sm hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-indigo-200"
          >
            {loading ? "登录中..." : "登录"}
          </button>
        </form>
        <p className="text-xs text-gray-400 text-center mt-6">
          默认管理员: admin / admin123
        </p>
      </div>
    </div>
  );
}

function App() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [kbs, setKbs] = useState<KB[]>([]);
  const [activeKB, setActiveKB] = useState<string | null>(null);
  const [nav, setNav] = useState<NavItem>("home");
  const [loading, setLoading] = useState(true);
  const [showNewDropdown, setShowNewDropdown] = useState(false);
  const [showKbDropdown, setShowKbDropdown] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const kbDropdownRef = useRef<HTMLDivElement>(null);

  // Check auth + load KBs
  useEffect(() => {
    if (!isLoggedIn()) {
      setLoading(false);
      return;
    }
    api.getMe().then((u) => {
      setUser(u);
      return api.listKBs();
    }).then((list) => {
      setKbs(list);
      if (list.length > 0) setActiveKB(list[0].id);
    }).catch(() => {
      logout();
    }).finally(() => {
      setLoading(false);
    });
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node))
        setShowNewDropdown(false);
      if (kbDropdownRef.current && !kbDropdownRef.current.contains(e.target as Node))
        setShowKbDropdown(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleCreateKB = async () => {
    const name = prompt("知识库名称：");
    if (!name) return;
    const kb = await api.createKB(name, "");
    setKbs((prev) => [...prev, kb]);
    setActiveKB(kb.id);
  };

  const handleDeleteKB = async () => {
    if (!activeKB) return;
    if (!confirm("确认删除此知识库？")) return;
    await api.deleteKB(activeKB);
    setKbs((prev) => prev.filter((kb) => kb.id !== activeKB));
    setActiveKB(kbs.find((kb) => kb.id !== activeKB)?.id ?? null);
  };

  const activeKbData = kbs.find((kb) => kb.id === activeKB);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#F7F8FA]">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader className="w-5 h-5 animate-spin" />
          <span className="text-sm font-medium">加载中...</span>
        </div>
      </div>
    );
  }

  if (!isLoggedIn()) {
    return <LoginPage />;
  }

  return (
    <div className="h-screen overflow-hidden flex bg-[#F7F8FA]">
      {/* ============ LEFT SIDEBAR ============ */}
      <aside className="w-[240px] h-full border-r border-gray-200 bg-white flex flex-col shrink-0 z-30">
        {/* Workspace */}
        <div className="p-4 flex items-center gap-2">
          <div className="w-6 h-6 bg-emerald-100 rounded flex items-center justify-center text-emerald-600">
            <Folder className="w-4 h-4" />
          </div>
          <span className="text-xs font-medium text-gray-500">个人知识库</span>
        </div>

        {/* KB Selector */}
        <div className="px-4 mb-4 relative" ref={kbDropdownRef}>
          <button
            onClick={() => setShowKbDropdown(!showKbDropdown)}
            className="w-full flex items-center justify-between p-2 rounded-xl hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-100 group"
          >
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white shrink-0">
                <Book className="w-5 h-5" />
              </div>
              <span className="font-semibold text-gray-800 text-sm truncate">
                {activeKbData?.name ?? "选择知识库"}
              </span>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-400 group-hover:text-gray-600 shrink-0" />
          </button>

          {showKbDropdown && (
            <div className="absolute left-4 right-4 top-full mt-1 bg-white rounded-2xl shadow-2xl border border-gray-100 z-50 p-2 dropdown-animate">
              <div className="space-y-1 max-h-[200px] overflow-y-auto custom-scrollbar">
                {kbs.map((kb) => (
                  <button
                    key={kb.id}
                    onClick={() => {
                      setActiveKB(kb.id);
                      setShowKbDropdown(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-3 ${
                      activeKB === kb.id
                        ? "bg-indigo-50 text-indigo-600"
                        : "hover:bg-gray-50 text-gray-700"
                    }`}
                  >
                    <Book className="w-4 h-4" />
                    <span className="truncate flex-1">{kb.name}</span>
                    <span className="text-[10px] text-gray-400 font-mono">
                      {kb.document_count}
                    </span>
                  </button>
                ))}
              </div>
              {activeKB && (
                <>
                  <hr className="my-1 border-gray-100" />
                  <button
                    onClick={handleDeleteKB}
                    className="w-full text-left px-3 py-2 rounded-lg text-sm text-red-500 hover:bg-red-50 flex items-center gap-3"
                  >
                    <Trash2 className="w-4 h-4" />
                    删除当前知识库
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* Search */}
        <div className="px-4 mb-5">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 group-focus-within:text-blue-500 transition-colors pointer-events-none" />
            <input
              type="text"
              placeholder="搜索知识库..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setNav("search")}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setNav("search");
                }
              }}
              className="w-full bg-gray-50 border border-gray-100 rounded-xl py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:bg-white transition-all"
            />
          </div>
        </div>

        {/* Navigation */}
        <nav className="px-2 space-y-0.5 flex-1 overflow-y-auto custom-scrollbar">
          {[
            { id: "home" as NavItem, icon: Home, label: "首页" },
            { id: "search" as NavItem, icon: Search, label: "搜索" },
            { id: "documents" as NavItem, icon: Layers, label: "文档" },
            { id: "recent" as NavItem, icon: Clock, label: "最近访问" },
            { id: "favorites" as NavItem, icon: Star, label: "收藏" },
            { id: "trash" as NavItem, icon: Trash2, label: "回收站" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setNav(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                nav === item.id
                  ? "sidebar-item-active bg-indigo-50 text-indigo-600"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </nav>

        {/* New Button */}
        <div className="p-4 border-t border-gray-100 relative" ref={dropdownRef}>
          <button
            onClick={() => setShowNewDropdown(!showNewDropdown)}
            className="w-full gradient-btn-green text-white py-2.5 rounded-xl flex items-center justify-center gap-2 font-semibold text-sm shadow-sm"
          >
            <Plus className="w-4 h-4" /> 新建
          </button>

          {showNewDropdown && (
            <div className="absolute bottom-full left-4 right-4 mb-2 bg-white rounded-2xl shadow-2xl border border-gray-100 z-50 p-2 dropdown-animate">
              <div className="space-y-1">
                <button
                  onClick={() => {
                    setShowNewDropdown(false);
                    handleCreateKB();
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-50 rounded-lg text-sm flex items-center gap-3"
                >
                  <Folder className="w-4 h-4 text-gray-400" />
                  知识库
                </button>
                <button
                  onClick={() => {
                    setShowNewDropdown(false);
                    setNav("documents");
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-50 rounded-lg text-sm flex items-center gap-3"
                >
                  <Upload className="w-4 h-4 text-gray-400" />
                  上传文档
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User Area */}
        <div className="p-4 bg-gray-50/50 flex items-center gap-3 border-t border-gray-100">
          <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 shrink-0 border-2 border-white shadow-sm">
            <User className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-800 truncate">
              {user?.display_name || user?.username || "User"}
            </p>
            <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
              {user?.role || "viewer"}
            </p>
          </div>
          <button
            onClick={logout}
            className="text-gray-400 hover:text-red-500 p-1 rounded-lg hover:bg-red-50 transition-all"
            title="登出"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* ============ MAIN CONTENT ============ */}
      <main className="flex-1 h-full overflow-y-auto custom-scrollbar flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 border-b border-gray-200 bg-white/80 backdrop-blur-md sticky top-0 z-20 px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4 min-w-0">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white shadow-sm shrink-0">
              <Book className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-base font-bold text-gray-900 leading-tight truncate">
                {activeKbData?.name ?? "知识库"}
              </h1>
              <p className="text-[11px] text-gray-400 font-medium">
                {activeKbData
                  ? `${activeKbData.document_count} 文档 · ${activeKbData.chunk_count} 片段`
                  : "请创建或选择一个知识库"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2 text-gray-400 hover:bg-gray-100 rounded-xl transition-colors">
              <Star className="w-5 h-5" />
            </button>
            <button className="p-2 text-gray-400 hover:bg-gray-100 rounded-xl transition-colors">
              <Share2 className="w-5 h-5" />
            </button>
            {activeKB && (
              <button className="gradient-ai-btn text-white px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 shadow-sm hover:opacity-90 transition-opacity">
                <Sparkles className="w-4 h-4" /> AI 总结
              </button>
            )}
            <button className="p-2 text-gray-400 hover:bg-gray-100 rounded-xl transition-colors">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
        </header>

        <div className="max-w-5xl w-full mx-auto p-8 lg:p-12 space-y-10">
          {!activeKB ? (
            /* Empty State */
            <div className="text-center py-20">
              <Book className="w-16 h-16 text-gray-200 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-400 mb-2">
                暂无知识库
              </h2>
              <p className="text-gray-300 mb-6">
                点击左侧「新建」按钮创建第一个知识库
              </p>
              <button
                onClick={handleCreateKB}
                className="gradient-btn-green text-white px-6 py-3 rounded-xl font-semibold text-sm inline-flex items-center gap-2"
              >
                <Plus className="w-4 h-4" /> 创建知识库
              </button>
            </div>
          ) : nav === "home" ? (
            /* ===== HOME ===== */
            <>
              {/* Welcome Hero */}
              <section className="relative bg-white rounded-[32px] p-10 border border-gray-100 shadow-xl shadow-gray-200/50 overflow-hidden flex flex-col md:flex-row items-center gap-10">
                <div className="flex-1 relative z-10 text-center md:text-left">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-600 text-xs font-bold mb-5">
                    <Sparkles className="w-3.5 h-3.5" /> AI Native Experience
                  </div>
                  <h2 className="text-3xl font-extrabold text-gray-900 mb-3 tracking-tight">
                    欢迎来到 AI 知识库
                  </h2>
                  <p className="text-gray-500 text-base leading-relaxed max-w-md">
                    知识库像一本持续生长的智能书籍，帮助团队沉淀知识、连接文档、增强搜索与
                    AI 问答能力。
                  </p>
                </div>

                {/* Knowledge Graph SVG */}
                <div className="w-full md:w-72 h-48 relative shrink-0">
                  <svg className="w-full h-full" viewBox="0 0 200 150">
                    <defs>
                      <linearGradient
                        id="graphGrad"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="100%"
                      >
                        <stop
                          offset="0%"
                          style={{ stopColor: "#6366F1", stopOpacity: 0.2 }}
                        />
                        <stop
                          offset="100%"
                          style={{ stopColor: "#10B981", stopOpacity: 0.2 }}
                        />
                      </linearGradient>
                    </defs>
                    <circle
                      cx="100"
                      cy="75"
                      r="40"
                      fill="url(#graphGrad)"
                      className="knowledge-graph-node"
                    />
                    <circle
                      cx="40"
                      cy="40"
                      r="8"
                      fill="#10B981"
                      className="knowledge-graph-node"
                      style={{ animationDelay: "0.5s" }}
                    />
                    <circle
                      cx="160"
                      cy="50"
                      r="10"
                      fill="#6366F1"
                      className="knowledge-graph-node"
                      style={{ animationDelay: "1.2s" }}
                    />
                    <circle
                      cx="150"
                      cy="110"
                      r="6"
                      fill="#F59E0B"
                      className="knowledge-graph-node"
                      style={{ animationDelay: "0.8s" }}
                    />
                    <circle
                      cx="50"
                      cy="120"
                      r="9"
                      fill="#EC4899"
                      className="knowledge-graph-node"
                      style={{ animationDelay: "1.5s" }}
                    />
                    <line
                      x1="100"
                      y1="75"
                      x2="40"
                      y2="40"
                      stroke="#E5E7EB"
                      strokeWidth="1.5"
                      strokeDasharray="4"
                    />
                    <line
                      x1="100"
                      y1="75"
                      x2="160"
                      y2="50"
                      stroke="#E5E7EB"
                      strokeWidth="1.5"
                      strokeDasharray="4"
                    />
                    <line
                      x1="100"
                      y1="75"
                      x2="150"
                      y2="110"
                      stroke="#E5E7EB"
                      strokeWidth="1.5"
                      strokeDasharray="4"
                    />
                    <line
                      x1="100"
                      y1="75"
                      x2="50"
                      y2="120"
                      stroke="#E5E7EB"
                      strokeWidth="1.5"
                      strokeDasharray="4"
                    />
                  </svg>
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 bg-white rounded-2xl shadow-lg border border-indigo-100 flex items-center justify-center text-indigo-600">
                    <Sparkles className="w-6 h-6" />
                  </div>
                </div>
              </section>

              {/* Quick Actions */}
              <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-6 rounded-[24px] border border-gray-100 shadow-sm hover:shadow-xl hover:-translate-y-0.5 transition-all cursor-pointer group">
                  <div className="w-12 h-12 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 mb-4 group-hover:scale-110 transition-transform">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-gray-900 mb-1 text-sm">
                    上传文档
                  </h3>
                  <p className="text-xs text-gray-400">
                    PDF, Markdown, Word...
                  </p>
                </div>
                <div className="bg-white p-6 rounded-[24px] border border-gray-100 shadow-sm hover:shadow-xl hover:-translate-y-0.5 transition-all cursor-pointer group">
                  <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 mb-4 group-hover:scale-110 transition-transform">
                    <PlusCircle className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-gray-900 mb-1 text-sm">
                    创建 AI Wiki
                  </h3>
                  <p className="text-xs text-gray-400">
                    结构化 AI 协作文档
                  </p>
                </div>
                <div className="bg-white p-6 rounded-[24px] border border-gray-100 shadow-sm hover:shadow-xl hover:-translate-y-0.5 transition-all cursor-pointer group">
                  <div className="w-12 h-12 bg-amber-50 rounded-2xl flex items-center justify-center text-amber-600 mb-4 group-hover:scale-110 transition-transform">
                    <MessageSquare className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-gray-900 mb-1 text-sm">
                    AI 问答
                  </h3>
                  <p className="text-xs text-gray-400">
                    基于知识库极速提问
                  </p>
                </div>
                <div className="bg-white p-6 rounded-[24px] border border-gray-100 shadow-sm hover:shadow-xl hover:-translate-y-0.5 transition-all cursor-pointer group">
                  <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center text-blue-600 mb-4 group-hover:scale-110 transition-transform">
                    <Import className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-gray-900 mb-1 text-sm">
                    导入外部同步
                  </h3>
                  <p className="text-xs text-gray-400">
                    飞书 / Notion / GitHub
                  </p>
                </div>
              </section>

              {/* Document List */}
              <ActiveDocumentTable kbId={activeKB} />
            </>
          ) : nav === "search" ? (
            <SearchPage kbId={activeKB} initialQuery={searchQuery} />
          ) : nav === "documents" ? (
            /* ===== DOCUMENTS ===== */
            <ActiveDocumentTable kbId={activeKB} />
          ) : (
            /* ===== OTHER NAVS (placeholders) ===== */
            <div className="text-center py-20">
              {nav === "recent" ? (
                <Clock className="w-16 h-16 text-gray-200 mx-auto mb-4" />
              ) : nav === "favorites" ? (
                <Star className="w-16 h-16 text-gray-200 mx-auto mb-4" />
              ) : (
                <Trash2 className="w-16 h-16 text-gray-200 mx-auto mb-4" />
              )}
              <h2 className="text-xl font-bold text-gray-300 mb-1">
                {nav === "recent"
                  ? "最近访问"
                  : nav === "favorites"
                  ? "收藏"
                  : "回收站"}
              </h2>
              <p className="text-sm text-gray-300">功能开发中...</p>
            </div>
          )}
        </div>
      </main>

      {/* ============ RIGHT AI PANEL ============ */}
      <AIPanel kbId={activeKB} />
    </div>
  );
}

// ============ Document Table Component ============

const fileIcons: Record<string, { bg: string; color: string; icon: any }> = {
  md: { bg: "bg-blue-50", color: "text-blue-500", icon: FileText },
  pdf: { bg: "bg-red-50", color: "text-red-500", icon: File },
  docx: { bg: "bg-purple-50", color: "text-purple-500", icon: FileText },
  txt: { bg: "bg-gray-50", color: "text-gray-500", icon: FileText },
};

function getFileType(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (ext in fileIcons) return ext;
  return "md";
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "刚刚";
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;
  return d.toLocaleDateString();
}

function ActiveDocumentTable({ kbId }: { kbId: string }) {
  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listDocuments(kbId);
      setDocs(list);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }, [kbId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    try {
      await api.uploadDocument(kbId, file, file.name);
      load();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("确认删除？")) return;
    await api.deleteDocument(kbId, docId);
    load();
  };

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          文档库
          <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            {docs.length}
          </span>
        </h3>
        <div className="flex items-center gap-2">
          <button className="text-xs font-semibold text-gray-500 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> 筛选
          </button>
          <button className="text-xs font-semibold text-gray-500 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-1">
            <ArrowUpDown className="w-3.5 h-3.5" /> 排序
          </button>
          <label className="text-xs font-semibold text-white px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 transition-colors flex items-center gap-1 cursor-pointer">
            <Upload className="w-3.5 h-3.5" /> 上传
            <input
              type="file"
              ref={fileRef}
              onChange={handleUpload}
              className="hidden"
            />
          </label>
        </div>
      </div>

      <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader className="w-5 h-5 text-gray-300 animate-spin" />
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center py-16">
            <FileText className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-400 font-medium">暂无文档</p>
            <p className="text-xs text-gray-300 mt-1">
              点击上方「上传」按钮添加文档
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-50 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
                  <th className="px-6 py-4">文件名</th>
                  <th className="px-6 py-4">更新时间</th>
                  <th className="px-6 py-4 text-center">
                    分块 (Chunks)
                  </th>
                  <th className="px-6 py-4">状态</th>
                  <th className="px-6 py-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {docs.map((doc) => {
                  const ftype = getFileType(doc.title);
                  const icon = fileIcons[ftype] ?? fileIcons["md"];
                  const IconComp = icon.icon;
                  return (
                    <tr
                      key={doc.id}
                      className="group hover:bg-gray-50/50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-9 h-9 ${icon.bg} ${icon.color} rounded-lg flex items-center justify-center`}
                          >
                            <IconComp className="w-5 h-5" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-gray-900 truncate max-w-[200px]">
                              {doc.title}
                            </p>
                            <p className="text-[11px] text-gray-400">
                              {doc.content_type}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {formatTime(doc.updated_at ?? doc.created_at)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="text-sm font-mono text-gray-600 bg-gray-50 px-2 py-0.5 rounded">
                          {doc.chunk_count}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {doc.status === "ready" ? (
                          <div className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                            <span className="text-xs font-semibold text-emerald-600">
                              已向量化
                            </span>
                          </div>
                        ) : doc.status === "failed" ? (
                          <div className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full bg-red-500"></div>
                            <span className="text-xs font-semibold text-red-600">
                              失败
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></div>
                            <span className="text-xs font-semibold text-amber-600">
                              同步中
                            </span>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="text-gray-400 hover:text-red-500 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

export default App;
