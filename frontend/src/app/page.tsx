"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Bot, TrendingUp } from "lucide-react";

interface OverviewData {
  total_seasons: number;
  total_matches: number;
  total_players: number;
  total_teams: number;
  total_venues: number;
  avg_first_innings_score: number;
  highest_team_score: number;
}

interface SeasonTrend {
  season: number;
  total_matches: number;
  avg_first_innings_score: number;
  avg_second_innings_score: number;
  highest_score: number;
}

interface StatsData {
  chasing_advantage_test: {
    chase_win_pct: number;
    p_value: number;
    statistically_significant_at_0_05: boolean;
  };
  scoring_era_shift_test: {
    early_era_2008_2017_avg: number;
    modern_era_2018_2026_avg: number;
    difference_runs: number;
    p_value: number;
  };
}

export default function OverviewPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [seasons, setSeasons] = useState<SeasonTrend[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<OverviewData>("/api/analytics/overview"),
      apiFetch<SeasonTrend[]>("/api/analytics/seasons"),
      apiFetch<StatsData>("/api/analytics/stats"),
    ])
      .then(([ov, sz, st]) => {
        setOverview(ov);
        setSeasons(sz);
        setStats(st);
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/40 p-6 text-sm text-red-300">
        Failed to load IPL analytics from backend: {error}. Make sure FastAPI is running on port 7860.
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        Loading live IPL Intelligence data (waking up API if sleeping)...
      </div>
    );
  }

  const kpis = [
    { label: "Seasons", value: overview.total_seasons },
    { label: "Matches", value: overview.total_matches.toLocaleString() },
    { label: "Players", value: overview.total_players.toLocaleString() },
    { label: "Venues", value: overview.total_venues },
    { label: "Avg 1st Innings", value: overview.avg_first_innings_score },
    { label: "Highest Total", value: overview.highest_team_score },
  ];

  return (
    <div className="space-y-8">
      <section className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">IPL Intelligence</h1>
          <p className="mt-1 text-sm text-slate-400">
            Historical IPL Data Warehouse (2008–2026), Statistical Analytics & Agentic AI Assistant.
          </p>
        </div>
        <Link
          href="/assistant"
          className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-400"
        >
          <Bot className="h-4 w-4" />
          Ask AI Analyst
        </Link>
      </section>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <p className="text-xs font-medium text-slate-400">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold text-white">{kpi.value}</p>
          </div>
        ))}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">Scoring Evolution Across IPL Seasons</h2>
        </div>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={seasons}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="season" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: 8 }}
              />
              <Line
                type="monotone"
                dataKey="avg_first_innings_score"
                name="Avg 1st Innings"
                stroke="#f59e0b"
                strokeWidth={2.5}
                dot={{ r: 3 }}
              />
              <Line
                type="monotone"
                dataKey="avg_second_innings_score"
                name="Avg 2nd Innings"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {stats && (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h3 className="text-sm font-semibold text-amber-400">Statistical Finding: Chasing Advantage</h3>
            <p className="mt-2 text-2xl font-bold text-white">
              {stats.chasing_advantage_test.chase_win_pct}% Chase Win Rate
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Exact Binomial Test p-value: {stats.chasing_advantage_test.p_value} (
              {stats.chasing_advantage_test.statistically_significant_at_0_05
                ? "Statistically significant at α = 0.05"
                : "Not statistically significant at α = 0.05"}
              )
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h3 className="text-sm font-semibold text-sky-400">Statistical Finding: Modern Scoring Shift</h3>
            <p className="mt-2 text-2xl font-bold text-white">
              +{stats.scoring_era_shift_test.difference_runs} Runs / 1st Innings
            </p>
            <p className="mt-1 text-xs text-slate-400">
              2008–2017 Avg: {stats.scoring_era_shift_test.early_era_2008_2017_avg} vs 2018–2026 Avg:{" "}
              {stats.scoring_era_shift_test.modern_era_2018_2026_avg} (Welch&apos;s t-test p ={" "}
              {stats.scoring_era_shift_test.p_value})
            </p>
          </div>
        </section>
      )}
    </div>
  );
}