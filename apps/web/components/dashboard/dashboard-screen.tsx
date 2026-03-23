"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell/app-shell";
import { MetricCard } from "@/components/cards/metric-card";
import { PanelCard } from "@/components/cards/panel-card";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";
import type { Conversation, DoctorCheckResult, KnowledgeDocument, ProviderConnection, RuntimeExecution, SkillDefinition, Workspace } from "@dreamaxis/client";

function fmtDate(value?: string | null) {
  if (!value) return "--";
  return new Date(value).toLocaleString();
}

export function DashboardScreen() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeDocument[]>([]);
  const [skills, setSkills] = useState<SkillDefinition[]>([]);
  const [runtime, setRuntime] = useState<RuntimeExecution[]>([]);
  const [connections, setConnections] = useState<ProviderConnection[]>([]);
  const [doctor, setDoctor] = useState<DoctorCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) return;

    (async () => {
      try {
        const workspaceRes = await apiClient.getWorkspaces(token);
        const workspaceList = workspaceRes.data;
        setWorkspaces(workspaceList);

        const primaryWorkspaceId = workspaceList[0]?.id;
        const [conversationRes, knowledgeRes, skillRes, runtimeRes, connectionRes] = await Promise.all([
          apiClient.getConversations(token, primaryWorkspaceId),
          apiClient.getKnowledgeDocuments(token, primaryWorkspaceId),
          apiClient.getSkills(token, primaryWorkspaceId),
          apiClient.getRuntimeExecutions(token, primaryWorkspaceId ? { workspace_id: primaryWorkspaceId } : undefined),
          apiClient.getProviderConnections(token),
        ]);

        setConversations(conversationRes.data);
        setKnowledge(knowledgeRes.data);
        setSkills(skillRes.data);
        setRuntime(runtimeRes.data);
        setConnections(connectionRes.data);
        if (primaryWorkspaceId) {
          const doctorRes = await apiClient.getEnvironmentDoctor(token, primaryWorkspaceId);
          setDoctor(doctorRes.data);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      }
    })();
  }, []);

  const metrics = useMemo(
    () => [
      { label: "Active Workspaces", value: String(workspaces.length).padStart(2, "0"), hint: "Workspace shells online" },
      { label: "Knowledge Docs", value: String(knowledge.length).padStart(2, "0"), hint: "Uploaded & indexed files" },
      { label: "Skills Online", value: String(skills.filter((skill) => skill.enabled).length).padStart(2, "0"), hint: "Prompt registry entries" },
      { label: "Active Connections", value: String(connections.filter((item) => item.is_enabled).length).padStart(2, "0"), hint: "User-managed API endpoints" },
      { label: "Synced Models", value: String(connections.reduce((sum, item) => sum + item.models.length, 0)).padStart(2, "0"), hint: "Discovered + manual models" },
      { label: "Failed Checks", value: String(connections.filter((item) => item.status === "error").length).padStart(2, "0"), hint: "Review provider health" },
      { label: "Conversation Lanes", value: String(conversations.length).padStart(2, "0"), hint: "Operator sessions" },
      { label: "Failed Runs", value: String(runtime.filter((item) => item.status === "failed").length).padStart(2, "0"), hint: "Review execution errors" },
      { label: "Missing Tools", value: String(doctor?.machine_summary.missing_required.length ?? 0).padStart(2, "0"), hint: "Baseline gaps detected" },
      { label: "Degraded Runtimes", value: String(doctor?.runtimes.filter((item) => item.doctor_status && item.doctor_status !== "ready").length ?? 0).padStart(2, "0"), hint: "Doctor reported warnings" },
    ],
    [connections, conversations.length, doctor, knowledge.length, runtime, skills, workspaces.length],
  );

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="panel flex flex-col gap-3 px-6 py-6">
          <p className="text-[10px] uppercase tracking-[0.3em] text-signal">System Intelligence</p>
          <h1 className="font-headline text-5xl font-black uppercase tracking-tight">Operational Overview</h1>
          <p className="text-sm uppercase tracking-[0.24em] text-mutedInk">
            API-key self-service is live. Connections, models, skills, and runtime now share one OpenAI-compatible path.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {metrics.map((metric) => (
            <MetricCard key={metric.label} {...metric} />
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
          <PanelCard eyebrow="Workspace mesh" title="Knowledge + connection state">
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            <div className="overflow-hidden border border-white/5 bg-black/20">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="border-b border-white/5 text-[10px] uppercase tracking-[0.3em] text-mutedInk">
                  <tr>
                    <th className="px-4 py-4">Connection</th>
                    <th className="px-4 py-4">Status</th>
                    <th className="px-4 py-4">Default model</th>
                    <th className="px-4 py-4">Models</th>
                  </tr>
                </thead>
                <tbody>
                  {connections.slice(0, 6).map((connection) => (
                    <tr key={connection.id} className="border-b border-white/5 last:border-b-0">
                      <td className="px-4 py-4 font-semibold text-ink">{connection.name}</td>
                      <td className="px-4 py-4 text-mutedInk">{connection.status}</td>
                      <td className="px-4 py-4 text-mutedInk">{connection.default_model_name ?? "--"}</td>
                      <td className="px-4 py-4 text-mutedInk">{connection.models.length}</td>
                    </tr>
                  ))}
                  {!connections.length ? (
                    <tr>
                      <td className="px-4 py-6 text-mutedInk" colSpan={4}>
                        No provider connections yet. Add one from Provider Settings to start streaming any compatible model.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </PanelCard>

          <div className="flex flex-col gap-6">
            <PanelCard eyebrow="Recent runtime" title="Execution lanes">
              <div className="flex flex-col gap-3">
                {runtime.slice(0, 5).map((execution) => (
                  <div key={execution.id} className="border border-white/5 bg-black/25 px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-semibold text-ink">
                        {execution.source.toUpperCase()} / {execution.status}
                      </p>
                      <span className="text-[10px] uppercase tracking-[0.2em] text-signal">{execution.total_tokens} tokens</span>
                    </div>
                    <p className="mt-2 text-xs leading-6 text-mutedInk">{execution.prompt_preview ?? "No prompt preview"}</p>
                    <p className="mt-2 text-xs text-mutedInk">
                      {execution.provider_connection_name ?? "No connection"} / {execution.resolved_model_name ?? "--"}
                    </p>
                    <p className="mt-2 text-[10px] uppercase tracking-[0.2em] text-mutedInk">{fmtDate(execution.created_at)}</p>
                  </div>
                ))}
                {!runtime.length ? <p className="text-sm text-mutedInk">No runtime executions yet.</p> : null}
              </div>
            </PanelCard>

            <PanelCard eyebrow="Navigation" title="Primary actions">
              <div className="grid gap-3 md:grid-cols-2">
                <Link href="/settings/providers" className="border border-white/10 bg-white/[0.03] px-4 py-4 text-sm font-semibold text-ink transition hover:border-signal/30">Provider Settings</Link>
                <Link href="/knowledge" className="border border-white/10 bg-white/[0.03] px-4 py-4 text-sm font-semibold text-ink transition hover:border-signal/30">Open Knowledge</Link>
                <Link href="/skills" className="border border-white/10 bg-white/[0.03] px-4 py-4 text-sm font-semibold text-ink transition hover:border-signal/30">Open Skills</Link>
                <Link href="/runtime" className="border border-white/10 bg-white/[0.03] px-4 py-4 text-sm font-semibold text-ink transition hover:border-signal/30">Open Runtime</Link>
                <Link href="/environment" className="border border-white/10 bg-white/[0.03] px-4 py-4 text-sm font-semibold text-ink transition hover:border-signal/30">Open Doctor</Link>
                <Link href={conversations[0] ? `/chat/${conversations[0].id}` : "/chat/local-demo"} className="border border-signal/40 bg-signal px-4 py-4 text-sm font-black uppercase tracking-[0.18em] text-black">Launch Console</Link>
              </div>
            </PanelCard>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
