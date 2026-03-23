"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { getAuthToken, setAuthToken, setStoredAppConfig, setStoredUser } from "@/lib/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;

    (async () => {
      const token = getAuthToken();
      if (token) {
        if (active) setReady(true);
        return;
      }

      try {
        const config = await apiClient.getAppConfig();
        setStoredAppConfig(config.data);
        if (config.data.auth_mode === "local_open") {
          const session = await apiClient.bootstrapAuth();
          setAuthToken(session.data.access_token);
          setStoredUser(session.data.user);
          if (active) setReady(true);
          return;
        }
      } catch {
        // fall through to login route
      }

      if (active) {
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      }
    })();

    return () => {
      active = false;
    };
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-graphite text-sm uppercase tracking-[0.3em] text-signal">
        Validating session...
      </div>
    );
  }

  return <>{children}</>;
}
