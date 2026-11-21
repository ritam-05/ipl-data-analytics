"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import DynamicChart, { ChartSpec } from "@/components/DynamicChart";
import { Bookmark, Code2 } from "lucide-react";

interface SavedAnalysis {
  id: string;
  title: string;
  question: string;
  summary: string;
  sql_query: string | null;
  chart_spec: ChartSpec | null;
  created_at: string;
}

export default function SavedAnalysesPage() {
  const [isAuthed, setIsAuthed] = useState<boolean | null>(null);
  const [items, setItems] = useState<SavedAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      const authed = Boolean(data.session);
      setIsAuthed(authed);
      if (authed) {
        apiFetch<SavedAnalysis[]>("/api/saved-analyses", {}, true)
          .then(setItems)
          .catch((err) => setError(err.message))
          .finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    });
  }, []);

  if (isAuthed === null || loading) {
    return <div className="py-16 text-center text-sm text-slate-400">Loading saved analyses...</div>;
  }

  if (!isAuthed) {
    return (
      <div className="mx-auto mt-12 max-w-lg rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-center">
        <Bookmark className="mx-auto h-10 w-10 text-amber-400" />
        <h1 className="mt-4 text-xl font-bold text-white">Sign in to view Saved Analyses</h1>
        <Link
          href="/login"
          className="mt-6 inline-block rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-400"
        >
          Sign In
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Saved Analyses</h1>
        <p className="text-sm text-slate-400">
          Your bookmarked cricketmama.exe insights, generated SQL queries, and interactive charts.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {items.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-10 text-center text-sm text-slate-400">
          No saved analyses yet. Ask a question in{" "}
          <Link href="/assistant" className="text-amber-400 underline">
            cricketmama.exe
          </Link>{" "}
          and click <strong>Save Analysis</strong>.
        </div>
      ) : (
        <div className="space-y-6">
          {items.map((item) => (
            <article
              key={item.id}
              className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6"
            >
              <div className="flex items-start justify-between gap-4">
                <h2 className="text-lg font-semibold text-white">{item.title}</h2>
                <span className="shrink-0 text-xs text-slate-500">
                  {new Date(item.created_at).toLocaleDateString()}
                </span>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
                {item.summary}
              </p>

              {item.chart_spec && <DynamicChart spec={item.chart_spec} />}

              {item.sql_query && (
                <details className="mt-4 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs">
                  <summary className="flex cursor-pointer items-center gap-1.5 font-medium text-slate-400">
                    <Code2 className="h-3.5 w-3.5" />
                    SQL Query
                  </summary>
                  <pre className="mt-2 overflow-x-auto text-[11px] text-emerald-400">
                    {item.sql_query}
                  </pre>
                </details>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}