"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

interface SeasonRow {
  season: number;
  total_matches: number;
  avg_first_innings_score: number;
  avg_second_innings_score: number;
  highest_score: number;
  chase_wins: number;
  bat_first_wins: number;
}

interface ExtremeMatchesResponse {
  highest_scoring_matches: Array<{
    match_id: number;
    season: number;
    start_date: string;
    venue: string;
    team_1: string;
    team_2: string;
    innings_1_runs: number;
    innings_2_runs: number;
    combined_runs: number;
    winner: string;
  }>;
  closest_run_margin_matches: Array<{
    match_id: number;
    season: number;
    start_date: string;
    team_1: string;
    team_2: string;
    innings_1_runs: number;
    innings_2_runs: number;
    winner: string;
    win_margin: number;
  }>;
}

export default function SeasonsPage() {
  const [seasons, setSeasons] = useState<SeasonRow[]>([]);
  const [extremes, setExtremes] = useState<ExtremeMatchesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<SeasonRow[]>("/api/analytics/seasons"),
      apiFetch<ExtremeMatchesResponse>("/api/analytics/matches/extremes?limit=5"),
    ])
      .then(([sz, ex]) => {
        setSeasons(sz);
        setExtremes(ex);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="py-16 text-center text-sm text-slate-400">Loading season & match analytics...</div>;
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Season & Match Analytics</h1>
        <p className="text-sm text-slate-400">
          Season-wise chasing vs. defending splits, scoring benchmarks, and historic match extremes.
        </p>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-300">
          Chase Wins vs. Bat First Wins by Season (2008–2026)
        </h2>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={seasons}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="season" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: 8 }} />
              <Legend />
              <Bar dataKey="bat_first_wins" name="Bat First Wins" fill="#f59e0b" />
              <Bar dataKey="chase_wins" name="Chase Wins" fill="#38bdf8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {extremes && (
        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="mb-4 text-sm font-semibold text-amber-400">Highest Scoring Matches (Combined Runs)</h2>
            <div className="space-y-3">
              {extremes.highest_scoring_matches.map((m) => (
                <div key={m.match_id} className="rounded-xl bg-slate-950/70 p-3 text-xs">
                  <div className="flex justify-between font-semibold text-white">
                    <span>{m.team_1} vs {m.team_2}</span>
                    <span className="text-amber-400">{m.combined_runs} runs</span>
                  </div>
                  <p className="mt-1 text-slate-400">
                    {m.season} • {m.innings_1_runs} vs {m.innings_2_runs} • Winner: {m.winner}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="mb-4 text-sm font-semibold text-sky-400">Closest Run-Margin Thrillers</h2>
            <div className="space-y-3">
              {extremes.closest_run_margin_matches.map((m) => (
                <div key={m.match_id} className="rounded-xl bg-slate-950/70 p-3 text-xs">
                  <div className="flex justify-between font-semibold text-white">
                    <span>{m.team_1} vs {m.team_2}</span>
                    <span className="text-sky-400">Won by {m.win_margin} run</span>
                  </div>
                  <p className="mt-1 text-slate-400">
                    {m.season} ({m.start_date}) • {m.innings_1_runs} vs {m.innings_2_runs} • Winner: {m.winner}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}