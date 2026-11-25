"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LabelList,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
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
  total_fours: number;
  total_sixes: number;
}

interface TeamWinRow {
  team: string;
  wins: number;
}

interface WinTypeRow {
  win_type: string;
  match_count: number;
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

const TEAM_COLORS = [
  "#0ea5e9",
  "#eab308",
  "#ef4444",
  "#a855f7",
  "#3b82f6",
  "#f472b6",
  "#ec4899",
  "#f97316",
  "#1d4ed8",
  "#10b981",
  "#64748b",
  "#8b5cf6",
  "#fb923c",
  "#14b8a6",
  "#f59e0b",
];

const WIN_TYPE_COLORS = ["#0ea5e9", "#3b82f6", "#f59e0b", "#a855f7"];

const WIN_TYPE_LABELS: Record<string, string> = {
  wickets: "Chase Wins (Wickets)",
  runs: "Defend Wins (Runs)",
  tie: "Tie / Super Over",
  no_result: "No Result",
};

export default function OverviewPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [seasons, setSeasons] = useState<SeasonTrend[]>([]);
  const [teamWins, setTeamWins] = useState<TeamWinRow[]>([]);
  const [winTypes, setWinTypes] = useState<WinTypeRow[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<OverviewData>("/api/analytics/overview"),
      apiFetch<SeasonTrend[]>("/api/analytics/seasons"),
      apiFetch<TeamWinRow[]>("/api/analytics/teams"),
      apiFetch<WinTypeRow[]>("/api/analytics/win-types"),
      apiFetch<StatsData>("/api/analytics/stats"),
    ])
      .then(([ov, sz, tm, wt, st]) => {
        setOverview(ov);
        setSeasons(sz);
        const sortedWins = [...tm]
          .filter((t) => t.wins > 0)
          .sort((a, b) => b.wins - a.wins);
        setTeamWins(sortedWins);
        setWinTypes(wt);
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
        Loading live Know IPL data...
      </div>
    );
  }

  const totalWinTypeMatches = winTypes.reduce((sum, item) => sum + item.match_count, 0);
  const formattedWinTypes = winTypes.map((w) => {
    const label = WIN_TYPE_LABELS[w.win_type] || w.win_type;
    const pct =
      totalWinTypeMatches > 0 ? ((w.match_count / totalWinTypeMatches) * 100).toFixed(1) : "0.0";
    return {
      ...w,
      displayName: `${label}: ${w.match_count} (${pct}%)`,
    };
  });

  return (
    <div className="space-y-8">
      <section className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Know IPL</h1>
          <p className="mt-1 text-sm text-slate-400">
            Historical IPL Data Warehouse (2008–2026), Statistical Analytics &amp; cricketmama.exe.
          </p>
        </div>
        <Link
          href="/assistant"
          className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-400"
        >
          <Bot className="h-4 w-4" />
          Ask cricketmama.exe
        </Link>
      </section>

      {/* Top Row: Scoring Evolution Line Chart + Total Matches Won by Teams Horizontal Bar */}
      <section className="grid gap-6 lg:grid-cols-2">
        <div className="flex flex-col rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-amber-400" />
            <div>
              <h2 className="text-base font-semibold text-white">
                Avg 1st Innings Score vs. Avg 2nd Innings Score
              </h2>
              <p className="text-xs text-slate-400">By season (2008–2026)</p>
            </div>
          </div>
          <div className="min-h-[380px] flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={seasons}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="season" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: 8,
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="avg_first_innings_score"
                  name="Avg 1st Innings Score"
                  stroke="#38bdf8"
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="avg_second_innings_score"
                  name="Avg 2nd Innings Score"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-base font-semibold text-white">Total Matches Won by Teams</h2>
          <p className="mb-4 text-xs text-slate-400">All-time matches won by franchise</p>
          <div className="h-[440px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={teamWins}
                layout="vertical"
                margin={{ top: 4, right: 36, left: 8, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#94a3b8" fontSize={11} domain={[0, 175]} />
                <YAxis
                  type="category"
                  dataKey="team"
                  stroke="#cbd5e1"
                  fontSize={11}
                  width={185}
                  interval={0}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="wins" name="Wins" radius={[0, 4, 4, 0]}>
                  {teamWins.map((entry, idx) => (
                    <Cell
                      key={entry.team}
                      fill={TEAM_COLORS[idx % TEAM_COLORS.length]}
                    />
                  ))}
                  <LabelList
                    dataKey="wins"
                    position="right"
                    fill="#cbd5e1"
                    fontSize={11}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* Bottom Row: Win Type Donut Chart + Total Fours & Total Sixes by Season */}
      <section className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 lg:col-span-1">
          <h2 className="text-base font-semibold text-white">Match Outcomes</h2>
          <p className="mb-3 text-xs text-slate-400">Breakdown by result type</p>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={formattedWinTypes}
                  dataKey="match_count"
                  nameKey="displayName"
                  cx="50%"
                  cy="44%"
                  innerRadius={50}
                  outerRadius={78}
                  paddingAngle={3}
                >
                  {formattedWinTypes.map((entry, idx) => (
                    <Cell
                      key={entry.win_type}
                      fill={WIN_TYPE_COLORS[idx % WIN_TYPE_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: 8,
                  }}
                />
                <Legend
                  layout="vertical"
                  verticalAlign="bottom"
                  align="center"
                  wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 lg:col-span-2">
          <h2 className="text-base font-semibold text-white">Total Fours and Total Sixes</h2>
          <p className="mb-3 text-xs text-slate-400">By season</p>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={seasons}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="season" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: 8,
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="total_fours"
                  name="Total Fours"
                  stroke="#38bdf8"
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="total_sixes"
                  name="Total Sixes"
                  stroke="#6366f1"
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {stats && (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h3 className="text-sm font-semibold text-amber-400">
              Statistical Finding: Chasing Advantage
            </h3>
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
            <h3 className="text-sm font-semibold text-sky-400">
              Statistical Finding: Modern Scoring Shift
            </h3>
            <p className="mt-2 text-2xl font-bold text-white">
              +{stats.scoring_era_shift_test.difference_runs} Runs / 1st Innings
            </p>
            <p className="mt-1 text-xs text-slate-400">
              2008–2017 Avg: {stats.scoring_era_shift_test.early_era_2008_2017_avg} vs 2018–2026
              Avg: {stats.scoring_era_shift_test.modern_era_2018_2026_avg} (Welch&apos;s t-test p ={" "}
              {stats.scoring_era_shift_test.p_value})
            </p>
          </div>
        </section>
      )}
    </div>
  );
}