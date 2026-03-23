import Link from "next/link";
import { ArrowRight, Cpu, Database, TerminalSquare } from "lucide-react";
import { PanelCard } from "@/components/cards/panel-card";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteHeader } from "@/components/landing/site-header";

const architectures = [
  { name: "Llama 3", note: "Native execution layer for private model nodes." },
  { name: "Mistral", note: "Fast structured reasoning for lightweight control planes." },
  { name: "Phi-3", note: "Compact inference path for desktop orchestration." },
  { name: "Gemma", note: "Optional experimental model track for self-hosted labs." },
];

const environments = [
  { title: "Headless CLI", description: "Run command surfaces, workflows, and scripted automations from a graphite control rail.", icon: TerminalSquare },
  { title: "Native Desktop", description: "Operate local runtimes with low-latency telemetry, policy overlays, and execution lanes.", icon: Cpu },
  { title: "Knowledge Plane", description: "Attach retrieval context, document fragments, and workspace memory without leaving the command center.", icon: Database },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-graphite text-ink">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 py-10">
        <section className="grid gap-8 lg:grid-cols-[1.2fr_0.9fr]">
          <div className="panel flex flex-col justify-between gap-6 px-8 py-8">
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-signal">System status: online • v0.1.0</p>
              <h1 className="mt-4 max-w-3xl font-headline text-5xl font-black leading-none tracking-tight md:text-7xl">
                Local-First AI <span className="text-signal">Execution Platform.</span>
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-mutedInk">
                Self-hosted, multi-model AI coordination. Run powerful language models securely on your own hardware with precise modular control and zero telemetry drift.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href="/login" className="inline-flex items-center gap-2 border border-signal/40 bg-signal px-5 py-4 text-xs font-black uppercase tracking-[0.2em] text-black">
                Initialize Node <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#supported" className="border border-white/10 px-5 py-4 text-xs font-semibold uppercase tracking-[0.2em] text-mutedInk">
                Read Documentation
              </a>
            </div>
            <div className="signal-line panel terminal-glow relative bg-black/35 px-4 py-4 pl-6 text-xs text-mutedInk data-grid">
              <div className="space-y-2 font-mono">
                <p>&gt; boot: initializing node registry…</p>
                <p>&gt; sync: loaded llama-3 (gpu)</p>
                <p>&gt; success: coordination mesh active on port 8000</p>
              </div>
            </div>
          </div>
          <div className="panel relative overflow-hidden bg-black/20 p-8 data-grid">
            <div className="absolute inset-x-8 bottom-8 top-8 border border-white/5 bg-black/40" />
            <div className="absolute inset-x-12 bottom-12 top-12 border border-signal/10 bg-gradient-to-br from-signal/5 to-transparent" />
            <div className="relative flex h-full flex-col justify-end gap-4">
              <p className="text-[10px] uppercase tracking-[0.3em] text-signal">Execution Preview</p>
              <div className="space-y-3 font-mono text-sm text-mutedInk">
                <p>NODE: Initializing local registry…</p>
                <p>MODEL: Ready • Llama 3</p>
                <p>CHANNEL: CLI runtime mapped</p>
                <p>STATUS: Command center stable</p>
              </div>
            </div>
          </div>
        </section>

        <PanelCard eyebrow="Supported Architectures" title="Native execution layers for the local-first stack">
          <div id="supported" className="grid gap-4 lg:grid-cols-4">
            {architectures.map((item) => (
              <div key={item.name} className="border border-white/5 bg-black/25 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-signal">verified</p>
                <h3 className="mt-4 font-headline text-2xl font-black">{item.name}</h3>
                <p className="mt-3 text-sm leading-7 text-mutedInk">{item.note}</p>
              </div>
            ))}
          </div>
        </PanelCard>

        <section className="grid gap-4 lg:grid-cols-3">
          {environments.map(({ title, description, icon: Icon }) => (
            <PanelCard key={title} eyebrow="Execution Environments" title={title}>
              <div className="flex items-start gap-4">
                <div className="border border-signal/20 bg-signal/5 p-3 text-signal">
                  <Icon className="h-5 w-5" />
                </div>
                <p className="text-sm leading-7 text-mutedInk">{description}</p>
              </div>
            </PanelCard>
          ))}
        </section>

        <section className="panel flex flex-col items-center gap-6 px-6 py-16 text-center">
          <p className="text-[10px] uppercase tracking-[0.3em] text-signal">Establish your node</p>
          <h2 className="font-headline text-4xl font-black uppercase tracking-tight">Bring the control plane local.</h2>
          <p className="max-w-3xl text-sm leading-8 text-mutedInk">
            Launch the DreamAxis monorepo, attach a PostgreSQL + Redis stack, and pilot your first execution lane from a single command center.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/login" className="border border-signal/40 bg-signal px-5 py-4 text-xs font-black uppercase tracking-[0.2em] text-black">Open Operator Console</Link>
            <a href="https://github.com" className="border border-white/10 px-5 py-4 text-xs font-semibold uppercase tracking-[0.2em] text-mutedInk">Community</a>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
