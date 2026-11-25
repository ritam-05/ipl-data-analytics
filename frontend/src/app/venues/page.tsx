"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

interface VenueRow {
  venue: string;
  total_matches: number;
  avg_first_innings_score: number;
  highest_first_innings_score: number;
  lowest_first_innings_score: number;
  bat_first_wins: number;
  chase_wins: number;
  chase_win_pct: number | null;
}

const SEASONS = Array.from({ length: 19 }, (_, i) => 2026 - i);
const DONUT_COLORS = ["#0284c7", "#1e3a8a"];

export default function VenuesPage() {
  const [season, setSeason] = useState<string>("all");
  const [venues, setVenues] = useState<VenueRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const param = season === "all" ? "?limit=40" : `?season=${season}&limit=40`;
    apiFetch<VenueRow[]>(`/api/analytics/venues${param}`)
      .then(setVenues)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [season]);

  const totalBatFirstWins = venues.reduce((sum, v) => sum + v.bat_first_wins, 0);
  const totalChaseWins = venues.reduce((sum, v) => sum + v.chase_wins, 0);

  const donutData = [
    { name: "Bat First Wins", value: totalBatFirstWins },
    { name: "Chase Wins", value: totalChaseWins },
  ];

  const topScoringVenues = [...venues]
    .sort((a, b) => b.avg_first_innings_score - a.avg_first_innings_score)
    .slice(0, 10);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Venue Analytics</h1>
          <p className="text-sm text-slate-400">
            Standardized stadium profiles, scoring averages, and chasing vs. defending splits.
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

      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-slate-400">Loading venue analytics...</div>
      ) : (
        <>
          {/* Top Row: Avg 1st Innings by Venue + Defending vs Chase Wins Grouped Bar */}
          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
              <h2 className="text-base font-semibold text-white">Avg 1st Innings by Venue</h2>
              <p className="mb-4 text-xs text-slate-400">Venue Avg 1st Innings by venue_name</p>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topScoringVenues}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="venue"
                      stroke="#94a3b8"
                      fontSize={10}
                      interval={0}
                      angle={-20}
                      textAnchor="end"
                      height={75}
                    />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 220]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: 8,
                      }}
                    />
                    <Bar
                      dataKey="avg_first_innings_score"
                      name="Avg 1st Innings"
                      fill="#0284c7"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
              <h2 className="text-base font-semibold text-white">Defending vs Chase Wins</h2>
              <p className="mb-4 text-xs text-slate-400">
                Venue Bat First Wins and Venue Chase Wins by venue_name
              </p>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={venues.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="venue"
                      stroke="#94a3b8"
                      fontSize={10}
                      interval={0}
                      angle={-20}
                      textAnchor="end"
                      height={75}
                    />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: 8,
                      }}
                    />
                    <Legend />
                    <Bar
                      dataKey="bat_first_wins"
                      name="Bat First Wins"
                      fill="#0284c7"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="chase_wins"
                      name="Chase Wins"
                      fill="#1e3a8a"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          {/* Bottom Section: Venues Table + Overall Defending vs Chase Donut */}
          <section className="grid gap-6 lg:grid-cols-12">
            <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60 lg:col-span-8">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-800 uppercase text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Venue</th>
                    <th className="px-4 py-3">Matches</th>
                    <th className="px-4 py-3">Highest</th>
                    <th className="px-4 py-3">Avg 1st Inn</th>
                    <th className="px-4 py-3">Chase Wins</th>
                    <th className="px-4 py-3">Lowest</th>
                    <th className="px-4 py-3">Bat First Wins</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {venues.map((v) => (
                    <tr key={v.venue} className="hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-medium text-white">{v.venue}</td>
                      <td className="px-4 py-3 text-slate-300">{v.total_matches}</td>
                      <td className="px-4 py-3 text-slate-300">{v.highest_first_innings_score}</td>
                      <td className="px-4 py-3 font-semibold text-amber-400">
                        {v.avg_first_innings_score}
                      </td>
                      <td className="px-4 py-3 font-semibold text-sky-400">{v.chase_wins}</td>
                      <td className="px-4 py-3 text-slate-300">{v.lowest_first_innings_score}</td>
                      <td className="px-4 py-3 text-slate-300">{v.bat_first_wins}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 lg:col-span-4">
              <h2 className="text-base font-semibold text-white">Defend vs Chase Wins</h2>
              <p className="mb-3 text-xs text-slate-400">Overall Bat First vs Chase split</p>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={donutData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={52}
                      outerRadius={80}
                      paddingAngle={3}
                    >
                      {donutData.map((entry, idx) => (
                        <Cell
                          key={entry.name}
                          fill={DONUT_COLORS[idx % DONUT_COLORS.length]}
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
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}