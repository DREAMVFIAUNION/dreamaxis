"use client";

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
              {doctor && !doctor.install_guidance.length ? <p className="text-sm text-mutedInk">No fixes required. This machine satisfies the current workspace baseline.</p> : null}
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
