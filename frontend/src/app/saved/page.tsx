"use client";

import { useEffect, useState, type ComponentType } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bookmark, Trash2, Calendar, Sparkles } from "lucide-react";
import { supabase } from "@/lib/supabase";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as ComponentType<any>;

interface SavedAnalysis {
  id: string;
  question: string;
  answer: string;
  chart_spec?: {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: any[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    layout?: Record<string, any>;
  } | null;
  created_at: string;
}

export default function SavedAnalysesPage() {
  const router = useRouter();
  const [analyses, setAnalyses] = useState<SavedAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSaved() {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push("/login");
        return;
      }

      const { data, error } = await supabase
        .from("saved_analyses")
        .select("id, question, answer, chart_spec, created_at")
        .order("created_at", { ascending: false });

      if (!error && data) {
        setAnalyses(data);
      }
      setLoading(false);
    }

    fetchSaved();
  }, [router]);

  async function handleDelete(id: string) {
    setDeletingId(id);
    const { error } = await supabase
      .from("saved_analyses")
      .delete()
      .eq("id", id);

    if (!error) {
      setAnalyses((prev) => prev.filter((item) => item.id !== id));
    }
    setDeletingId(null);
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 px-4 sm:px-8 py-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-5">
          <div>
            <div className="flex items-center gap-2.5">
              <Bookmark className="w-6 h-6 text-amber-400" />
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                Saved Analyses
              </h1>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Your bookmarked cricketmama.exe insights and interactive visualizations.
            </p>
          </div>
          {!loading && (
            <span className="text-xs font-medium px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
              {analyses.length} {analyses.length === 1 ? "Insight" : "Insights"}
            </span>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            {[1, 2].map((n) => (
              <div
                key={n}
                className="h-44 rounded-2xl bg-[#0d1424] border border-slate-800/80 animate-pulse"
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && analyses.length === 0 && (
          <div className="rounded-2xl bg-[#0d1424] border border-slate-800/80 p-12 text-center">
            <Sparkles className="w-8 h-8 text-amber-400 mx-auto mb-3 opacity-80" />
            <h2 className="text-lg font-semibold text-white">No saved analyses yet</h2>
            <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
              Ask cricketmama.exe a question in the AI Assistant and click Save to bookmark insights here.
            </p>
          </div>
        )}

        {/* Saved Cards */}
        <div className="space-y-6">
          {analyses.map((item) => (
            <article
              key={item.id}
              className="rounded-2xl bg-[#0d1424] border border-slate-800/90 shadow-lg overflow-hidden transition-colors hover:border-slate-700"
            >
              {/* Card Header */}
              <div className="flex flex-wrap items-start justify-between gap-3 px-6 py-4 bg-slate-900/60 border-b border-slate-800/80">
                <h2 className="text-base sm:text-lg font-semibold text-white leading-snug">
                  {item.question}
                </h2>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
                    <Calendar className="w-3.5 h-3.5" />
                    {new Date(item.created_at).toLocaleDateString("en-GB")}
                  </span>
                  <button
                    onClick={() => handleDelete(item.id)}
                    disabled={deletingId === item.id}
                    title="Remove saved analysis"
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Formatted Markdown Body */}
              <div className="px-6 py-5 text-sm sm:text-[15px] text-slate-200 leading-relaxed space-y-4">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children }) => (
                      <h3 className="text-lg font-bold text-amber-400 mt-4 mb-2 first:mt-0">
                        {children}
                      </h3>
                    ),
                    h2: ({ children }) => (
                      <h3 className="text-base font-bold text-amber-400 mt-4 mb-2 first:mt-0">
                        {children}
                      </h3>
                    ),
                    h3: ({ children }) => (
                      <h4 className="text-sm font-semibold uppercase tracking-wider text-amber-400 mt-5 mb-2 first:mt-0">
                        {children}
                      </h4>
                    ),
                    p: ({ children }) => (
                      <p className="text-slate-200 leading-relaxed my-2">{children}</p>
                    ),
                    ul: ({ children }) => (
                      <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5 my-2.5 pl-4 list-disc marker:text-amber-400">
                        {children}
                      </ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="space-y-1.5 my-2.5 pl-5 list-decimal marker:text-amber-400">
                        {children}
                      </ol>
                    ),
                    li: ({ children }) => (
                      <li className="text-slate-300">{children}</li>
                    ),
                    strong: ({ children }) => (
                      <strong className="font-semibold text-white">{children}</strong>
                    ),
                    table: ({ children }) => (
                      <div className="my-4 overflow-x-auto rounded-xl border border-slate-800">
                        <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                          {children}
                        </table>
                      </div>
                    ),
                    thead: ({ children }) => (
                      <thead className="bg-slate-900/90 text-slate-300 font-semibold">
                        {children}
                      </thead>
                    ),
                    tbody: ({ children }) => (
                      <tbody className="divide-y divide-slate-800/70 bg-[#0a101d]">
                        {children}
                      </tbody>
                    ),
                    th: ({ children }) => (
                      <th className="px-4 py-2.5 text-xs uppercase tracking-wider text-amber-300/90 whitespace-nowrap">
                        {children}
                      </th>
                    ),
                    td: ({ children }) => (
                      <td className="px-4 py-2.5 text-slate-200 whitespace-nowrap font-mono text-xs sm:text-sm">
                        {children}
                      </td>
                    ),
                  }}
                >
                  {item.answer}
                </ReactMarkdown>

                {/* Optional Saved Chart */}
                {item.chart_spec &&
                  Array.isArray(item.chart_spec.data) &&
                  item.chart_spec.data.length > 0 && (
                    <div className="mt-5 pt-4 border-t border-slate-800/80">
                      <div className="rounded-xl bg-[#080d18] border border-slate-800 p-3">
                        <Plot
                          data={item.chart_spec.data}
                          layout={{
                            autosize: true,
                            paper_bgcolor: "rgba(0,0,0,0)",
                            plot_bgcolor: "rgba(0,0,0,0)",
                            font: { color: "#cbd5e1", size: 12 },
                            margin: { l: 50, r: 24, t: 44, b: 48 },
                            xaxis: { gridcolor: "#1e293b" },
                            yaxis: { gridcolor: "#1e293b" },
                            ...(item.chart_spec.layout || {}),
                          }}
                          useResizeHandler
                          style={{ width: "100%", height: "320px" }}
                          config={{ displayModeBar: false, responsive: true }}
                        />
                      </div>
                    </div>
                  )}
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}