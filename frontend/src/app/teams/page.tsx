"use client";

import { useEffect, useRef, useState } from "react";
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
import { Award, Flame, Sparkles, Target, Trophy, X, Zap } from "lucide-react";

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

interface TeamDetails {
  team: string;
  season: number | null;
  summary: {
    matches_played: number;
    wins: number;
    win_pct: number | null;
    bat_first_wins: number;
    chase_wins: number;
    highest_team_score: number | null;
    avg_team_score: number | null;
  };
  most_runs: {
    player_name: string;
    total_runs: number;
    strike_rate: number;
    batting_average: number | null;
  } | null;
  most_wickets: {
    player_name: string;
    total_wickets: number;
    economy_rate: number;
  } | null;
  best_batting_sr: {
    player_name: string;
    total_runs: number;
    balls_faced: number;
    strike_rate: number;
  } | null;
  best_bowling_sr: {
    player_name: string;
    total_wickets: number;
    bowling_strike_rate: number;
  } | null;
  best_economy: {
    player_name: string;
    total_wickets: number;
    overs: number;
    economy_rate: number;
  } | null;
  emerging_player: {
    player_name: string;
    debut_season: number;
    runs: number;
    strike_rate: number;
  } | null;
  top_batters: Array<{
    player_name: string;
    matches: number;
    total_runs: number;
    batting_average: number | null;
    strike_rate: number;
    highest_score: number;
  }>;
  top_bowlers: Array<{
    player_name: string;
    matches: number;
    total_wickets: number;
    overs: number;
    economy_rate: number;
    bowling_strike_rate: number | null;
  }>;
}

const SEASONS = Array.from({ length: 19 }, (_, i) => 2026 - i);

export default function TeamsPage() {
  const [season, setSeason] = useState<string>("all");
  const [teams, setTeams] = useState<TeamRow[]>([]);
  const [teamA, setTeamA] = useState("Mumbai Indians");
  const [teamB, setTeamB] = useState("Chennai Super Kings");
  const [h2h, setH2h] = useState<H2HResult | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [teamDetails, setTeamDetails] = useState<TeamDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const detailsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setLoading(true);
    const param = season === "all" ? "" : `?season=${season}`;
    apiFetch<TeamRow[]>(`/api/analytics/teams${param}`)
      .then((data) => {
        setTeams(data);
        if (selectedTeam && !data.some((t) => t.team === selectedTeam)) {
          setSelectedTeam(null);
          setTeamDetails(null);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [season, selectedTeam]);

  useEffect(() => {
    if (!teamA || !teamB || teamA === teamB) return;
    apiFetch<H2HResult>(
      `/api/analytics/teams/h2h?team_a=${encodeURIComponent(teamA)}&team_b=${encodeURIComponent(teamB)}`
    )
      .then(setH2h)
      .catch(() => setH2h(null));
  }, [teamA, teamB]);

  useEffect(() => {
    if (!selectedTeam) return;
    setDetailsLoading(true);
    setDetailsError(null);
    const seasonParam = season === "all" ? "" : `&season=${season}`;
    apiFetch<TeamDetails>(
      `/api/analytics/teams/details?team=${encodeURIComponent(selectedTeam)}${seasonParam}`
    )
      .then(setTeamDetails)
      .catch((err) => {
        setTeamDetails(null);
        setDetailsError(err instanceof Error ? err.message : "Failed to load franchise stats.");
      })
      .finally(() => setDetailsLoading(false));
  }, [selectedTeam, season]);

  function handleSelectTeam(teamName: string) {
    setSelectedTeam(teamName);
    setTimeout(() => {
      detailsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Team Analytics</h1>
          <p className="text-sm text-slate-400">
            Franchise win percentages, head-to-head rivalries, and click any franchise for a full deep dive.
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
                  <XAxis
                    dataKey="team"
                    stroke="#94a3b8"
                    fontSize={10}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                    height={70}
                  />
                  <YAxis stroke="#94a3b8" fontSize={12} unit="%" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="win_pct" name="Win %" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-200">Franchise Standings</h2>
              <span className="text-xs text-amber-400">Click any franchise row to inspect detailed stats</span>
            </div>
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
                {teams.map((t) => {
                  const isSelected = selectedTeam === t.team;
                  return (
                    <tr
                      key={t.team}
                      onClick={() => handleSelectTeam(t.team)}
                      className={`cursor-pointer transition ${
                        isSelected ? "bg-amber-500/15" : "hover:bg-slate-800/50"
                      }`}
                    >
                      <td className="px-4 py-3 font-medium text-white">
                        {t.team}
                        {isSelected && (
                          <span className="ml-2 rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-400">
                            Selected
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-300">{t.matches_played}</td>
                      <td className="px-4 py-3 text-slate-300">{t.wins}</td>
                      <td className="px-4 py-3 font-semibold text-amber-400">{t.win_pct}%</td>
                      <td className="px-4 py-3 text-slate-300">{t.bat_first_wins}</td>
                      <td className="px-4 py-3 text-slate-300">{t.chase_wins}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Franchise Deep-Dive Section */}
          {selectedTeam && (
            <section
              ref={detailsRef}
              className="space-y-6 rounded-2xl border border-amber-500/40 bg-slate-900/80 p-6 shadow-lg"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <Trophy className="h-5 w-5 text-amber-400" />
                    <h2 className="text-xl font-bold text-white">{selectedTeam}</h2>
                    <span className="rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
                      {season === "all" ? "All-Time (2008–2026)" : `IPL ${season}`}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    Franchise performance leaders and key metrics for the selected period.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setSelectedTeam(null);
                    setTeamDetails(null);
                    setDetailsError(null);
                  }}
                  className="rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                  aria-label="Close franchise details"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {detailsError ? (
                <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
                  {detailsError}
                </div>
              ) : detailsLoading || !teamDetails ? (
                <div className="py-10 text-center text-sm text-slate-400">
                  Loading {selectedTeam} stats...
                </div>
              ) : (
                <>
                  {/* Team KPI Strip */}
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                    <div className="rounded-xl bg-slate-950/70 p-4">
                      <p className="text-xs text-slate-400">Win %</p>
                      <p className="mt-1 text-2xl font-bold text-amber-400">
                        {teamDetails.summary.win_pct ?? 0}%
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-950/70 p-4">
                      <p className="text-xs text-slate-400">Matches / Wins</p>
                      <p className="mt-1 text-2xl font-bold text-white">
                        {teamDetails.summary.matches_played} / {teamDetails.summary.wins}
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-950/70 p-4">
                      <p className="text-xs text-slate-400">Bat 1st / Chase Wins</p>
                      <p className="mt-1 text-2xl font-bold text-sky-400">
                        {teamDetails.summary.bat_first_wins} / {teamDetails.summary.chase_wins}
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-950/70 p-4">
                      <p className="text-xs text-slate-400">Highest Score</p>
                      <p className="mt-1 text-2xl font-bold text-white">
                        {teamDetails.summary.highest_team_score ?? "—"}
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-950/70 p-4">
                      <p className="text-xs text-slate-400">Avg Team Score</p>
                      <p className="mt-1 text-2xl font-bold text-white">
                        {teamDetails.summary.avg_team_score ?? "—"}
                      </p>
                    </div>
                  </div>

                  {/* Key Award / Highlight Cards */}
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                        <Award className="h-4 w-4" />
                        Most Runs
                      </div>
                      <p className="mt-2 text-lg font-bold text-white">
                        {teamDetails.most_runs?.player_name ?? "—"}
                      </p>
                      <p className="text-xs text-slate-400">
                        {teamDetails.most_runs
                          ? `${teamDetails.most_runs.total_runs.toLocaleString()} runs • SR ${teamDetails.most_runs.strike_rate}`
                          : "No data"}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-400">
                        <Target className="h-4 w-4" />
                        Most Wickets
                      </div>
                      <p className="mt-2 text-lg font-bold text-white">
                        {teamDetails.most_wickets?.player_name ?? "—"}
                      </p>
                      <p className="text-xs text-slate-400">
                        {teamDetails.most_wickets
                          ? `${teamDetails.most_wickets.total_wickets} wickets • Econ ${teamDetails.most_wickets.economy_rate}`
                          : "No data"}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-orange-400">
                        <Flame className="h-4 w-4" />
                        Best Batting SR
                      </div>
                      <p className="mt-2 text-lg font-bold text-white">
                        {teamDetails.best_batting_sr?.player_name ?? "—"}
                      </p>
                      <p className="text-xs text-slate-400">
                        {teamDetails.best_batting_sr
                          ? `SR ${teamDetails.best_batting_sr.strike_rate} (${teamDetails.best_batting_sr.total_runs} runs off ${teamDetails.best_batting_sr.balls_faced} balls)`
                          : "No data"}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-violet-400">
                        <Zap className="h-4 w-4" />
                        Best Bowling SR
                      </div>
                      <p className="mt-2 text-lg font-bold text-white">
                        {teamDetails.best_bowling_sr?.player_name ?? "—"}
                      </p>
                      <p className="text-xs text-slate-400">
                        {teamDetails.best_bowling_sr
                          ? `SR ${teamDetails.best_bowling_sr.bowling_strike_rate} (${teamDetails.best_bowling_sr.total_wickets} wickets)`
                          : "No data"}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                        <Target className="h-4 w-4" />
                        Best Economy
                      </div>
                      <p className="mt-2 text-lg font-bold text-white">
                        {teamDetails.best_economy?.player_name ?? "—"}
                      </p>
                      <p className="text-xs text-slate-400">
                        {teamDetails.best_economy
                          ? `Econ ${teamDetails.best_economy.economy_rate} (${teamDetails.best_economy.overs} overs)`
                          : "No data"}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-pink-400">
                        <Sparkles className="h-4 w-4" />
                        Emerging / Debut Performer
                      </div>
                      <p className="mt-2 text-lg font-bold text-white">
                        {teamDetails.emerging_player?.player_name ?? "—"}
                      </p>
                      <p className="text-xs text-slate-400">
                        {teamDetails.emerging_player
                          ? `${teamDetails.emerging_player.runs} runs in debut IPL ${teamDetails.emerging_player.debut_season} (SR ${teamDetails.emerging_player.strike_rate})`
                          : "No debutant batter in this period"}
                      </p>
                    </div>
                  </div>

                  {/* Top 5 Batters & Bowlers Side-by-Side */}
                  <div className="grid gap-6 lg:grid-cols-2">
                    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
                      <div className="border-b border-slate-800 px-4 py-2.5 text-xs font-semibold text-amber-400">
                        Top 5 Batters
                      </div>
                      <table className="w-full text-left text-xs">
                        <thead className="border-b border-slate-800 text-slate-400">
                          <tr>
                            <th className="px-3 py-2">Player</th>
                            <th className="px-3 py-2">Runs</th>
                            <th className="px-3 py-2">Avg</th>
                            <th className="px-3 py-2">SR</th>
                            <th className="px-3 py-2">HS</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {teamDetails.top_batters.map((b) => (
                            <tr key={b.player_name}>
                              <td className="px-3 py-2 font-medium text-white">{b.player_name}</td>
                              <td className="px-3 py-2 font-semibold text-amber-400">{b.total_runs}</td>
                              <td className="px-3 py-2 text-slate-300">{b.batting_average ?? "—"}</td>
                              <td className="px-3 py-2 text-slate-300">{b.strike_rate}</td>
                              <td className="px-3 py-2 text-slate-300">{b.highest_score}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
                      <div className="border-b border-slate-800 px-4 py-2.5 text-xs font-semibold text-sky-400">
                        Top 5 Bowlers
                      </div>
                      <table className="w-full text-left text-xs">
                        <thead className="border-b border-slate-800 text-slate-400">
                          <tr>
                            <th className="px-3 py-2">Player</th>
                            <th className="px-3 py-2">Wkts</th>
                            <th className="px-3 py-2">Overs</th>
                            <th className="px-3 py-2">Econ</th>
                            <th className="px-3 py-2">SR</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {teamDetails.top_bowlers.map((bw) => (
                            <tr key={bw.player_name}>
                              <td className="px-3 py-2 font-medium text-white">{bw.player_name}</td>
                              <td className="px-3 py-2 font-semibold text-sky-400">{bw.total_wickets}</td>
                              <td className="px-3 py-2 text-slate-300">{bw.overs}</td>
                              <td className="px-3 py-2 text-slate-300">{bw.economy_rate}</td>
                              <td className="px-3 py-2 text-slate-300">{bw.bowling_strike_rate ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}