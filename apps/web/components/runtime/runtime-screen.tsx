"use client";

import { useEffect, useMemo, useState } from "react";
import type { RuntimeExecution, RuntimeHost, RuntimeSession, Workspace } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

function fmtDate(value?: string | null) {
  if (!value) return "--";
  return new Date(value).toLocaleString();
}

function trimBlock(value?: string | null) {
  return value?.trim() || "--";
}

function readRuntimeEnvironment(runtime: RuntimeHost) {
  const environment = runtime.capabilities_json && typeof runtime.capabilities_json === "object"
    ? (runtime.capabilities_json.environment as Record<string, unknown> | undefined)
    : undefined;
  return environment && typeof environment === "object" ? environment : null;
}

function renderArtifact(artifact: Record<string, unknown>, index: number) {
  const dataUrl = typeof artifact.data_url === "string" ? artifact.data_url : null;
  if (dataUrl) {
    return <img key={index} src={dataUrl} alt="runtime artifact" className="mt-3 w-full border border-white/5" />;
  }
  return (
    <pre key={index} className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-ink">
      {JSON.stringify(artifact, null, 2)}
    </pre>
  );
}

export function RuntimeScreen() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [runtimeFilter, setRuntimeFilter] = useState<string>("");
  const [runtimes, setRuntimes] = useState<RuntimeHost[]>([]);
  const [sessions, setSessions] = useState<RuntimeSession[]>([]);
  const [executions, setExecutions] = useState<RuntimeExecution[]>([]);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const selectedExecution = useMemo(() => executions.find((item) => item.id === selectedExecutionId) ?? executions[0] ?? null, [executions, selectedExecutionId]);

  async function loadRuntimeState(activeWorkspaceId: string, nextRuntimeType?: string) {
    const token = getAuthToken();
    if (!token || !activeWorkspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const runtimeType = nextRuntimeType ?? runtimeFilter;
      const [runtimeRes, sessionRes, executionRes] = await Promise.all([
        apiClient.getRuntimesFiltered(token, { workspace_id: activeWorkspaceId, runtime_type: runtimeType || undefined }),
        apiClient.getRuntimeSessionsFiltered(token, { workspace_id: activeWorkspaceId, session_type: runtimeType || undefined }),
        apiClient.getRuntimeExecutions(token, { workspace_id: activeWorkspaceId }),
      ]);
      setRuntimes(runtimeRes.data);
      setSessions(sessionRes.data);
      setExecutions(runtimeType ? executionRes.data.filter((item) => item.execution_kind.includes(runtimeType)) : executionRes.data);
      setSelectedExecutionId((current) => current || executionRes.data[0]?.id || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load runtime state");
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
        const primaryWorkspaceId = workspaceRes.data[0]?.id ?? "";
        setWorkspaceId(primaryWorkspaceId);
        if (primaryWorkspaceId) await loadRuntimeState(primaryWorkspaceId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load workspaces");
      }
    })();
  }, []);

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <PanelCard eyebrow="Execution Layer" title="Runtime control plane">
          <div className="grid gap-4 xl:grid-cols-[1fr_0.55fr_auto_auto] xl:items-end">
            <label className="flex min-w-72 flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Workspace
              <select
                value={workspaceId}
                onChange={async (event) => {
                  const nextWorkspaceId = event.target.value;
                  setWorkspaceId(nextWorkspaceId);
                  await loadRuntimeState(nextWorkspaceId);
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
            <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Runtime filter
              <select
                value={runtimeFilter}
                onChange={async (event) => {
                  setRuntimeFilter(event.target.value);
                  await loadRuntimeState(workspaceId, event.target.value);
                }}
                className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
              >
                <option value="">All runtimes</option>
                <option value="cli">CLI</option>
                <option value="browser">Browser</option>
              </select>
            </label>
            <div className="flex flex-wrap gap-4 text-[10px] uppercase tracking-[0.2em] text-mutedInk">
              <span>{runtimes.length} runtime hosts</span>
              <span>{sessions.length} sessions</span>
              <span>{executions.length} executions</span>
              <span>{loading ? "refreshing" : "live snapshot"}</span>
            </div>
          </div>
          {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
        </PanelCard>

        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="flex flex-col gap-6">
            <PanelCard eyebrow="Runtime hosts" title="Registered runtimes">
              <div className="space-y-3">
                {runtimes.map((runtime) => (
                  <div key={runtime.id} className="border border-white/5 bg-black/20 px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-semibold text-ink">{runtime.name}</p>
                      <span className={`text-[10px] uppercase tracking-[0.18em] ${runtime.status.startsWith("online") ? "text-emerald-300" : "text-red-300"}`}>
                        {runtime.runtime_type} / {runtime.status}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-mutedInk">{runtime.endpoint_url}</p>
                    <p className="mt-1 text-xs text-mutedInk">Heartbeat: {fmtDate(runtime.last_heartbeat_at)}</p>
                    <p className="mt-1 text-xs text-mutedInk">Doctor: {runtime.doctor_status ?? "--"} / Checked: {fmtDate(runtime.last_capability_check_at)}</p>
                    {readRuntimeEnvironment(runtime)?.machine && typeof readRuntimeEnvironment(runtime)?.machine === "object" ? (
                      <p className="mt-1 text-xs text-mutedInk">
                        Machine status: {String(((readRuntimeEnvironment(runtime)?.machine as Record<string, unknown>).summary as Record<string, unknown> | undefined)?.status ?? "--")}
                      </p>
                    ) : null}
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-mutedInk">{JSON.stringify(runtime.capabilities_json ?? {}, null, 2)}</pre>
                  </div>
                ))}
                {!runtimes.length ? <p className="text-sm text-mutedInk">No runtime host registered for this workspace.</p> : null}
              </div>
            </PanelCard>

            <PanelCard eyebrow="Active sessions" title="Session registry">
              <div className="space-y-3">
                {sessions.map((runtimeSession) => (
                  <div key={runtimeSession.id} className="border border-white/5 bg-black/20 px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-semibold text-ink">{runtimeSession.runtime_name ?? runtimeSession.runtime_id}</p>
                      <span className="text-[10px] uppercase tracking-[0.18em] text-signal">{runtimeSession.session_type} / {runtimeSession.status}</span>
                    </div>
                    <p className="mt-2 text-xs text-mutedInk">Session: {runtimeSession.id}</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-mutedInk">{JSON.stringify(runtimeSession.context_json ?? {}, null, 2)}</pre>
                    <p className="mt-1 text-xs text-mutedInk">Last activity: {fmtDate(runtimeSession.last_activity_at)}</p>
                  </div>
                ))}
                {!sessions.length ? <p className="text-sm text-mutedInk">No runtime sessions have been created yet.</p> : null}
              </div>
            </PanelCard>
          </div>

          <div className="flex flex-col gap-6">
            <PanelCard eyebrow="Executions" title="Runtime execution log">
              <div className="overflow-hidden border border-white/5 bg-black/20">
                <table className="w-full border-collapse text-left text-sm">
                  <thead className="border-b border-white/5 text-[10px] uppercase tracking-[0.3em] text-mutedInk">
                    <tr>
                      <th className="px-4 py-4">Kind</th>
                      <th className="px-4 py-4">Status</th>
                      <th className="px-4 py-4">Runtime</th>
                      <th className="px-4 py-4">Session</th>
                      <th className="px-4 py-4">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {executions.map((execution) => (
                      <tr key={execution.id} onClick={() => setSelectedExecutionId(execution.id)} className={`cursor-pointer border-b border-white/5 last:border-b-0 ${selectedExecution?.id === execution.id ? "bg-signal/5" : ""}`}>
                        <td className="px-4 py-4 font-semibold text-ink">{execution.execution_kind}</td>
                        <td className="px-4 py-4 text-mutedInk">{execution.status}</td>
                        <td className="px-4 py-4 text-mutedInk">{execution.runtime_name ?? execution.runtime_id ?? "--"}</td>
                        <td className="px-4 py-4 text-mutedInk">{execution.runtime_session_id ?? "--"}</td>
                        <td className="px-4 py-4 text-mutedInk">{fmtDate(execution.created_at)}</td>
                      </tr>
                    ))}
                    {!executions.length ? (
                      <tr>
                        <td className="px-4 py-6 text-mutedInk" colSpan={5}>No runtime executions captured yet.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </PanelCard>

            <PanelCard eyebrow="Selected execution" title={selectedExecution?.id ?? "No execution selected"}>
              {selectedExecution ? (
                <div className="space-y-4 text-sm text-mutedInk">
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Execution metadata</p>
                    <p className="mt-2 text-lg font-semibold text-ink">{selectedExecution.status}</p>
                    <p className="mt-2">Kind: {selectedExecution.execution_kind}</p>
                    <p>Source: {selectedExecution.source}</p>
                    <p>Runtime: {selectedExecution.runtime_name ?? selectedExecution.runtime_id ?? "--"}</p>
                    <p>Session: {selectedExecution.runtime_session_id ?? "--"}</p>
                    <p>Connection: {selectedExecution.provider_connection_name ?? "--"}</p>
                    <p>Model: {selectedExecution.resolved_model_name ?? "--"}</p>
                    <p>Created: {fmtDate(selectedExecution.created_at)}</p>
                    <p>Completed: {fmtDate(selectedExecution.completed_at)}</p>
                  </div>
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Command / prompt</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-7 text-ink">
                      {trimBlock(selectedExecution.command_preview ?? selectedExecution.prompt_preview)}
                    </pre>
                  </div>
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Result stream</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-7 text-ink">
                      {trimBlock(selectedExecution.response_preview ?? selectedExecution.error_message)}
                    </pre>
                  </div>
                  {selectedExecution.details_json ? (
                    <div className="border border-white/5 bg-black/25 px-4 py-4">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Execution details</p>
                      <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-ink">{JSON.stringify(selectedExecution.details_json, null, 2)}</pre>
                    </div>
                  ) : null}
                  {Array.isArray(selectedExecution.artifacts_json) && selectedExecution.artifacts_json.length ? (
                    <div className="border border-white/5 bg-black/25 px-4 py-4">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Artifacts</p>
                      {selectedExecution.artifacts_json.map((artifact, index) => renderArtifact(artifact as Record<string, unknown>, index))}
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-mutedInk">Select a runtime execution to inspect it.</p>
              )}
            </PanelCard>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
