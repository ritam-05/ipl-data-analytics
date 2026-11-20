import { supabase } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:7860";

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  requireAuth = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (requireAuth) {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.access_token) {
      throw new Error("Please sign in to access this feature.");
    }
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `API error (${res.status})`);
  }

  return res.json();
}