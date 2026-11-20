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

interface VenueRow {
  venue: string;
  total_matches: number;
  avg_first_innings_score: number;
  highest_first_innings_score: number;
  lowest_first_innings_score: number;
  bat_first_wins: number;
  chase_wins: number;
  chase_win_pct: number;
}

export default function VenuesPage() {
  const [minMatches, setMinMatches] = useState(15);
  const [venues, setVenues] = useState<VenueRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    apiFetch<VenueRow[]>(`/api/analytics/venues?min_matches=${minMatches}&limit=25`)
      .then(setVenues)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [minMatches]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Venue Analytics</h1>
          <p className="text-sm text-slate-400">
            Average 1st innings scores, scoring extremes, and chasing advantage across IPL stadiums.
          </p>
        </div>

        <select
          value={minMatches}
          onChange={(e) => setMinMatches(Number(e.target.value))}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
        >
          <option value={5}>Min 5 Matches</option>
          <option value={15}>Min 15 Matches</option>
          <option value={30}>Min 30 Matches</option>
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
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="mb-4 text-sm font-semibold text-slate-300">
              Bat First Wins vs. Chase Wins (Top 10 Venues by Matches)
            </h2>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={venues.slice(0, 10)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="venue" stroke="#94a3b8" fontSize={10} interval={0} angle={-18} textAnchor="end" height={75} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: 8 }} />
                  <Legend />
                  <Bar dataKey="bat_first_wins" name="Bat First Wins" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="chase_wins" name="Chase Wins" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-4 py-3">Venue</th>
                  <th className="px-4 py-3">Matches</th>
                  <th className="px-4 py-3">Avg 1st Inn</th>
                  <th className="px-4 py-3">Highest</th>
                  <th className="px-4 py-3">Lowest</th>
                  <th className="px-4 py-3">Chase Win %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {venues.map((v) => (
                  <tr key={v.venue} className="hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-medium text-white">{v.venue}</td>
                    <td className="px-4 py-3 text-slate-300">{v.total_matches}</td>
                    <td className="px-4 py-3 font-semibold text-amber-400">{v.avg_first_innings_score}</td>
                    <td className="px-4 py-3 text-slate-300">{v.highest_first_innings_score}</td>
                    <td className="px-4 py-3 text-slate-300">{v.lowest_first_innings_score}</td>
                    <td className="px-4 py-3 font-semibold text-sky-400">{v.chase_win_pct}%</td>
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