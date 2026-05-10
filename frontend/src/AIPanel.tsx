import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { api, SearchResult } from "./api";
import {
  Sparkles,
  ArrowUp,
  Cpu,
  ShieldCheck,
  Copy,
  CheckCircle,
  RefreshCw,
  Loader,
  PanelRightClose,
} from "lucide-react";

interface AIPanelProps {
  kbId: string | null;
}

/** 在 markdown 块级元素前补换行 */
function normalizeBlock(text: string): string {
  return text
    .replace(/(?<=\S)(?=#{1,6}\s)/g, "\n")
    .replace(/(?<=\S)(?=\d+\.\s)/g, "\n")
    .replace(/(?<=\S)(?=[-\*]\s)/g, "\n")
    .replace(/\n{2,}/g, "\n")
    .trim();
}

export function AIPanel({ kbId }: AIPanelProps) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState<string[]>([]);
  const [hasAnswered, setHasAnswered] = useState(false);
  const abortRef = useRef<{ abort: () => void } | null>(null);
  const pendingBuf = useRef("");
  const answerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const startRef = useRef(0);
  const [elapsed, setElapsed] = useState(0);

  // Auto-scroll
  useEffect(() => {
    if (answerRef.current && loading) {
      answerRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [answer, loading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  }, [query]);

  const handleSubmit = async () => {
    if (!query.trim() || !kbId) return;
    if (abortRef.current) abortRef.current.abort();

    const userQuery = query;
    setQuery("");
    setLoading(true);
    setThinking(true);
    setAnswer("");
    setSources([]);
    setHasAnswered(false);
    setElapsed(0);
    pendingBuf.current = "";
    startRef.current = performance.now();
    setThinkingSteps(["🔍 语义搜索中..."]);

    abortRef.current = api.queryStream(kbId, userQuery, {
      onToken: (text) => {
        if (thinking) {
          setThinking(false);
          setThinkingSteps((prev) => [...prev, "📝 生成回答中..."]);
        }
        pendingBuf.current += text;
        if (
          pendingBuf.current.length >= 30 ||
          pendingBuf.current.includes("\n")
        ) {
          setAnswer((prev) => prev + pendingBuf.current);
          pendingBuf.current = "";
          setHasAnswered(true);
        }
      },
      onSources: (sources) => {
        setSources(sources);
        setThinkingSteps((prev) => [...prev, `📎 引用 ${sources.length} 个来源`]);
      },
      onDone: () => {
        if (pendingBuf.current) {
          setAnswer((prev) => prev + pendingBuf.current);
          pendingBuf.current = "";
          setHasAnswered(true);
        }
        setElapsed(performance.now() - startRef.current);
        setLoading(false);
        setThinking(false);
      },
      onError: (err) => {
        console.error(err);
        setLoading(false);
        setThinking(false);
      },
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const copyAnswer = async () => {
    if (answer) {
      await navigator.clipboard.writeText(answer);
    }
  };

  return (
    <aside className="w-[360px] h-full border-l border-gray-200 bg-white flex flex-col shrink-0">
      {/* Header */}
      <div className="p-5 border-b border-gray-100">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
              AI Copilot
              <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            </h2>
            <p className="text-[11px] text-gray-400 font-medium">
              基于知识库深度问答
            </p>
          </div>
        </div>

        <div className="relative">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              kbId ? "询问知识库中的任何问题..." : "请先选择知识库"
            }
            disabled={!kbId || loading}
            rows={2}
            className="w-full bg-gray-50 border border-gray-100 rounded-[20px] p-4 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:bg-white transition-all resize-none custom-scrollbar disabled:opacity-50"
          />
          <button
            onClick={handleSubmit}
            disabled={!kbId || loading || !query.trim()}
            className="absolute bottom-3 right-3 w-8 h-8 bg-indigo-600 text-white rounded-xl flex items-center justify-center hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Model Stats */}
      <div className="px-5 py-2.5 bg-gray-50/50 flex items-center justify-between border-b border-gray-100">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-[10px] font-bold text-gray-500 uppercase tracking-wide">
            <Cpu className="w-3 h-3" /> DeepSeek V3
          </span>
          <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-600 uppercase tracking-wide">
            <ShieldCheck className="w-3 h-3" /> RAG
          </span>
        </div>
        {elapsed > 0 && (
          <span className="text-[10px] font-bold text-gray-400">
            {elapsed.toFixed(0)}ms
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5 custom-scrollbar">
        {!kbId ? (
          <div className="text-center py-16">
            <Sparkles className="w-10 h-10 text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-400 font-medium">
              请选择知识库开始提问
            </p>
          </div>
        ) : !hasAnswered && !loading && !thinking ? (
          <div className="text-center py-16">
            <Sparkles className="w-10 h-10 text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-400 font-medium">
              询问知识库中的任何问题
            </p>
            <p className="text-[11px] text-gray-300 mt-1">
              Enter 发送 · Shift+Enter 换行
            </p>
          </div>
        ) : (
          <>
            {/* Answer */}
            {answer && (
              <div className="space-y-3">
                <div
                  ref={answerRef}
                  className="bg-indigo-50/50 rounded-2xl p-4 border border-indigo-100/50"
                >
                  <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed">
                    <ReactMarkdown
                      components={{
                        ol: ({ children }) => (
                          <ol
                            style={{
                              margin: 0,
                              paddingLeft: 20,
                              listStylePosition: "inside",
                            }}
                          >
                            {children}
                          </ol>
                        ),
                        ul: ({ children }) => (
                          <ul
                            style={{
                              margin: 0,
                              paddingLeft: 20,
                              listStylePosition: "inside",
                            }}
                          >
                            {children}
                          </ul>
                        ),
                        li: ({ children, ...props }) => {
                          const p = props as any;
                          return (
                            <li
                              style={{
                                margin: 0,
                                listStyle: p.ordered ? "none" : "disc",
                              }}
                            >
                              {p.ordered && (
                                <span style={{ marginRight: 4 }}>
                                  {(p.index ?? 0) + 1}.
                                </span>
                              )}
                              {children}
                            </li>
                          );
                        },
                        p: ({ children }) => (
                          <p style={{ margin: "4px 0" }}>{children}</p>
                        ),
                        h1: ({ children }) => (
                          <h1
                            style={{
                              margin: "6px 0 2px",
                              fontSize: 17,
                              fontWeight: 600,
                            }}
                          >
                            {children}
                          </h1>
                        ),
                        h2: ({ children }) => (
                          <h2
                            style={{
                              margin: "5px 0 2px",
                              fontSize: 16,
                              fontWeight: 600,
                            }}
                          >
                            {children}
                          </h2>
                        ),
                        h3: ({ children }) => (
                          <h3
                            style={{
                              margin: "4px 0 2px",
                              fontSize: 15,
                              fontWeight: 600,
                            }}
                          >
                            {children}
                          </h3>
                        ),
                        pre: ({ children }) => (
                          <pre
                            style={{
                              background: "#1e293b",
                              color: "#e2e8f0",
                              padding: 12,
                              borderRadius: 6,
                              overflow: "auto",
                              fontSize: 12,
                              lineHeight: 1.5,
                              margin: "6px 0",
                            }}
                          >
                            {children}
                          </pre>
                        ),
                        code: ({ children }) => (
                          <code
                            style={{
                              background: "#f1f5f9",
                              padding: "1px 4px",
                              borderRadius: 3,
                              fontSize: "0.9em",
                            }}
                          >
                            {children}
                          </code>
                        ),
                      }}
                    >
                      {normalizeBlock(answer)}
                    </ReactMarkdown>
                    {loading && (
                      <span
                        className="inline-block w-[2px] h-4 bg-indigo-500 ml-0.5 align-middle"
                        style={{ animation: "blink 0.8s step-end infinite" }}
                      />
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Citations */}
            {sources.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">
                  引用来源 ({sources.length})
                </h4>
                <div className="grid grid-cols-2 gap-2">
                  {sources.slice(0, 4).map((s, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 p-2 bg-white border border-gray-100 rounded-xl hover:border-indigo-200 cursor-pointer transition-colors shadow-sm"
                    >
                      <div className="w-6 h-6 bg-purple-50 text-purple-600 rounded flex items-center justify-center shrink-0">
                        <span className="text-[10px] font-bold">#{i + 1}</span>
                      </div>
                      <span className="text-xs text-gray-700 truncate font-medium">
                        {s.document_title}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Thinking State */}
            {thinking && (
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-sm text-gray-400">
                  <div className="flex items-center gap-1">
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                  </div>
                  <span className="font-medium italic">正在分析...</span>
                </div>
                <div className="space-y-2 pl-6 border-l-2 border-indigo-100">
                  {thinkingSteps.map((step, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs font-semibold"
                      style={{
                        color:
                          i === thinkingSteps.length - 1 && !loading
                            ? "#059669"
                            : i === thinkingSteps.length - 1
                            ? "#6366f1"
                            : "#9ca3af",
                      }}
                    >
                      {i === thinkingSteps.length - 1 && loading ? (
                        <RefreshCw className="w-3 h-3 animate-spin shrink-0" />
                      ) : (
                        <CheckCircle className="w-3 h-3 shrink-0" />
                      )}
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty state for no results */}
            {hasAnswered && !loading && !answer && (
              <div className="text-center py-8">
                <p className="text-sm text-gray-400">未找到相关结果</p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      {answer && (
        <div className="p-4 border-t border-gray-100">
          <button
            onClick={copyAnswer}
            className="w-full py-2 bg-gray-50 hover:bg-gray-100 rounded-xl text-xs font-bold text-gray-500 transition-colors flex items-center justify-center gap-2"
          >
            <Copy className="w-3.5 h-3.5" />
            复制回答
          </button>
        </div>
      )}
    </aside>
  );
}
