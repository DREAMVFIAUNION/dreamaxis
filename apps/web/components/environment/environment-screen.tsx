"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { DoctorCheckResult, Workspace } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { MetricCard } from "@/components/cards/metric-card";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

function fmtDate(value?: string | null) {
  if (!value) return "--";
  return new Date(value).toLocaleString();
}

function statusTone(status?: string | null) {
  if (status === "ready") return "text-emerald-300";
  if (status === "warn" || status === "degraded") return "text-amber-300";
  if (status === "blocked" || status === "missing") return "text-red-300";
  return "text-mutedInk";
}

function GuidanceStep({
  eyebrow,
  title,
  summary,
  href,
  linkLabel,
  tone = "neutral",
}: {
  eyebrow: string;
  title: string;
  summary: string;
  href?: string;
  linkLabel?: string;
  tone?: "neutral" | "warn" | "good";
}) {
  const toneClass =
    tone === "warn"
      ? "border-amber-300/25 bg-amber-500/10"
      : tone === "good"
        ? "border-emerald-400/25 bg-emerald-500/10"
        : "border-white/5 bg-black/20";
  return (
    <div className={`border px-4 py-4 ${toneClass}`}>
      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">{eyebrow}</p>
      <p className="mt-2 text-base font-semibold text-ink">{title}</p>
      <p className="mt-2 text-sm leading-7 text-mutedInk">{summary}</p>
      {href && linkLabel ? (
        <Link href={href} className="mt-3 inline-block text-xs font-semibold uppercase tracking-[0.18em] text-signal">
          {linkLabel}
        </Link>
      ) : null}
    </div>
  );
}

export function EnvironmentScreen() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [doctor, setDoctor] = useState<DoctorCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadDoctor(activeWorkspaceId?: string) {
    const token = getAuthToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getEnvironmentDoctor(token, activeWorkspaceId);
      setDoctor(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load environment doctor");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const token = getAuthToken();
    if (!token) return;
    (async () => {
      try {
        const workspaceRes = await apiClient.getWorkspaces(token);
        setWorkspaces(workspaceRes.data);
        const nextWorkspaceId = workspaceRes.data[0]?.id ?? "";
        setWorkspaceId(nextWorkspaceId);
        await loadDoctor(nextWorkspaceId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load workspaces");
      }
    })();
  }, []);

  const metrics = useMemo(() => {
    if (!doctor) return [];
    return [
      { label: "Machine Status", value: doctor.machine_summary.status.toUpperCase(), hint: "Core baseline readiness" },
      { label: "Missing Required", value: String(doctor.machine_summary.missing_required.length).padStart(2, "0"), hint: "Git / Node / package manager / Python" },
      { label: "Warnings", value: String(doctor.machine_summary.warnings.length).padStart(2, "0"), hint: "Optional enhancements to install" },
      { label: "Skill Coverage", value: `${doctor.skill_compatibility.ready ?? 0}/${doctor.skill_compatibility.total ?? 0}`, hint: "Skills fully ready on this machine" },
    ];
  }, [doctor]);

  const firstRunSteps = useMemo(() => {
    if (!doctor) return [];
    const hasMissingRequired = doctor.machine_summary.missing_required.length > 0;
    const hasRuntimes = doctor.runtimes.length > 0;
    const readySkills = doctor.skill_compatibility.ready ?? 0;
    return [
      hasMissingRequired
        ? {
            eyebrow: "Do first",
            title: "Fix required machine tools",
            summary:
              "Install every missing required tool on this machine before trusting a skill failure. Git, Node.js, pnpm/npm, and Python define the current desktop baseline.",
            href: "/environment",
            linkLabel: "Review machine baseline",
            tone: "warn" as const,
          }
        : {
            eyebrow: "Baseline ready",
            title: "Machine baseline is clear",
            summary:
              "Required local tools are present. Optional warnings can wait while you connect a provider and run a first execution.",
            href: "/settings/providers",
            linkLabel: "Open provider settings",
            tone: "good" as const,
          },
      !hasRuntimes
        ? {
            eyebrow: "Next",
            title: "Start at least one runtime host",
            summary:
              "The web shell is up, but no runtime has reported health yet. Start the CLI, Browser, or Desktop worker so the operator surfaces can execute real work.",
            href: "/runtime",
            linkLabel: "Inspect runtime registry",
            tone: "warn" as const,
          }
        : {
            eyebrow: "Connected",
            title: "Runtime hosts are reporting in",
            summary:
              "A runtime has checked in. Next, wire a provider connection and confirm one prompt or runtime-backed skill completes end to end.",
            href: "/runtime",
            linkLabel: "Open runtime audit",
            tone: "good" as const,
          },
      {
        eyebrow: readySkills > 0 ? "Recommended flow" : "Needs setup",
        title: readySkills > 0 ? "Run one skill and inspect the audit trail" : "Unblock skill coverage before first use",
        summary:
          readySkills > 0
            ? "Use `/skills` or `/chat/local-demo`, then confirm the resulting execution appears in `/runtime` with timeline, artifacts, and summaries."
            : "Current compatibility shows blocked skills. Use the machine baseline and runtime snapshots below to clear blockers before expecting a stable first run.",
        href: readySkills > 0 ? "/skills" : "/runtime",
        linkLabel: readySkills > 0 ? "Open skills" : "Open runtime troubleshooting",
        tone: readySkills > 0 ? ("neutral" as const) : ("warn" as const),
      },
      {
        eyebrow: "Reference",
        title: "Follow the seeded local path",
        summary:
          "The preferred first-run path remains provider setup -> one CLI or Browser skill -> knowledge sync -> `/chat/local-demo` -> `/runtime` confirmation.",
        href: "/chat/local-demo",
        linkLabel: "Open local demo chat",
        tone: "neutral" as const,
      },
    ];
  }, [doctor]);

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <PanelCard eyebrow="Desktop Standard" title="Environment doctor">
          <div className="grid gap-4 xl:grid-cols-[1fr_auto_auto] xl:items-end">
            <label className="flex min-w-72 flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Workspace
              <select
                value={workspaceId}
                onChange={async (event) => {
                  const nextWorkspaceId = event.target.value;
                  setWorkspaceId(nextWorkspaceId);
                  await loadDoctor(nextWorkspaceId);
                }}
                className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
              >
                {workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap gap-4 text-[10px] uppercase tracking-[0.2em] text-mutedInk">
              <span>{doctor?.profile.name ?? "Loading profile"}</span>
              <span>{loading ? "refreshing" : "live doctor"}</span>
            </div>
          </div>
          {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
        </PanelCard>

        {!doctor && loading ? (
          <PanelCard eyebrow="First-run guidance" title="Collecting machine baseline">
            <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm leading-7 text-mutedInk">
              DreamAxis is gathering machine, workspace, and runtime readiness before suggesting a first-run path.
            </div>
          </PanelCard>
        ) : null}

        {doctor ? (
          <PanelCard eyebrow="First-run guidance" title="Recommended next actions">
            <div className="grid gap-4 xl:grid-cols-2">
              {firstRunSteps.map((step) => (
                <GuidanceStep key={step.title} {...step} />
              ))}
            </div>
          </PanelCard>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <MetricCard key={metric.label} {...metric} />
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <PanelCard eyebrow="Machine baseline" title="Core + optional capabilities">
            <div className="space-y-3">
              {doctor?.machine_capabilities.map((capability) => (
                <div key={capability.name} className="border border-white/5 bg-black/20 px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-ink">{capability.name}</p>
                    <span className={`text-[10px] uppercase tracking-[0.18em] ${statusTone(capability.status)}`}>{capability.status}</span>
                  </div>
                  <p className="mt-2 text-xs text-mutedInk">{capability.version ?? capability.message ?? "--"}</p>
                  {capability.install_hint ? <p className="mt-2 text-xs text-mutedInk">Fix: {capability.install_hint}</p> : null}
                </div>
              ))}
            </div>
          </PanelCard>

          <PanelCard eyebrow="Workspace readiness" title={doctor?.workspace?.workspace_name ?? "Workspace"}>
            <div className="space-y-3">
              <div className="border border-white/5 bg-black/20 px-4 py-4">
                <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Root path</p>
                <p className="mt-2 break-all text-sm text-ink">{doctor?.workspace?.root_path ?? "--"}</p>
              </div>
              {doctor?.workspace?.capabilities.map((capability) => (
                <div key={capability.name} className="border border-white/5 bg-black/20 px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-ink">{capability.name}</p>
                    <span className={`text-[10px] uppercase tracking-[0.18em] ${statusTone(capability.status)}`}>{capability.status}</span>
                  </div>
                  <p className="mt-2 text-xs text-mutedInk">{capability.message ?? "--"}</p>
                </div>
              ))}
            </div>
          </PanelCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <PanelCard eyebrow="Skill coverage" title="Compatibility summary">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="border border-white/5 bg-black/20 px-4 py-4">
                <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Ready</p>
                <p className="mt-2 text-2xl font-black text-ink">{doctor?.skill_compatibility.ready ?? 0}</p>
              </div>
              <div className="border border-white/5 bg-black/20 px-4 py-4">
                <p className="text-[10px] uppercase tracking-[0.18em] text-amber-300">Warn</p>
                <p className="mt-2 text-2xl font-black text-ink">{doctor?.skill_compatibility.warn ?? 0}</p>
              </div>
              <div className="border border-white/5 bg-black/20 px-4 py-4">
                <p className="text-[10px] uppercase tracking-[0.18em] text-red-300">Blocked</p>
                <p className="mt-2 text-2xl font-black text-ink">{doctor?.skill_compatibility.blocked ?? 0}</p>
              </div>
            </div>
          </PanelCard>

          <PanelCard eyebrow="Install guidance" title="How to fix missing items">
            <div className="space-y-3">
              {doctor?.install_guidance.map((item) => (
                <div key={item} className="border border-white/5 bg-black/20 px-4 py-4 text-sm text-mutedInk">
                  {item}
                </div>
              ))}
              {doctor && !doctor.install_guidance.length ? (
                <div className="border border-emerald-400/20 bg-emerald-500/10 px-4 py-4 text-sm leading-7 text-emerald-100">
                  No fixes required. This machine satisfies the current workspace baseline. Continue with provider setup, one skill run, then confirm the audit trail in <span className="font-semibold text-white">/runtime</span>.
                </div>
              ) : null}
            </div>
          </PanelCard>
        </section>

        <PanelCard eyebrow="Runtime hosts" title="Runtime doctor snapshots">
          <div className="overflow-hidden border border-white/5 bg-black/20">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="border-b border-white/5 text-[10px] uppercase tracking-[0.3em] text-mutedInk">
                <tr>
                  <th className="px-4 py-4">Runtime</th>
                  <th className="px-4 py-4">Type</th>
                  <th className="px-4 py-4">Status</th>
                  <th className="px-4 py-4">Doctor</th>
                  <th className="px-4 py-4">Checked</th>
                </tr>
              </thead>
              <tbody>
                {doctor?.runtimes.map((runtime) => (
                  <tr key={runtime.runtime_id} className="border-b border-white/5 last:border-b-0">
                    <td className="px-4 py-4 font-semibold text-ink">{runtime.runtime_name}</td>
                    <td className="px-4 py-4 text-mutedInk">{runtime.runtime_type}</td>
                    <td className="px-4 py-4 text-mutedInk">{runtime.status}</td>
                    <td className={`px-4 py-4 ${statusTone(runtime.doctor_status)}`}>{runtime.doctor_status ?? "--"}</td>
                    <td className="px-4 py-4 text-mutedInk">{fmtDate(runtime.last_capability_check_at)}</td>
                  </tr>
                ))}
                {!doctor?.runtimes.length ? (
                  <tr>
                    <td className="px-4 py-6 text-mutedInk" colSpan={5}>
                      No runtime hosts have reported environment snapshots yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </PanelCard>
      </div>
    </AppShell>
  );
}
