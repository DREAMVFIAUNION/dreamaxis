"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { ExecutionAnnotation, RuntimeExecution, RuntimeSession, RuntimeSessionEvent, RuntimeHost, Workspace } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { ExecutionTimeline } from "@/components/execution/execution-timeline";
import { RichContentRenderer } from "@/components/rich-content/rich-content-renderer";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

function fmtDate(value?: string | null) {
  if (!value) return "--";
  return new Date(value).toLocaleString();
}

function trimBlock(value?: string | null) {
  return value?.trim() || "--";
}

function toArtifactList(value: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(value)) return value as Array<Record<string, unknown>>;
  if (value && typeof value === "object") return [value as Record<string, unknown>];
  return [];
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

function statusTone(value?: string | null) {
  const normalized = String(value ?? "").toLowerCase();
  if (!normalized) return "border-white/10 bg-white/5 text-mutedInk";
  if (normalized.includes("fail") || normalized.includes("error") || normalized.includes("blocked")) {
    return "border-red-400/30 bg-red-500/10 text-red-200";
  }
  if (normalized.includes("approval") || normalized.includes("running") || normalized.includes("pending") || normalized.includes("warn")) {
    return "border-amber-300/30 bg-amber-500/10 text-amber-100";
  }
  return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
}

function getExecutionTrace(execution: RuntimeExecution | null): Record<string, unknown> | null {
  if (!execution?.details_json || typeof execution.details_json !== "object") return null;
  const trace = (execution.details_json as Record<string, unknown>).execution_trace;
  if (!trace || typeof trace !== "object") return null;
  return trace as Record<string, unknown>;
}

function StatePanel({
  title,
  body,
  children,
  tone = "neutral",
}: {
  title: string;
  body: string;
  children?: React.ReactNode;
  tone?: "neutral" | "warn" | "error";
}) {
  const toneClass =
    tone === "error"
      ? "border-red-400/20 bg-red-500/10"
      : tone === "warn"
        ? "border-amber-300/20 bg-amber-500/10"
        : "border-dashed border-white/10 bg-black/20";
  return (
    <div className={`px-4 py-5 text-sm ${toneClass}`}>
      <p className="font-semibold text-ink">{title}</p>
      <p className="mt-2 leading-7 text-mutedInk">{body}</p>
      {children ? <div className="mt-3">{children}</div> : null}
    </div>
  );
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
  const selectedArtifacts = useMemo(() => toArtifactList(selectedExecution?.artifacts_json), [selectedExecution?.artifacts_json]);
  const selectedTrace = useMemo(() => getExecutionTrace(selectedExecution), [selectedExecution]);
  const traceSteps = useMemo(() => {
    if (!selectedTrace) return [] as Array<Record<string, unknown>>;
    const steps = selectedTrace.steps;
    return Array.isArray(steps) ? (steps.filter((item) => item && typeof item === "object") as Array<Record<string, unknown>>) : [];
  }, [selectedTrace]);
  const traceTimeline = useMemo(() => {
    if (!selectedTrace) return [] as Array<Record<string, unknown>>;
    const timeline = selectedTrace.timeline;
    return Array.isArray(timeline)
      ? (timeline.filter((item) => item && typeof item === "object") as Array<Record<string, unknown>>)
      : [];
  }, [selectedTrace]);
  const traceArtifacts = useMemo(() => {
    if (!selectedTrace) return [] as Array<Record<string, unknown>>;
    return toArtifactList(selectedTrace.artifact_summaries ?? selectedTrace.desktop_artifacts);
  }, [selectedTrace]);
  const allArtifacts = useMemo(() => (traceArtifacts.length ? traceArtifacts : selectedArtifacts), [traceArtifacts, selectedArtifacts]);
  const childExecutions = useMemo(
    () =>
      selectedExecution?.child_execution_ids
        ?.map((childId) => executions.find((item) => item.id === childId))
        .filter((item): item is RuntimeExecution => Boolean(item)) ?? [],
    [selectedExecution?.child_execution_ids, executions],
  );
  const approvalHistory = useMemo(() => {
    if (!selectedTrace) return [] as Array<Record<string, unknown>>;
    const explicitHistory = selectedTrace.approval_history;
    if (Array.isArray(explicitHistory)) {
      return explicitHistory.filter((item) => item && typeof item === "object") as Array<Record<string, unknown>>;
    }
    const approval = selectedTrace.desktop_action_approval;
    if (approval && typeof approval === "object") return [approval as Record<string, unknown>];
    return [] as Array<Record<string, unknown>>;
  }, [selectedTrace]);
  const selectedApproval = useMemo(() => {
    if (!selectedTrace) return null;
    const approval = selectedTrace.desktop_action_approval;
    return approval && typeof approval === "object" ? (approval as Record<string, unknown>) : null;
  }, [selectedTrace]);
  const operatorPlanId = selectedExecution?.operator_plan_id;
  const hasNoRuntimeState = !loading && !runtimes.length && !sessions.length && !executions.length;

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
                <option value="desktop">Desktop</option>
              </select>
            </label>
            <div className="flex flex-wrap gap-4 text-[10px] uppercase tracking-[0.2em] text-mutedInk">
              <span>{runtimes.length} runtime hosts</span>
              <span>{sessions.length} sessions</span>
              <span>{executions.length} executions</span>
              <span>{loading ? "refreshing" : "live snapshot"}</span>
            </div>
          </div>
          {error ? (
            <div className="mt-4 border border-red-400/20 bg-red-500/10 px-4 py-4 text-sm text-red-100">
              <p className="font-semibold">Runtime snapshot could not be refreshed</p>
              <p className="mt-2 leading-7">{error}</p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-red-100/90">
                <li>Check that the API and worker processes are still online.</li>
                <li>Open <Link href="/environment" className="text-signal">/environment</Link> to confirm machine and runtime readiness.</li>
                <li>Retry after changing the workspace or runtime filter.</li>
              </ul>
            </div>
          ) : null}
        </PanelCard>

        {loading && !runtimes.length && !sessions.length && !executions.length ? (
          <StatePanel
            title="Collecting runtime state"
            body="DreamAxis is querying runtime hosts, sessions, and executions for this workspace before building the audit view."
          />
        ) : null}

        {hasNoRuntimeState ? (
          <StatePanel
            title="No runtime activity yet"
            body="This workspace has not produced any runtime state yet. Start a worker, run one skill, or send a chat task so the audit plane has something to inspect."
            tone="warn"
          >
            <div className="flex flex-wrap gap-3 text-xs uppercase tracking-[0.18em]">
              <Link href="/environment" className="border border-white/10 px-3 py-2 text-signal">Open environment doctor</Link>
              <Link href="/skills" className="border border-white/10 px-3 py-2 text-signal">Run a skill</Link>
              <Link href="/chat/local-demo" className="border border-white/10 px-3 py-2 text-signal">Open local demo chat</Link>
            </div>
          </StatePanel>
        ) : null}

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
                <StatePanel
                  title="No runtime host is online"
                  body="Start the CLI, Browser, or Desktop worker and then refresh this view. The audit plane only becomes useful after a runtime host has checked in."
                  tone="warn"
                >
                  <div className="flex flex-wrap gap-3 text-xs uppercase tracking-[0.18em]">
                    <Link href="/environment" className="border border-white/10 px-3 py-2 text-signal">Open environment doctor</Link>
                    <Link href="/skills" className="border border-white/10 px-3 py-2 text-signal">Open skills</Link>
                  </div>
                </StatePanel>
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
                <StatePanel
                  title="No runtime sessions yet"
                  body="Sessions appear after a skill, chat task, or browser flow actually reaches a runtime. Use the seeded local path, then come back here for reusable session context."
                >
                  <div className="flex flex-wrap gap-3 text-xs uppercase tracking-[0.18em]">
                    <Link href="/chat/local-demo" className="border border-white/10 px-3 py-2 text-signal">Open local demo chat</Link>
                    <Link href="/skills" className="border border-white/10 px-3 py-2 text-signal">Run a skill</Link>
                  </div>
                </StatePanel>
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
                <StatePanel
                  title="No executions yet"
                  body="Trigger a repo copilot chat, desktop operator turn, CLI skill, or browser skill to populate this console. Runtime execution rows are the entry point for the audit plane."
                >
                  <div className="flex flex-wrap gap-3 text-xs uppercase tracking-[0.18em]">
                    <Link href="/chat/local-demo" className="border border-white/10 px-3 py-2 text-signal">Open chat</Link>
                    <Link href="/operator" className="border border-white/10 px-3 py-2 text-signal">Open operator</Link>
                    <Link href="/skills" className="border border-white/10 px-3 py-2 text-signal">Open skills</Link>
                  </div>
                </StatePanel>
              )}
            </PanelCard>

            <PanelCard eyebrow="Selected execution" title={selectedExecution?.trace_summary?.headline ?? selectedExecution?.id ?? "No execution selected"}>
              {selectedExecution ? (
                <div className="space-y-4 text-sm text-mutedInk">
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Execution summary</p>
                    <p className="mt-2 text-lg font-semibold text-ink">{selectedExecution.trace_summary?.headline ?? selectedExecution.status}</p>
                    <div className="mt-2"><RichContentRenderer content={selectedExecution.trace_summary?.summary ?? selectedExecution.response_preview ?? selectedExecution.error_message ?? "No summary available."} compact /></div>
                    <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                      <p>Kind: {selectedExecution.execution_kind}</p>
                      <p>Mode: {selectedExecution.mode ?? "--"}</p>
                      <p>Status: {selectedExecution.status}</p>
                      <p>Stage: {selectedExecution.operator_stage?.replaceAll("_", " ") ?? "--"}</p>
                      <p>Runtime: {selectedExecution.runtime_name ?? selectedExecution.runtime_id ?? "--"}</p>
                      <p>Session: {selectedExecution.runtime_session_id ?? "--"}</p>
                      <p>Connection: {selectedExecution.provider_connection_name ?? "--"}</p>
                      <p>Model: {selectedExecution.resolved_model_name ?? "--"}</p>
                      <p>Bundle: {selectedExecution.execution_bundle_id ?? "--"}</p>
                      <p>Operator plan: {selectedExecution.operator_plan_id ?? "--"}</p>
                      <p>Parent execution: {selectedExecution.parent_execution_id ?? "--"}</p>
                      <p>Created: {fmtDate(selectedExecution.created_at)}</p>
                      <p>Completed: {fmtDate(selectedExecution.completed_at)}</p>
                    </div>
                    <div className="mt-3 border-t border-white/5 pt-3 text-xs text-mutedInk">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Lineage</p>
                      <div className="mt-2 grid gap-3 md:grid-cols-2">
                        <div className="border border-white/10 bg-black/30 px-3 py-3">
                          <p className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">Parent execution</p>
                          <p className="mt-2 break-all text-ink">{selectedExecution.parent_execution_id ?? "Root execution"}</p>
                        </div>
                        <div className="border border-white/10 bg-black/30 px-3 py-3">
                          <p className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">Operator plan</p>
                          <p className="mt-2 break-all text-ink">{operatorPlanId ?? "--"}</p>
                        </div>
                      </div>
                      {childExecutions.length ? (
                        <div className="mt-3">
                          <p className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">Child executions</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {childExecutions.map((childExecution) => (
                              <button
                                key={childExecution.id}
                                type="button"
                                onClick={() => setSelectedExecutionId(childExecution.id)}
                                className={`border px-3 py-2 text-[11px] text-ink transition hover:border-signal/30 ${statusTone(childExecution.status)}`}
                              >
                                {childExecution.execution_kind} / {childExecution.status}
                              </button>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                    {selectedExecution.conversation_id ? (
                      <div className="mt-3 border-t border-white/5 pt-3 text-xs text-mutedInk">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Origin</p>
                        <a href={`/chat/${selectedExecution.conversation_id}`} className="mt-2 inline-block text-signal">
                          Open source conversation
                        </a>
                      </div>
                    ) : null}
                    {operatorPlanId ? (
                      <div className="mt-3 border-t border-white/5 pt-3 text-xs text-mutedInk">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Operator plan</p>
                        <Link href={`/operator?plan=${operatorPlanId}`} className="mt-2 inline-block text-signal">
                          Open linked operator plan
                        </Link>
                      </div>
                    ) : null}
                  </div>

                  {allArtifacts.length ? (
                    <div className="border border-white/5 bg-black/25 px-4 py-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Artifact carousel</p>
                        <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{allArtifacts.length} captured</span>
                      </div>
                      <div className="mt-3 flex gap-3 overflow-x-auto pb-2">
                        {allArtifacts.map((artifact, index) => {
                          const dataUrl = typeof artifact.data_url === "string" ? artifact.data_url : null;
                          const name = typeof artifact.name === "string" ? artifact.name : `artifact-${index + 1}`;
                          return dataUrl ? (
                            <figure key={`${name}-${index}`} className="min-w-[18rem] overflow-hidden border border-white/5 bg-black/20">
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img src={dataUrl} alt={name} className="h-56 w-full object-cover" />
                              <figcaption className="border-t border-white/5 px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                                {name}
                              </figcaption>
                            </figure>
                          ) : (
                            <pre key={`${name}-${index}`} className="min-w-[18rem] whitespace-pre-wrap border border-white/5 bg-black/20 px-3 py-3 font-sans text-xs leading-6 text-ink">
                              {JSON.stringify(artifact, null, 2)}
                            </pre>
                          );
                        })}
                      </div>
                    </div>
                  ) : null}

                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Action timeline</p>
                      <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                        {timelineLoading ? "loading" : `${traceSteps.length || executionTimeline.length} grouped events`}
                      </span>
                    </div>
                    {traceSteps.length ? (
                      <div className="mt-3 space-y-3">
                        {traceSteps.map((step, index) => {
                          const stepStatus = String(step.status ?? "pending");
                          const stepRuntimeId = typeof step.runtime_execution_id === "string" ? step.runtime_execution_id : null;
                          const stepArtifacts = toArtifactList(step.artifact_summaries);
                          return (
                            <details
                              key={`${String(step.title ?? "step")}-${index}`}
                              className="border border-white/10 bg-black/30 px-3 py-3"
                              open={stepStatus !== "succeeded"}
                            >
                              <summary className="cursor-pointer list-none">
                                <div className="flex items-start justify-between gap-3">
                                  <div className="min-w-0">
                                    <p className="font-semibold text-ink">{String(step.title ?? `Step ${index + 1}`)}</p>
                                    <div className="mt-1 text-xs text-mutedInk"><RichContentRenderer content={String(step.summary ?? "No summary")} compact /></div>
                                  </div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${statusTone(stepStatus)}`}>{stepStatus}</span>
                                    {stepRuntimeId ? (
                                      <button
                                        type="button"
                                        onClick={(event) => {
                                          event.preventDefault();
                                          setSelectedExecutionId(stepRuntimeId);
                                        }}
                                        className="border border-cyan-400/20 bg-cyan-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-cyan-100"
                                      >
                                        Open child
                                      </button>
                                    ) : null}
                                  </div>
                                </div>
                              </summary>
                              <div className="mt-3 border-t border-white/10 pt-3">
                                <p className="text-xs leading-6 text-ink">{String(step.output_excerpt ?? "No output excerpt")}</p>
                                {stepArtifacts.length ? (
                                  <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-mutedInk">
                                    {stepArtifacts.length} artifact(s) attached
                                  </p>
                                ) : null}
                              </div>
                            </details>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="mt-3">
                        <ExecutionTimeline
                          items={executionTimeline}
                          emptyCopy={
                            selectedExecution.status === "failed"
                              ? "This execution failed before a full timeline could be captured. Check summary and session history."
                              : "No structured timeline was captured for this execution."
                          }
                          resolveArtifacts={(item) =>
                            item.runtime_execution_id === selectedExecution.id && Array.isArray(selectedExecution.artifacts_json)
                              ? (selectedExecution.artifacts_json as Array<Record<string, unknown>>)
                              : []
                          }
                        />
                      </div>
                    )}
                    {traceTimeline.length ? (
                      <details className="mt-3 border border-white/10 bg-black/20 px-3 py-2">
                        <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                          Expanded trace timeline ({traceTimeline.length})
                        </summary>
                        <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-ink">
                          {JSON.stringify(traceTimeline, null, 2)}
                        </pre>
                      </details>
                    ) : null}
                  </div>

                  {approvalHistory.length ? (
                    <div className="border border-amber-300/20 bg-amber-500/5 px-4 py-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-amber-100">Approval history</p>
                        <span className="text-[10px] uppercase tracking-[0.18em] text-amber-100">{approvalHistory.length} event(s)</span>
                      </div>
                      <div className="mt-3 space-y-3">
                        {approvalHistory.map((approvalItem, historyIndex) => {
                          const itemStatus = String(approvalItem.status ?? "pending");
                          const requestedActions = Array.isArray(approvalItem.requested_actions)
                            ? (approvalItem.requested_actions as Array<Record<string, unknown>>)
                            : [];
                          return (
                            <div key={`${itemStatus}-${historyIndex}`} className="border border-white/10 bg-black/20 px-3 py-3">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${statusTone(itemStatus)}`}>
                                  {itemStatus.replaceAll("_", " ")}
                                </span>
                                <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                                  {String(approvalItem.reviewed_at ?? approvalItem.updated_at ?? selectedExecution.updated_at ?? "--")}
                                </span>
                              </div>
                              <div className="mt-2 text-sm text-ink"><RichContentRenderer content={String(approvalItem.summary ?? "Desktop approval metadata captured.")} compact /></div>
                              {requestedActions.length ? (
                                <div className="mt-2 grid gap-2 md:grid-cols-2">
                                  {requestedActions.map((action, actionIndex) => (
                                    <div key={`${String(action.id ?? actionIndex)}`} className="border border-white/10 bg-black/30 px-3 py-2">
                                      <p className="text-[10px] uppercase tracking-[0.18em] text-amber-100">
                                        {String(action.action ?? "desktop_action").replaceAll("_", " ")}
                                      </p>
                                      <p className="mt-1 text-xs leading-6 text-mutedInk">
                                        {String(action.target_window ?? action.target_app ?? action.target_label ?? "desktop")}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : selectedApproval ? (
                    <div className="border border-amber-300/20 bg-amber-500/5 px-4 py-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-amber-100">Approval state</p>
                        <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${statusTone(String(selectedApproval.status ?? "pending"))}`}>
                          {String(selectedApproval.status ?? "pending").replaceAll("_", " ")}
                        </span>
                      </div>
                      <div className="mt-2 text-sm text-ink"><RichContentRenderer content={String(selectedApproval.summary ?? "Desktop approval metadata captured.")} compact /></div>
                    </div>
                  ) : null}

                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Session event stream</p>
                    <div className="mt-3">
                      <ExecutionTimeline
                        items={normalizedSessionTimeline}
                        emptyCopy="No session-level events were recorded for this execution."
                      />
                    </div>
                  </div>

                  <details className="border border-white/5 bg-black/25 px-4 py-4">
                    <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-signal">Raw payload (compressed by default)</summary>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-7 text-ink">
                      {trimBlock(selectedExecution.command_preview ?? selectedExecution.prompt_preview)}
                    </pre>
                    <details className="mt-3 border border-white/10 bg-black/20 px-3 py-2">
                      <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-mutedInk">Details JSON</summary>
                      <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-ink">
                        {JSON.stringify(selectedExecution.details_json ?? {}, null, 2)}
                      </pre>
                    </details>
                    {selectedExecution.error_message && !executionTimeline.length ? (
                      <div className="mt-3 border border-red-400/20 bg-red-500/10 px-3 py-3 text-red-200">
                        Failed with limited details: {selectedExecution.error_message}
                      </div>
                    ) : null}
                  </details>

                  {selectedExecution.execution_kind.includes("browser") && !allArtifacts.length ? (
                    <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">
                      Browser execution finished without a retrievable artifact. Timeline and session event stream still preserve URL and action summary.
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
                <StatePanel
                  title={executions.length ? "Select an execution" : "Execution details will appear here"}
                  body={
                    executions.length
                      ? "Pick any execution row above to inspect lineage, summaries, approval history, artifacts, and raw payload details."
                      : "Once this workspace produces a runtime execution, this panel becomes the detailed audit view for timelines, artifacts, and operator linkage."
                  }
                />
              )}
            </PanelCard>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
