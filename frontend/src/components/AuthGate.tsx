"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

interface AuthGateProps {
  children: React.ReactNode;
}

export default function AuthGate({ children }: AuthGateProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  const isLoginRoute = pathname === "/login";

  useEffect(() => {
    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      const hasSession = Boolean(data.session);
      setAuthenticated(hasSession);
      setChecking(false);

      if (!hasSession && !isLoginRoute) {
        router.replace("/login");
      } else if (hasSession && isLoginRoute) {
        router.replace("/");
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!active) return;
      const hasSession = Boolean(session);
      setAuthenticated(hasSession);
      setChecking(false);

      if (!hasSession && !isLoginRoute) {
        router.replace("/login");
      } else if (hasSession && isLoginRoute) {
        router.replace("/");
      }
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [isLoginRoute, router]);

  if (isLoginRoute) {
    return <>{children}</>;
  }

  if (checking || !authenticated) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-sm text-slate-400">
        Verifying Supabase session...
      </div>
    );
  }

  return <>{children}</>;
}