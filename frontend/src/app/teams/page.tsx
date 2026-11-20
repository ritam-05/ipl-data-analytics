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

interface TeamRow {
  team: string;
  matches_played: number;
  wins: number;
  win_pct: number;
  bat_first_wins: number;
  chase_wins: number;
}

interface H2HResult {
  team_a: string;
  team_b: string;
  total_matches: number;
  team_a_wins: number;
  team_b_wins: number;
  no_result_or_tie: number;
}

const SEASONS = Array.from({ length: 19 }, (_, i) => 2026 - i);

export default function TeamsPage() {
  const [season, setSeason] = useState<string>("all");
  const [teams, setTeams] = useState<TeamRow[]>([]);
  const [teamA, setTeamA] = useState("Mumbai Indians");
  const [teamB, setTeamB] = useState("Chennai Super Kings");
  const [h2h, setH2h] = useState<H2HResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    const param = season === "all" ? "" : `?season=${season}`;
    apiFetch<TeamRow[]>(`/api/analytics/teams${param}`)
      .then(setTeams)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [season]);

  useEffect(() => {
    if (!teamA || !teamB || teamA === teamB) return;
    apiFetch<H2HResult>(
      `/api/analytics/teams/h2h?team_a=${encodeURIComponent(teamA)}&team_b=${encodeURIComponent(teamB)}`
    )
      .then(setH2h)
      .catch(() => setH2h(null));
  }, [teamA, teamB]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Team Analytics</h1>
          <p className="text-sm text-slate-400">
            Franchise win percentages, chasing vs. defending records, and head-to-head rivalries.
          </p>
        </div>

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
      </div>

      {/* Head-to-Head Comparator */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-sm font-semibold text-amber-400">Head-to-Head Rivalry Comparator</h2>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <select
            value={teamA}
            onChange={(e) => setTeamA(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
          >
            {teams.map((t) => (
              <option key={t.team} value={t.team}>
                {t.team}
              </option>
            ))}
          </select>
          <span className="text-xs font-bold uppercase text-slate-500">vs</span>
          <select
            value={teamB}
            onChange={(e) => setTeamB(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
          >
            {teams.map((t) => (
              <option key={t.team} value={t.team}>
                {t.team}
              </option>
            ))}
          </select>
        </div>

        {h2h && (
          <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-xl bg-slate-950/70 p-4">
              <p className="text-xs text-slate-400">Matches</p>
              <p className="mt-1 text-2xl font-bold text-white">{h2h.total_matches}</p>
            </div>
            <div className="rounded-xl bg-slate-950/70 p-4">
              <p className="text-xs text-slate-400">{h2h.team_a}</p>
              <p className="mt-1 text-2xl font-bold text-amber-400">{h2h.team_a_wins ?? 0} Wins</p>
            </div>
            <div className="rounded-xl bg-slate-950/70 p-4">
              <p className="text-xs text-slate-400">{h2h.team_b}</p>
              <p className="mt-1 text-2xl font-bold text-sky-400">{h2h.team_b_wins ?? 0} Wins</p>
            </div>
            <div className="rounded-xl bg-slate-950/70 p-4">
              <p className="text-xs text-slate-400">Tie / No Result</p>
              <p className="mt-1 text-2xl font-bold text-slate-300">{h2h.no_result_or_tie ?? 0}</p>
            </div>
          </div>
        )}
      </section>

      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-slate-400">Loading team stats...</div>
      ) : (
        <>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="mb-4 text-sm font-semibold text-slate-300">Win Percentage by Franchise</h2>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={teams.slice(0, 12)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="team" stroke="#94a3b8" fontSize={10} interval={0} angle={-20} textAnchor="end" height={70} />
                  <YAxis stroke="#94a3b8" fontSize={12} unit="%" />
                  <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: 8 }} />
                  <Bar dataKey="win_pct" name="Win %" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-4 py-3">Franchise</th>
                  <th className="px-4 py-3">Matches</th>
                  <th className="px-4 py-3">Wins</th>
                  <th className="px-4 py-3">Win %</th>
                  <th className="px-4 py-3">Bat 1st Wins</th>
                  <th className="px-4 py-3">Chase Wins</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {teams.map((t) => (
                  <tr key={t.team} className="hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-medium text-white">{t.team}</td>
                    <td className="px-4 py-3 text-slate-300">{t.matches_played}</td>
                    <td className="px-4 py-3 text-slate-300">{t.wins}</td>
                    <td className="px-4 py-3 font-semibold text-amber-400">{t.win_pct}%</td>
                    <td className="px-4 py-3 text-slate-300">{t.bat_first_wins}</td>
                    <td className="px-4 py-3 text-slate-300">{t.chase_wins}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}