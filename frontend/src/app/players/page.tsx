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
} from "recharts";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";

interface BatterRow {
  player_name: string;
  matches: number;
  total_runs: number;
  balls_faced: number;
  fours: number;
  sixes: number;
  highest_score: number;
  batting_average: number | null;
  strike_rate: number;
}

interface BowlerRow {
  player_name: string;
  matches: number;
  total_wickets: number;
  runs_conceded: number;
  overs: number;
  economy_rate: number;
  bowling_average: number | null;
  bowling_strike_rate: number | null;
}

interface ConsistencyRow {
  player_name: string;
  seasons_played: number;
  total_runs: number;
  mean_runs_per_season: number;
  std_runs_per_season: number;
  cv: number;
}

interface PlayerDirectoryRow {
  player_name: string;
  matches: number;
  runs: number;
  balls_faced: number;
  fours: number;
  sixes: number;
  highest_score: number;
  batting_average: number | null;
  batting_sr: number | null;
  wickets: number;
  runs_conceded: number;
  overs: number;
  economy_rate: number | null;
  bowling_average: number | null;
  bowling_sr: number | null;
}

interface PlayerDirectoryResponse {
  total: number;
  limit: number;
  offset: number;
  players: PlayerDirectoryRow[];
}

const SEASONS = Array.from({ length: 19 }, (_, i) => 2026 - i);
const PAGE_SIZE = 50;

export default function PlayersPage() {
  const [tab, setTab] = useState<"batters" | "bowlers" | "consistency" | "all">("batters");
  const [season, setSeason] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [batters, setBatters] = useState<BatterRow[]>([]);
  const [bowlers, setBowlers] = useState<BowlerRow[]>([]);
  const [consistency, setConsistency] = useState<ConsistencyRow[]>([]);
  const [directory, setDirectory] = useState<PlayerDirectoryRow[]>([]);
  const [totalPlayers, setTotalPlayers] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPage(0);
  }, [season, search, tab]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const seasonParam = season === "all" ? "" : `&season=${season}`;

    if (tab === "all") {
      const offset = page * PAGE_SIZE;
      const searchParam = search.trim() ? `&search=${encodeURIComponent(search.trim())}` : "";
      apiFetch<PlayerDirectoryResponse>(
        `/api/analytics/players/all?limit=${PAGE_SIZE}&offset=${offset}${seasonParam}${searchParam}`
      )
        .then((res) => {
          setDirectory(res.players);
          setTotalPlayers(res.total);
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
      return;
    }

    Promise.all([
      apiFetch<BatterRow[]>(`/api/analytics/players/batters?limit=30${seasonParam}`),
      apiFetch<BowlerRow[]>(`/api/analytics/players/bowlers?limit=30${seasonParam}`),
      apiFetch<ConsistencyRow[]>(
        `/api/analytics/players/consistency?min_seasons=6&min_total_runs=2000&limit=15`
      ),
    ])
      .then(([bat, bowl, cons]) => {
        setBatters(bat);
        setBowlers(bowl);
        setConsistency(cons);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [season, tab, page, search]);

  const q = search.trim().toLowerCase();
  const filteredBatters = batters.filter((b) => b.player_name.toLowerCase().includes(q));
  const filteredBowlers = bowlers.filter((b) => b.player_name.toLowerCase().includes(q));
  const filteredConsistency = consistency.filter((c) => c.player_name.toLowerCase().includes(q));

  const chartData: Array<BatterRow | BowlerRow | ConsistencyRow> =
    tab === "batters"
      ? filteredBatters.slice(0, 10)
      : tab === "bowlers"
      ? filteredBowlers.slice(0, 10)
      : filteredConsistency.slice(0, 10);

  const totalPages = Math.max(1, Math.ceil(totalPlayers / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Player Analytics</h1>
          <p className="text-sm text-slate-400">
            Batting leaders, bowling leaders, consistency (CV), and complete player career stats.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search player..."
              className="rounded-lg border border-slate-700 bg-slate-900 py-2 pl-9 pr-3 text-sm text-white focus:border-amber-500 focus:outline-none"
            />
          </div>

          {tab !== "consistency" && (
            <select
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-amber-500 focus:outline-none"
            >
              <option value="all">All-Time (2008–2026)</option>
              {SEASONS.map((yr) => (
                <option key={yr} value={yr}>
                  IPL {yr}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setTab("batters")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            tab === "batters"
              ? "bg-amber-500 text-slate-950"
              : "bg-slate-900 text-slate-300 hover:bg-slate-800"
          }`}
        >
          Top Batters
        </button>
        <button
          onClick={() => setTab("bowlers")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            tab === "bowlers"
              ? "bg-amber-500 text-slate-950"
              : "bg-slate-900 text-slate-300 hover:bg-slate-800"
          }`}
        >
          Top Bowlers
        </button>
        <button
          onClick={() => setTab("consistency")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            tab === "consistency"
              ? "bg-amber-500 text-slate-950"
              : "bg-slate-900 text-slate-300 hover:bg-slate-800"
          }`}
        >
          Consistency (CV)
        </button>
        <button
          onClick={() => setTab("all")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            tab === "all"
              ? "bg-amber-500 text-slate-950"
              : "bg-slate-900 text-slate-300 hover:bg-slate-800"
          }`}
        >
          Player Stats
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-16 text-center text-sm text-slate-400">Loading player analytics...</div>
      ) : tab === "all" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <span>
              Showing <strong className="text-white">{directory.length}</strong> of{" "}
              <strong className="text-amber-400">{totalPlayers.toLocaleString()}</strong> IPL players
              {season !== "all" ? ` in IPL ${season}` : " across all seasons"}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Prev
              </button>
              <span className="px-2 text-slate-300">
                Page {page + 1} / {totalPages}
              </span>
              <button
                type="button"
                disabled={page + 1 >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40"
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-900/90 uppercase text-slate-400">
                <tr>
                  <th className="sticky left-0 bg-slate-900 px-3 py-3 text-white">Player</th>
                  <th className="px-3 py-3">Mat</th>
                  <th className="px-3 py-3 text-amber-400">Runs</th>
                  <th className="px-3 py-3">Bat Avg</th>
                  <th className="px-3 py-3">Bat SR</th>
                  <th className="px-3 py-3">4s</th>
                  <th className="px-3 py-3">6s</th>
                  <th className="px-3 py-3">HS</th>
                  <th className="px-3 py-3 text-sky-400">Wkts</th>
                  <th className="px-3 py-3">Overs</th>
                  <th className="px-3 py-3">Econ</th>
                  <th className="px-3 py-3">Bowl Avg</th>
                  <th className="px-3 py-3">Bowl SR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {directory.map((p) => (
                  <tr key={p.player_name} className="hover:bg-slate-800/40">
                    <td className="sticky left-0 bg-slate-950/95 px-3 py-2.5 font-medium text-white">
                      {p.player_name}
                    </td>
                    <td className="px-3 py-2.5 text-slate-300">{p.matches}</td>
                    <td className="px-3 py-2.5 font-semibold text-amber-400">
                      {p.runs.toLocaleString()}
                    </td>
                    <td className="px-3 py-2.5 text-slate-300">{p.batting_average ?? "—"}</td>
                    <td className="px-3 py-2.5 text-slate-300">{p.batting_sr ?? "—"}</td>
                    <td className="px-3 py-2.5 text-slate-300">{p.fours}</td>
                    <td className="px-3 py-2.5 text-slate-300">{p.sixes}</td>
                    <td className="px-3 py-2.5 text-slate-300">{p.highest_score}</td>
                    <td className="px-3 py-2.5 font-semibold text-sky-400">{p.wickets}</td>
                    <td className="px-3 py-2.5 text-slate-300">{p.overs}</td>
                    <td className="px-3 py-2.5 text-slate-300">{p.economy_rate ?? "—"}</td>
                    <td className="px-3 py-2.5 text-slate-300">{p.bowling_average ?? "—"}</td>
                    <td className="px-3 py-2.5 text-slate-300">{p.bowling_sr ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="mb-4 text-sm font-semibold text-slate-300">
              {tab === "batters" && "Top 10 Run Scorers"}
              {tab === "bowlers" && "Top 10 Wicket Takers"}
              {tab === "consistency" && "Most Consistent Batters (Lower CV = More Consistent)"}
            </h2>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="player_name"
                    stroke="#94a3b8"
                    fontSize={11}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: 8,
                    }}
                  />
                  {tab === "batters" && (
                    <Bar dataKey="total_runs" name="Runs" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  )}
                  {tab === "bowlers" && (
                    <Bar
                      dataKey="total_wickets"
                      name="Wickets"
                      fill="#38bdf8"
                      radius={[4, 4, 0, 0]}
                    />
                  )}
                  {tab === "consistency" && (
                    <Bar
                      dataKey="cv"
                      name="CV (Lower is better)"
                      fill="#10b981"
                      radius={[4, 4, 0, 0]}
                    />
                  )}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
            {tab === "batters" && (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Player</th>
                    <th className="px-4 py-3">Mat</th>
                    <th className="px-4 py-3">Runs</th>
                    <th className="px-4 py-3">Avg</th>
                    <th className="px-4 py-3">SR</th>
                    <th className="px-4 py-3">4s</th>
                    <th className="px-4 py-3">6s</th>
                    <th className="px-4 py-3">HS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {filteredBatters.map((b) => (
                    <tr key={b.player_name} className="hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-medium text-white">{b.player_name}</td>
                      <td className="px-4 py-3 text-slate-300">{b.matches}</td>
                      <td className="px-4 py-3 font-semibold text-amber-400">
                        {b.total_runs.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-slate-300">{b.batting_average ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-300">{b.strike_rate}</td>
                      <td className="px-4 py-3 text-slate-300">{b.fours}</td>
                      <td className="px-4 py-3 text-slate-300">{b.sixes}</td>
                      <td className="px-4 py-3 text-slate-300">{b.highest_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {tab === "bowlers" && (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Player</th>
                    <th className="px-4 py-3">Mat</th>
                    <th className="px-4 py-3">Wickets</th>
                    <th className="px-4 py-3">Overs</th>
                    <th className="px-4 py-3">Econ</th>
                    <th className="px-4 py-3">Avg</th>
                    <th className="px-4 py-3">SR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {filteredBowlers.map((bw) => (
                    <tr key={bw.player_name} className="hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-medium text-white">{bw.player_name}</td>
                      <td className="px-4 py-3 text-slate-300">{bw.matches}</td>
                      <td className="px-4 py-3 font-semibold text-sky-400">{bw.total_wickets}</td>
                      <td className="px-4 py-3 text-slate-300">{bw.overs}</td>
                      <td className="px-4 py-3 text-slate-300">{bw.economy_rate}</td>
                      <td className="px-4 py-3 text-slate-300">{bw.bowling_average ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-300">{bw.bowling_strike_rate ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {tab === "consistency" && (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Player</th>
                    <th className="px-4 py-3">Seasons</th>
                    <th className="px-4 py-3">Total Runs</th>
                    <th className="px-4 py-3">Mean Runs / Season</th>
                    <th className="px-4 py-3">Std Dev</th>
                    <th className="px-4 py-3">CV (Lower = Better)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {filteredConsistency.map((c) => (
                    <tr key={c.player_name} className="hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-medium text-white">{c.player_name}</td>
                      <td className="px-4 py-3 text-slate-300">{c.seasons_played}</td>
                      <td className="px-4 py-3 text-slate-300">{c.total_runs.toLocaleString()}</td>
                      <td className="px-4 py-3 text-slate-300">{c.mean_runs_per_season}</td>
                      <td className="px-4 py-3 text-slate-300">{c.std_runs_per_season}</td>
                      <td className="px-4 py-3 font-semibold text-emerald-400">{c.cv}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}