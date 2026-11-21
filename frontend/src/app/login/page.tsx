"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      if (isSignUp) {
        const { error: signUpErr } = await supabase.auth.signUp({ email, password });
        if (signUpErr) throw signUpErr;
        setMessage(
          "Account created! Check your email to confirm, or sign in if email confirmation is disabled."
        );
      } else {
        const { error: signInErr } = await supabase.auth.signInWithPassword({ email, password });
        if (signInErr) throw signInErr;
        router.push("/");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto mt-12 max-w-md rounded-2xl border border-slate-800 bg-slate-900/70 p-8 shadow-xl">
      <h1 className="text-2xl font-bold text-white">
        {isSignUp ? "Create your account" : "Sign in to Know IPL"}
      </h1>
      <p className="mt-1 text-sm text-slate-400">
        Access personalized AI analytics, chat history, and saved charts.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-300">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-amber-500 focus:outline-none"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300">Password</label>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-amber-500 focus:outline-none"
            placeholder="••••••••"
          />
        </div>

        {error && <p className="rounded-lg bg-red-500/10 p-3 text-xs text-red-400">{error}</p>}
        {message && (
          <p className="rounded-lg bg-emerald-500/10 p-3 text-xs text-emerald-400">{message}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-amber-500 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50"
        >
          {loading ? "Please wait..." : isSignUp ? "Sign Up" : "Sign In"}
        </button>
      </form>

      <button
        onClick={() => {
          setIsSignUp(!isSignUp);
          setError(null);
          setMessage(null);
        }}
        className="mt-4 w-full text-center text-xs text-slate-400 hover:text-amber-400"
      >
        {isSignUp ? "Already have an account? Sign in" : "Need an account? Sign up"}
      </button>
    </div>
  );
}