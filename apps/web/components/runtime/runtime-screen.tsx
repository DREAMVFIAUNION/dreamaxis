"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { ExecutionAnnotation, RuntimeExecution, RuntimeSession, RuntimeSessionEvent, RuntimeHost, Workspace } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { ExecutionTimeline } from "@/components/execution/execution-timeline";
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
  const environment =
    runtime.capabilities_json && typeof runtime.capabilities_json === "object"
      ? (runtime.capabilities_json.environment as Record<string, unknown> | undefined)
      : undefined;
  return environment && typeof environment === "object" ? environment : null;
}

function normalizeSessionEvents(events: RuntimeSessionEvent[]): ExecutionAnnotation[] {
  return events.map((event) => {
    const payload = event.payload_json ?? {};
    return {
      id: event.id,
      kind: String(payload.annotation_kind ?? event.event_type),
      title: String(payload.annotation_title ?? event.message ?? event.event_type),
      summary: String(payload.annotation_summary ?? event.message ?? "No summary available."),
      status: String(payload.annotation_status ?? "ready"),
      timestamp: event.created_at,
      source_layer: String(payload.source_layer ?? "runtime"),
      runtime_execution_id: typeof payload.execution_id === "string" ? payload.execution_id : null,
      runtime_session_id: event.runtime_session_id,
      payload_preview:
        typeof payload.payload_preview === "string" || typeof payload.payload_preview === "object"
          ? (payload.payload_preview as Record<string, unknown> | string)
          : null,
      raw_payload: payload,
      target_label: typeof payload.target_label === "string" ? payload.target_label : null,
      duration_ms: typeof payload.duration_ms === "number" ? payload.duration_ms : null,
      evidence_refs: [],
    };
  });
}

export function RuntimeScreen() {
  const searchParams = useSearchParams();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [runtimeFilter, setRuntimeFilter] = useState<string>("");
  const [runtimes, setRuntimes] = useState<RuntimeHost[]>([]);
  const [sessions, setSessions] = useState<RuntimeSession[]>([]);
  const [executions, setExecutions] = useState<RuntimeExecution[]>([]);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>("");
  const [executionTimeline, setExecutionTimeline] = useState<ExecutionAnnotation[]>([]);
  const [sessionEvents, setSessionEvents] = useState<RuntimeSessionEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [timelineLoading, setTimelineLoading] = useState(false);

  const selectedExecution = useMemo(
    () => executions.find((item) => item.id === selectedExecutionId) ?? executions[0] ?? null,
    [executions, selectedExecutionId],
  );

  useEffect(() => {
    const requestedExecutionId = searchParams.get("execution");
    if (!requestedExecutionId) return;
    setSelectedExecutionId(requestedExecutionId);
  }, [searchParams]);

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
      const filteredExecutions = runtimeType
        ? executionRes.data.filter((item) => item.execution_kind.includes(runtimeType))
        : executionRes.data;
      setRuntimes(runtimeRes.data);
      setSessions(sessionRes.data);
      setExecutions(filteredExecutions);
      setSelectedExecutionId((current) => (filteredExecutions.some((item) => item.id === current) ? current : filteredExecutions[0]?.id || ""));
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

  useEffect(() => {
    const token = getAuthToken();
    if (!token || !selectedExecution) {
      setExecutionTimeline([]);
      setSessionEvents([]);
      return;
    }

    setTimelineLoading(true);
    (async () => {
      try {
        const timelineRes = await apiClient.getRuntimeExecutionTimeline(token, selectedExecution.id);
        setExecutionTimeline(timelineRes.data.timeline);

        if (selectedExecution.runtime_session_id) {
          const eventRes = await apiClient.getRuntimeSessionEvents(token, selectedExecution.runtime_session_id);
          setSessionEvents(eventRes.data);
        } else {
          setSessionEvents([]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load execution timeline");
      } finally {
        setTimelineLoading(false);
      }
    })();
  }, [selectedExecution]);

  const selectedRuntime = selectedExecution?.runtime_id ? runtimes.find((item) => item.id === selectedExecution.runtime_id) ?? null : null;
  const normalizedSessionTimeline = useMemo(() => normalizeSessionEvents(sessionEvents), [sessionEvents]);

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <PanelCard eyebrow="Execution Layer" title="Runtime control plane">
          <div className="grid gap-4 xl:grid-cols-[1fr_0.55fr_auto] xl:items-end">
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

        <div className="grid gap-6 xl:grid-cols-[0.82fr_1.18fr]">
          <div className="flex flex-col gap-6">
            <PanelCard eyebrow="Runtime hosts" title="Registered runtimes">
              <div className="space-y-3">
                {runtimes.length ? (
                  runtimes.map((runtime) => (
                    <div key={runtime.id} className="border border-white/5 bg-black/20 px-4 py-4">
                      <div className="flex items-center justify-between gap-4">
                        <p className="font-semibold text-ink">{runtime.name}</p>
                        <span
                          className={`text-[10px] uppercase tracking-[0.18em] ${
                            runtime.status.startsWith("online") ? "text-emerald-300" : "text-red-300"
                          }`}
                        >
                          {runtime.runtime_type} / {runtime.status}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-mutedInk">{runtime.endpoint_url}</p>
                      <p className="mt-1 text-xs text-mutedInk">Heartbeat: {fmtDate(runtime.last_heartbeat_at)}</p>
                      <p className="mt-1 text-xs text-mutedInk">
                        Doctor: {runtime.doctor_status ?? "--"} / Checked: {fmtDate(runtime.last_capability_check_at)}
                      </p>
                      {readRuntimeEnvironment(runtime)?.machine && typeof readRuntimeEnvironment(runtime)?.machine === "object" ? (
                        <p className="mt-1 text-xs text-mutedInk">
                          Machine status:{" "}
                          {String(
                            ((readRuntimeEnvironment(runtime)?.machine as Record<string, unknown>).summary as
                              | Record<string, unknown>
                              | undefined)?.status ?? "--",
                          )}
                        </p>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">
                    No runtime host is online for this workspace yet. Start the CLI or Browser worker and then refresh this view.
                  </div>
                )}
              </div>
            </PanelCard>

            <PanelCard eyebrow="Active sessions" title="Session registry">
              <div className="space-y-3">
                {sessions.length ? (
                  sessions.map((runtimeSession) => (
                    <div key={runtimeSession.id} className="border border-white/5 bg-black/20 px-4 py-4">
                      <div className="flex items-center justify-between gap-4">
                        <p className="font-semibold text-ink">{runtimeSession.runtime_name ?? runtimeSession.runtime_id}</p>
                        <span className="text-[10px] uppercase tracking-[0.18em] text-signal">
                          {runtimeSession.session_type} / {runtimeSession.status}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-mutedInk">Session: {runtimeSession.id}</p>
                      <p className="mt-1 text-xs text-mutedInk">Last activity: {fmtDate(runtimeSession.last_activity_at)}</p>
                      <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-mutedInk">
                        {JSON.stringify(runtimeSession.context_json ?? {}, null, 2)}
                      </pre>
                    </div>
                  ))
                ) : (
                  <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">
                    No sessions have been created yet. Once a skill or chat task hits a runtime, reusable sessions will appear here.
                  </div>
                )}
              </div>
            </PanelCard>
          </div>

          <div className="flex flex-col gap-6">
            <PanelCard eyebrow="Executions" title="Runtime execution log">
              {executions.length ? (
                <div className="overflow-hidden border border-white/5 bg-black/20">
                  <table className="w-full border-collapse text-left text-sm">
                    <thead className="border-b border-white/5 text-[10px] uppercase tracking-[0.3em] text-mutedInk">
                      <tr>
                        <th className="px-4 py-4">Kind</th>
                        <th className="px-4 py-4">Status</th>
                        <th className="px-4 py-4">Summary</th>
                        <th className="px-4 py-4">Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {executions.map((execution) => (
                        <tr
                          key={execution.id}
                          onClick={() => setSelectedExecutionId(execution.id)}
                          className={`cursor-pointer border-b border-white/5 last:border-b-0 ${
                            selectedExecution?.id === execution.id ? "bg-signal/5" : ""
                          }`}
                        >
                          <td className="px-4 py-4 font-semibold text-ink">{execution.execution_kind}</td>
                          <td className="px-4 py-4 text-mutedInk">{execution.status}</td>
                          <td className="px-4 py-4 text-mutedInk">{execution.trace_summary?.headline ?? execution.runtime_name ?? execution.runtime_id ?? "--"}</td>
                          <td className="px-4 py-4 text-mutedInk">{fmtDate(execution.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">
                  No executions yet. Trigger a repo copilot chat, CLI skill, or browser skill to populate this console.
                </div>
              )}
            </PanelCard>

            <PanelCard eyebrow="Selected execution" title={selectedExecution?.trace_summary?.headline ?? selectedExecution?.id ?? "No execution selected"}>
              {selectedExecution ? (
                <div className="space-y-4 text-sm text-mutedInk">
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Execution summary</p>
                    <p className="mt-2 text-lg font-semibold text-ink">{selectedExecution.trace_summary?.headline ?? selectedExecution.status}</p>
                    <p className="mt-2 leading-7">{selectedExecution.trace_summary?.summary ?? selectedExecution.response_preview ?? selectedExecution.error_message ?? "No summary available."}</p>
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      <p>Kind: {selectedExecution.execution_kind}</p>
                      <p>Mode: {selectedExecution.mode ?? "--"}</p>
                      <p>Status: {selectedExecution.status}</p>
                      <p>Runtime: {selectedExecution.runtime_name ?? selectedExecution.runtime_id ?? "--"}</p>
                      <p>Session: {selectedExecution.runtime_session_id ?? "--"}</p>
                      <p>Connection: {selectedExecution.provider_connection_name ?? "--"}</p>
                      <p>Model: {selectedExecution.resolved_model_name ?? "--"}</p>
                      <p>Bundle: {selectedExecution.execution_bundle_id ?? "--"}</p>
                      <p>Parent execution: {selectedExecution.parent_execution_id ?? "--"}</p>
                      <p>Created: {fmtDate(selectedExecution.created_at)}</p>
                      <p>Completed: {fmtDate(selectedExecution.completed_at)}</p>
                    </div>
                    {selectedExecution.child_execution_ids?.length ? (
                      <div className="mt-3 border-t border-white/5 pt-3 text-xs text-mutedInk">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Child executions</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {selectedExecution.child_execution_ids.map((childId) => (
                            <button
                              key={childId}
                              type="button"
                              onClick={() => setSelectedExecutionId(childId)}
                              className="border border-white/10 bg-black/30 px-3 py-2 text-[11px] text-ink transition hover:border-signal/30"
                            >
                              {childId}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    {selectedExecution.conversation_id ? (
                      <div className="mt-3 border-t border-white/5 pt-3 text-xs text-mutedInk">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Origin</p>
                        <a href={`/chat/${selectedExecution.conversation_id}`} className="mt-2 inline-block text-signal">
                          Open source conversation
                        </a>
                      </div>
                    ) : null}
                  </div>

                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Execution timeline</p>
                      <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                        {timelineLoading ? "loading" : `${executionTimeline.length} events`}
                      </span>
                    </div>
                    <div className="mt-3">
                      <ExecutionTimeline
                        items={executionTimeline}
                        emptyCopy={
                          selectedExecution.status === "failed"
                            ? "This execution failed before a full timeline could be captured. Check the summary and session events below."
                            : "No structured timeline was captured for this execution."
                        }
                        resolveArtifacts={(item) =>
                          item.runtime_execution_id === selectedExecution.id && Array.isArray(selectedExecution.artifacts_json)
                            ? (selectedExecution.artifacts_json as Array<Record<string, unknown>>)
                            : []
                        }
                      />
                    </div>
                  </div>

                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Execution payload</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-7 text-ink">
                      {trimBlock(selectedExecution.command_preview ?? selectedExecution.prompt_preview)}
                    </pre>
                    {selectedExecution.error_message && !executionTimeline.length ? (
                      <div className="mt-3 border border-red-400/20 bg-red-500/10 px-3 py-3 text-red-200">
                        Failed with limited details: {selectedExecution.error_message}
                      </div>
                    ) : null}
                  </div>

                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Session event stream</p>
                    <div className="mt-3">
                      <ExecutionTimeline
                        items={normalizedSessionTimeline}
                        emptyCopy="No session-level events were recorded for this execution."
                      />
                    </div>
                  </div>

                  {selectedExecution.execution_kind.includes("browser") && !Array.isArray(selectedExecution.artifacts_json) ? (
                    <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">
                      Browser execution finished without a retrievable artifact. The timeline and session event stream still preserve the URL and action summary.
                    </div>
                  ) : null}

                  {selectedRuntime ? (
                    <div className="border border-white/5 bg-black/25 px-4 py-4">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Runtime snapshot</p>
                      <p className="mt-2">Host: {selectedRuntime.name}</p>
                      <p className="mt-1">Status: {selectedRuntime.status}</p>
                      <p className="mt-1">Doctor: {selectedRuntime.doctor_status ?? "--"}</p>
                      <p className="mt-1">Last heartbeat: {fmtDate(selectedRuntime.last_heartbeat_at)}</p>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">
                  Select an execution from the table to inspect its timeline, failure summary, and session-level event stream.
                </div>
              )}
            </PanelCard>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
