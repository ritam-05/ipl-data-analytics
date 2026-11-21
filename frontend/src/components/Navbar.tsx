"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import {
  Activity,
  Bot,
  BarChart3,
  Users,
  MapPin,
  Trophy,
  Bookmark,
  Settings,
  LogOut,
  LogIn,
} from "lucide-react";

const NAV_LINKS = [
  { href: "/", label: "Overview", icon: Activity },
  { href: "/players", label: "Players", icon: Users },
  { href: "/teams", label: "Teams", icon: Trophy },
  { href: "/venues", label: "Venues", icon: MapPin },
  { href: "/seasons", label: "Seasons", icon: BarChart3 },
  { href: "/assistant", label: "cricketmama.exe", icon: Bot },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setUserEmail(data.user?.email ?? null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUserEmail(session?.user?.email ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link
          href={userEmail ? "/" : "/login"}
          className="flex items-center gap-2 text-lg font-bold tracking-tight text-white"
        >
          <span className="inline-flex h-8 items-center justify-center rounded-lg bg-amber-500 px-2 text-sm font-black text-slate-950">
            Know
          </span>
          <span>IPL</span>
        </Link>

        {userEmail && (
          <nav className="hidden items-center gap-1 lg:flex">
            {NAV_LINKS.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition ${
                    active
                      ? "bg-amber-500/15 text-amber-400"
                      : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              );
            })}
          </nav>
        )}

        <div className="flex items-center gap-3">
          {userEmail ? (
            <>
              <span className="hidden text-xs text-slate-400 xl:inline">{userEmail}</span>
              <button
                onClick={handleSignOut}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800"
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign Out
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-amber-400"
            >
              <LogIn className="h-3.5 w-3.5" />
              Sign In
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}