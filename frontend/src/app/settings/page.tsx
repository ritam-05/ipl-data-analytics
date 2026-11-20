"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { Settings, Save } from "lucide-react";

interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  favourite_team: string | null;
  favourite_player: string | null;
}

const IPL_TEAMS = [
  "Chennai Super Kings",
  "Mumbai Indians",
  "Royal Challengers Bengaluru",
  "Kolkata Knight Riders",
  "Delhi Capitals",
  "Punjab Kings",
  "Rajasthan Royals",
  "Sunrisers Hyderabad",
  "Gujarat Titans",
  "Lucknow Super Giants",
];

export default function SettingsPage() {
  const [isAuthed, setIsAuthed] = useState<boolean | null>(null);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [favouriteTeam, setFavouriteTeam] = useState("");
  const [favouritePlayer, setFavouritePlayer] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      const authed = Boolean(data.session);
      setIsAuthed(authed);
      if (authed) {
        apiFetch<UserProfile>("/api/profile", {}, true)
          .then((p) => {
            setEmail(p.email || "");
            setDisplayName(p.display_name || "");
            setFavouriteTeam(p.favourite_team || "");
            setFavouritePlayer(p.favourite_player || "");
          })
          .catch((err) => setError(err.message));
      }
    });
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);

    try {
      await apiFetch(
        "/api/profile",
        {
          method: "PUT",
          body: JSON.stringify({
            display_name: displayName || null,
            favourite_team: favouriteTeam || null,
            favourite_player: favouritePlayer || null,
          }),
        },
        true
      );
      setMessage("Profile preferences saved! Your AI Assistant will now personalize responses.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save preferences.");
    } finally {
      setSaving(false);
    }
  }

  if (isAuthed === null) {
    return <div className="py-16 text-center text-sm text-slate-400">Loading settings...</div>;
  }

  if (!isAuthed) {
    return (
      <div className="mx-auto mt-12 max-w-lg rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-center">
        <Settings className="mx-auto h-10 w-10 text-amber-400" />
        <h1 className="mt-4 text-xl font-bold text-white">Sign in to manage preferences</h1>
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
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Profile &amp; AI Preferences</h1>
        <p className="text-sm text-slate-400">
          Customize your favourite IPL franchise and player for personalized AI analysis.
        </p>
      </div>

      <form
        onSubmit={handleSave}
        className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6"
      >
        <div>
          <label className="block text-xs font-medium text-slate-400">Account Email</label>
          <input
            type="text"
            value={email}
            disabled
            className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-400"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300">Display Name</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g., Ritam"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-amber-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300">Favourite IPL Team</label>
          <select
            value={favouriteTeam}
            onChange={(e) => setFavouriteTeam(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-amber-500 focus:outline-none"
          >
            <option value="">Select a franchise...</option>
            {IPL_TEAMS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300">Favourite Player</label>
          <input
            type="text"
            value={favouritePlayer}
            onChange={(e) => setFavouritePlayer(e.target.value)}
            placeholder="e.g., Virat Kohli, Jasprit Bumrah"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-amber-500 focus:outline-none"
          />
        </div>

        {error && <p className="rounded-lg bg-red-500/10 p-3 text-xs text-red-400">{error}</p>}
        {message && (
          <p className="rounded-lg bg-emerald-500/10 p-3 text-xs text-emerald-400">{message}</p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="flex items-center gap-2 rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {saving ? "Saving..." : "Save Preferences"}
        </button>
      </form>
    </div>
  );
}