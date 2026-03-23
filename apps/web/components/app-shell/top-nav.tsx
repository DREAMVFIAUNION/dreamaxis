"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, LogOut, Search } from "lucide-react";
import { clearAuthToken } from "@/lib/auth";
import { BrandLogo } from "@/components/brand/brand-logo";

export function TopNav() {
  const router = useRouter();

  return (
    <header className="flex h-20 items-center justify-between border-b border-white/5 bg-black/20 px-6">
      <div className="flex items-center gap-6">
        <BrandLogo className="lg:hidden" />
        <div className="hidden items-center gap-2 border border-white/5 bg-white/[0.02] px-4 py-3 text-xs uppercase tracking-[0.2em] text-mutedInk md:flex">
          <Search className="h-4 w-4 text-signal" />
          <span>Knowledge / Runtime Search</span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Link href="/settings/providers" className="border border-white/10 bg-white/[0.03] px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-mutedInk transition hover:text-ink">
          Connections
        </Link>
        <button className="border border-white/10 bg-white/[0.03] p-3 text-mutedInk transition hover:text-ink">
          <Bell className="h-4 w-4" />
        </button>
        <button
          onClick={() => {
            clearAuthToken();
            router.push("/login");
          }}
          className="inline-flex items-center gap-2 border border-signal/30 bg-signal/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-signal transition hover:bg-signal/20"
        >
          <LogOut className="h-4 w-4" />
          Exit
        </button>
        <Link href="/chat/local-demo" className="border border-signal/40 bg-signal px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-black">
          Execute
        </Link>
      </div>
    </header>
  );
}
