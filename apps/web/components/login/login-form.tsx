"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/brand/brand-logo";
import { apiClient } from "@/lib/api";
import { setAuthToken, setStoredAppConfig, setStoredUser } from "@/lib/auth";

export function LoginForm({ next = "/dashboard" }: { next?: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("demo@dreamaxis.dev");
  const [password, setPassword] = useState("dreamaxis");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [authMode, setAuthMode] = useState<"loading" | "local_open" | "password">("loading");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const config = await apiClient.getAppConfig();
        setStoredAppConfig(config.data);
        if (!active) return;
        if (config.data.auth_mode === "local_open") {
          setAuthMode("local_open");
          const response = await apiClient.bootstrapAuth();
          if (!active) return;
          setAuthToken(response.data.access_token);
          setStoredUser(response.data.user);
          router.replace(next);
          return;
        }
        setAuthMode("password");
      } catch {
        if (active) setAuthMode("password");
      }
    })();

    return () => {
      active = false;
    };
  }, [next, router]);

  return (
    <div className="panel mx-auto flex w-full max-w-md flex-col gap-6 px-8 py-8">
      <BrandLogo />
      <div>
        <p className="text-[10px] uppercase tracking-[0.3em] text-signal">Command Center Access</p>
        <h1 className="mt-2 font-headline text-4xl font-black uppercase tracking-tight">Operator Login</h1>
        <p className="mt-4 text-sm leading-7 text-mutedInk">
          {authMode === "local_open"
            ? "Local-open mode is enabled. Bootstrapping your operator shell..."
            : "Use the seeded local demo identity to enter the DreamAxis runtime shell."}
        </p>
      </div>
      <form
        className="flex flex-col gap-4"
        onSubmit={async (event) => {
          event.preventDefault();
          setPending(true);
          setError(null);
          try {
            const response = await apiClient.login(email, password);
            setAuthToken(response.data.access_token);
            setStoredUser(response.data.user);
            router.replace(next);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
          } finally {
            setPending(false);
          }
        }}
      >
        <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.24em] text-mutedInk">
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} className="border border-white/10 bg-black/25 px-4 py-4 text-sm tracking-normal text-ink outline-none focus:border-signal/40" />
        </label>
        <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.24em] text-mutedInk">
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="border border-white/10 bg-black/25 px-4 py-4 text-sm tracking-normal text-ink outline-none focus:border-signal/40" />
        </label>
        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        <button disabled={pending || authMode === "local_open"} className="border border-signal/40 bg-signal px-5 py-4 text-xs font-black uppercase tracking-[0.2em] text-black disabled:opacity-50">
          {pending ? "Connecting..." : authMode === "local_open" ? "No Login Required" : "Enter Command Center"}
        </button>
      </form>
      <div className="border border-white/5 bg-black/25 px-4 py-4 text-xs leading-6 text-mutedInk">
        <p className="uppercase tracking-[0.24em] text-signal">Demo seed</p>
        <p className="mt-2">Email: demo@dreamaxis.dev</p>
        <p>Password: dreamaxis</p>
      </div>
    </div>
  );
}
