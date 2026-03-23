import Link from "next/link";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";

export function ModulePlaceholder({ title, copy }: { title: string; copy: string }) {
  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <PanelCard eyebrow="Reserved Module" title={title}>
          <p className="max-w-2xl text-sm leading-7 text-mutedInk">{copy}</p>
          <div className="mt-6 flex gap-3">
            <Link href="/dashboard" className="border border-signal/40 bg-signal px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-black">
              Return to Dashboard
            </Link>
            <Link href="/chat/local-demo" className="border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-mutedInk">
              Open Console
            </Link>
          </div>
        </PanelCard>
      </div>
    </AppShell>
  );
}
