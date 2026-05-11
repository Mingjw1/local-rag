import { useState, useRef, useEffect } from "react";
import { api, SearchResult } from "./api";
import {
  Search,
  ArrowUp,
  FileText,
  File,
  BookOpen,
  Clock,
  SlidersHorizontal,
  X,
  Loader,
  Sparkles,
} from "lucide-react";

interface SearchPageProps {
  kbId: string | null;
  initialQuery?: string;
}

const fileIcons: Record<string, { bg: string; color: string }> = {
  md: { bg: "bg-blue-50", color: "text-blue-500" },
  pdf: { bg: "bg-red-50", color: "text-red-500" },
  docx: { bg: "bg-purple-50", color: "text-purple-500" },
  txt: { bg: "bg-gray-50", color: "text-gray-500" },
};

function getFileType(title: string): string {
  const ext = title.split(".").pop()?.toLowerCase() ?? "";
  if (ext in fileIcons) return ext;
  return "md";
}

function ResultCard({ result, rank }: { result: SearchResult; rank: number }) {
  const ftype = getFileType(result.document_title);
  const icon = fileIcons[ftype] ?? fileIcons["md"];
  const scorePct = Math.round(result.score * 100);

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 hover:border-indigo-200 hover:shadow-md transition-all">
      <div className="flex items-start gap-4">
        {/* Rank badge */}
        <div className="w-8 h-8 bg-indigo-50 text-indigo-500 rounded-xl flex items-center justify-center shrink-0 mt-0.5">
          <span className="text-xs font-bold">{rank}</span>
        </div>

        <div className="flex-1 min-w-0">
          {/* Title row */}
          <div className="flex items-center gap-2 mb-1.5">
            <div className={`w-6 h-6 ${icon.bg} ${icon.color} rounded-md flex items-center justify-center shrink-0`}>
              <FileText className="w-3.5 h-3.5" />
            </div>
            <span className="text-sm font-semibold text-gray-900 truncate">
              {result.document_title}
            </span>
          </div>

          {/* Content excerpt */}
          <p className="text-sm text-gray-600 leading-relaxed line-clamp-3 mb-3">
            {result.content}
          </p>

          {/* Meta row */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Score bar */}
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <span className="font-medium">相关度</span>
              <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full transition-all"
                  style={{ width: `${scorePct}%` }}
                />
              </div>
              <span className="font-mono text-indigo-600 font-bold">
                {result.score.toFixed(3)}
              </span>
            </div>

            {result.chunk_index != null && (
              <span className="text-xs text-gray-400 font-mono flex items-center gap-1">
                <BookOpen className="w-3 h-3" />
                chunk #{result.chunk_index}
              </span>
            )}

            {result.updated_at && (
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                更新于 {new Date(result.updated_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function SearchPage({ kbId, initialQuery }: SearchPageProps) {
  const [query, setQuery] = useState(initialQuery || "");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [queryTime, setQueryTime] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [hybrid, setHybrid] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on mount
  useEffect(() => {
    if (!initialQuery) {
      inputRef.current?.focus();
    }
  }, [initialQuery]);

  const handleSearch = async () => {
    if (!query.trim() || !kbId) return;
    setLoading(true);
    setSearched(true);
    try {
      const resp = await api.search(kbId, query, 10);
      setResults(resp.results);
      setTotal(resp.total);
      setQueryTime(resp.query_time_ms);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-extrabold text-gray-900 flex items-center gap-3">
          <Search className="w-6 h-6 text-indigo-500" />
          知识库搜索
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          混合搜索 — 语义向量 + 关键词全文检索
        </p>
      </div>

      {/* Search bar */}
      <div className="relative group">
        <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-indigo-500 transition-colors pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            kbId ? "搜索知识库中的文档..." : "请先选择知识库"
          }
          disabled={!kbId}
          className="w-full bg-white border border-gray-200 rounded-2xl py-4 pl-14 pr-32 text-base focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 transition-all shadow-sm disabled:opacity-50"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-xl transition-colors ${
              showFilters
                ? "bg-indigo-50 text-indigo-600"
                : "text-gray-400 hover:bg-gray-100"
            }`}
            title="搜索选项"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>
          <button
            onClick={handleSearch}
            disabled={!kbId || loading || !query.trim()}
            className="w-9 h-9 bg-indigo-600 text-white rounded-xl flex items-center justify-center hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <Loader className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowUp className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Filter options */}
      {showFilters && (
        <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm space-y-3">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
            搜索模式
          </h4>
          <label className="flex items-center gap-3 cursor-pointer">
            <div className="relative">
              <input
                type="checkbox"
                checked={hybrid}
                onChange={() => setHybrid(!hybrid)}
                className="sr-only"
              />
              <div
                className={`w-10 h-5 rounded-full transition-colors ${
                  hybrid ? "bg-indigo-600" : "bg-gray-200"
                }`}
              >
                <div
                  className={`w-4 h-4 bg-white rounded-full shadow-sm transition-transform mt-0.5 ${
                    hybrid ? "translate-x-5 ml-0.5" : "translate-x-0.5"
                  }`}
                />
              </div>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-800">
                混合搜索
              </span>
              <p className="text-xs text-gray-400">
                同时使用语义向量和关键词全文检索，通过 RRF 融合排序
              </p>
            </div>
          </label>
        </div>
      )}

      {/* Results */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-white rounded-2xl border border-gray-100 p-5 animate-pulse"
            >
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 bg-gray-100 rounded-xl shrink-0" />
                <div className="flex-1 space-y-3">
                  <div className="h-4 bg-gray-100 rounded w-1/3" />
                  <div className="h-3 bg-gray-50 rounded w-full" />
                  <div className="h-3 bg-gray-50 rounded w-2/3" />
                  <div className="h-3 bg-gray-50 rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : searched && results.length === 0 ? (
        /* Empty state */
        <div className="text-center py-16">
          <div className="w-16 h-16 bg-gray-50 rounded-3xl flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-gray-300" />
          </div>
          <h3 className="text-lg font-bold text-gray-300 mb-1">
            未找到相关结果
          </h3>
          <p className="text-sm text-gray-300">
            试试更换关键词或关闭混合搜索
          </p>
        </div>
      ) : !searched ? (
        /* Initial state */
        <div className="text-center py-16">
          <div className="w-20 h-20 bg-indigo-50 rounded-[32px] flex items-center justify-center mx-auto mb-5">
            <Sparkles className="w-10 h-10 text-indigo-300" />
          </div>
          <h3 className="text-lg font-bold text-gray-400 mb-1">
            输入关键词开始搜索
          </h3>
          <p className="text-sm text-gray-300">
            支持语义搜索和全文关键词搜索
          </p>
        </div>
      ) : (
        /* Results list */
        <div className="space-y-5">
          {/* Result meta */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              找到 <span className="font-bold text-gray-800">{total}</span> 个结果
              {queryTime > 0 && (
                <span className="text-gray-300 ml-2">
                  · {queryTime.toFixed(0)}ms
                </span>
              )}
            </p>
            {hybrid && (
              <span className="text-[10px] font-bold text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full uppercase tracking-wider">
                混合搜索
              </span>
            )}
          </div>

          {/* Result cards */}
          {results.map((r, i) => (
            <ResultCard key={r.chunk_id} result={r} rank={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
