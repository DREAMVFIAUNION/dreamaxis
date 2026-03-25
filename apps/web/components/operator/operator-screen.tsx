"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { ChatExecutionTrace, ChatMode, OperatorPlan, OperatorPlanTemplate, RuntimeExecution, Workspace } from "@dreamaxis/client";
import { AnimatePresence, motion } from "framer-motion";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { ChatExecutionBundle } from "@/components/chat/chat-execution-bundle";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";
import { operatorCardMotion } from "@/lib/operator-motion";

type PlanView = "approval_queue" | "active_runs" | "all_plans" | "templates" | "recent_failures";
type PlanStatusFilter = "all" | "queued" | "running" | "awaiting_approval" | "blocked" | "failed" | "succeeded";

const DESKTOP_MODES: ChatMode[] = ["inspect_desktop", "verify_desktop", "operate_desktop"];
const FILTERS: PlanStatusFilter[] = ["all", "queued", "running", "awaiting_approval", "blocked", "failed", "succeeded"];

function toTrace(value: unknown): ChatExecutionTrace | null {
  if (!value || typeof value !== "object") return null;
  if (!("scenario_tag" in value) || !("steps" in value)) return null;
  return value as ChatExecutionTrace;
}

function label(value?: string | null) {
  return (value || "unknown").replaceAll("_", " ");
}

function tone(value?: string | null) {
  const v = (value ?? "").toLowerCase();
  if (v.includes("fail") || v.includes("error") || v.includes("blocked")) return "border-red-400/30 bg-red-500/10 text-red-200";
  if (v.includes("approval") || v.includes("running") || v.includes("warn")) return "border-amber-300/30 bg-amber-500/10 text-amber-100";
  if (!v || v === "pending") return "border-white/10 bg-white/5 text-mutedInk";
  return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
}

function modeLabel(mode?: string | null) {
  return mode ? mode.replaceAll("_", " ") : "inspect desktop";
}

function shortText(value?: string | null, limit = 120) {
  const normalized = (value || "").replace(/\s+/g, " ").trim();
  if (!normalized) return "--";
  return normalized.length <= limit ? normalized : `${normalized.slice(0, limit - 3)}...`;
}

function EmptyState({ copy }: { copy: string }) {
  return <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">{copy}</div>;
}

function PlanListItem({
  plan,
  selected,
  onOpen,
}: {
  plan: OperatorPlan;
  selected: boolean;
  onOpen: (planId: string) => void;
}) {
  return (
    <motion.button
      type="button"
      layout
      {...operatorCardMotion}
      onClick={() => onOpen(plan.id)}
      className={`w-full border px-4 py-4 text-left ${selected ? "border-signal/30 bg-signal/5" : "border-white/5 bg-black/20"}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink">{plan.title}</p>
          <p className="mt-2 text-xs leading-6 text-mutedInk">{shortText(plan.primary_target_value ?? plan.requested_prompt)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${tone(plan.status)}`}>{label(plan.status)}</span>
          <span className="border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk">{modeLabel(plan.mode)}</span>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-mutedInk">
        <span>Stage: {label(plan.operator_stage)}</span>
        <span>Approvals: {plan.pending_approval_count}</span>
        <span>Updated: {new Date(plan.updated_at).toLocaleString()}</span>
      </div>
    </motion.button>
  );
}

export function OperatorScreen() {
  const searchParams = useSearchParams();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [plans, setPlans] = useState<OperatorPlan[]>([]);
  const [templates, setTemplates] = useState<OperatorPlanTemplate[]>([]);
  const [runtime, setRuntime] = useState<RuntimeExecution[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [view, setView] = useState<PlanView>("approval_queue");
  const [filter, setFilter] = useState<PlanStatusFilter>("all");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<ChatMode>("inspect_desktop");
  const [title, setTitle] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPlan = useMemo(() => plans.find((item) => item.id === selectedPlanId) ?? null, [plans, selectedPlanId]);
  const selectedTrace = useMemo(() => toTrace(selectedPlan?.trace_json), [selectedPlan?.trace_json]);
  const runtimeIndex = useMemo(() => new Map(runtime.map((item) => [item.id, item])), [runtime]);
  const pendingApprovals = useMemo(() => plans.filter((item) => item.status === "awaiting_approval"), [plans]);
  const activeRuns = useMemo(() => plans.filter((item) => ["running", "awaiting_approval"].includes(item.status)), [plans]);
  const failedPlans = useMemo(() => plans.filter((item) => item.status === "failed"), [plans]);
  const filteredPlans = useMemo(() => (filter === "all" ? plans : plans.filter((item) => item.status === filter)), [plans, filter]);

  const refresh = useCallback(async (nextWorkspaceId?: string) => {
    const token = getAuthToken();
    const targetWorkspaceId = nextWorkspaceId ?? workspaceId;
    if (!token || !targetWorkspaceId) return;
    const [planRes, runtimeRes] = await Promise.all([
      apiClient.getOperatorPlans(token, targetWorkspaceId),
      apiClient.getRuntimeExecutions(token, { workspace_id: targetWorkspaceId }),
    ]);
    setPlans(planRes.data.items);
    setTemplates(planRes.data.templates);
    setRuntime(runtimeRes.data);
    setSelectedPlanId((current) => {
      const fromQuery = searchParams.get("plan");
      if (fromQuery && planRes.data.items.some((item) => item.id === fromQuery)) return fromQuery;
      if (current && planRes.data.items.some((item) => item.id === current)) return current;
      return planRes.data.items[0]?.id ?? "";
    });
  }, [searchParams, workspaceId]);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) return;
    (async () => {
      try {
        const workspaceRes = await apiClient.getWorkspaces(token);
        setWorkspaces(workspaceRes.data);
        const nextWorkspaceId = workspaceRes.data[0]?.id ?? "";
        setWorkspaceId(nextWorkspaceId);
        if (nextWorkspaceId) await refresh(nextWorkspaceId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load operator workspace state");
      }
    })();
  }, [refresh]);

  useEffect(() => {
    if (!workspaceId) return;
    const intervalId = window.setInterval(() => {
      void refresh(workspaceId);
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [refresh, workspaceId]);

  async function handleCreate(template?: OperatorPlanTemplate) {
    const token = getAuthToken();
    if (!token || !workspaceId) return;
    setPending(true);
    setError(null);
    try {
      const response = await apiClient.createOperatorPlan(token, {
        workspace_id: workspaceId,
        prompt: template?.prompt ?? prompt,
        mode: template?.mode ?? mode,
        template_slug: template?.slug,
        title: template?.title ?? (title || undefined),
      });
      await refresh(workspaceId);
      setSelectedPlanId(response.data.id);
      setDrawerOpen(true);
      setPrompt("");
      setTitle("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create operator plan");
    } finally {
      setPending(false);
    }
  }

  async function handleApproval(planId: string, decision: "approved" | "denied") {
    const token = getAuthToken();
    if (!token) return;
    setPending(true);
    setError(null);
    try {
      if (decision === "approved") await apiClient.approveOperatorPlan(token, planId);
      else await apiClient.denyOperatorPlan(token, planId);
      await refresh(workspaceId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to review operator plan");
    } finally {
      setPending(false);
    }
  }

  async function handleResume(planId: string) {
    const token = getAuthToken();
    if (!token) return;
    setPending(true);
    setError(null);
    try {
      await apiClient.resumeOperatorPlan(token, planId);
      await refresh(workspaceId);
      setDrawerOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resume operator plan");
    } finally {
      setPending(false);
    }
  }

  function openPlan(planId: string) {
    setSelectedPlanId(planId);
    setDrawerOpen(true);
  }

  const currentViewItems =
    view === "approval_queue"
      ? pendingApprovals
      : view === "active_runs"
        ? activeRuns
        : view === "recent_failures"
          ? failedPlans.slice(0, 5)
          : filteredPlans;

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <PanelCard eyebrow="Operator lane" title="Motion-first Desktop Operator">
          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr_auto] xl:items-end">
            <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Workspace
              <select
                value={workspaceId}
                onChange={async (event) => {
                  const nextWorkspaceId = event.target.value;
                  setWorkspaceId(nextWorkspaceId);
                  await refresh(nextWorkspaceId);
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
            <div className="grid gap-3 md:grid-cols-3">
              <div className="border border-white/5 bg-black/20 px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-signal">Active runs</p>
                <p className="mt-2 text-2xl font-black text-ink">{activeRuns.length}</p>
              </div>
              <div className="border border-white/5 bg-black/20 px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-signal">Pending approvals</p>
                <p className="mt-2 text-2xl font-black text-ink">{pendingApprovals.length}</p>
              </div>
              <div className="border border-white/5 bg-black/20 px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-signal">Templates</p>
                <p className="mt-2 text-2xl font-black text-ink">{templates.length}</p>
              </div>
            </div>
            <div className="flex flex-col items-start gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              <Link href="/runtime" className="border border-cyan-400/20 bg-cyan-500/10 px-4 py-3 text-cyan-100">
                Open runtime audit
              </Link>
              <Link href="/chat/local-demo" className="text-signal">
                Jump back to chat
              </Link>
            </div>
          </div>
          {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
        </PanelCard>

        <div className="grid gap-6 xl:grid-cols-[0.34fr_0.66fr]">
          <div className="flex flex-col gap-6">
            <PanelCard eyebrow="Create plan" title="Launch a new operator run">
              <div className="space-y-3">
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Optional plan title"
                  className="w-full border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
                />
                <textarea
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  rows={4}
                  placeholder="Describe the desktop task you want DreamAxis to inspect, verify, or operate."
                  className="w-full border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
                />
                <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                  <select
                    value={mode}
                    onChange={(event) => setMode(event.target.value as ChatMode)}
                    className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
                  >
                    {DESKTOP_MODES.map((item) => (
                      <option key={item} value={item}>
                        {modeLabel(item)}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={pending || !prompt.trim()}
                    onClick={() => void handleCreate()}
                    className="border border-signal/30 bg-signal px-5 py-3 text-xs font-black uppercase tracking-[0.2em] text-black disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {pending ? "Running..." : "Create plan"}
                  </button>
                </div>
              </div>
            </PanelCard>

            <PanelCard eyebrow="Operator nav" title="Manage queue">
              <div className="space-y-2">
                {[
                  ["approval_queue", "Approval Queue", pendingApprovals.length],
                  ["active_runs", "Active Runs", activeRuns.length],
                  ["all_plans", "All Plans", plans.length],
                  ["templates", "Templates", templates.length],
                  ["recent_failures", "Recent Failures", failedPlans.length],
                ].map(([nextView, copy, count]) => (
                  <button
                    key={String(nextView)}
                    type="button"
                    onClick={() => setView(nextView as PlanView)}
                    className={`flex w-full items-center justify-between border px-4 py-3 text-left text-sm ${
                      view === nextView ? "border-signal/30 bg-signal/5 text-ink" : "border-white/5 bg-black/20 text-mutedInk"
                    }`}
                  >
                    <span>{copy}</span>
                    <span className="text-[10px] uppercase tracking-[0.18em]">{count}</span>
                  </button>
                ))}
              </div>
            </PanelCard>
          </div>

          <div className="flex flex-col gap-6">
            {view === "templates" ? (
              <PanelCard eyebrow="Template library" title="Built-in operator templates">
                {templates.length ? (
                  <div className="grid gap-3 lg:grid-cols-2">
                    {templates.map((template) => (
                      <motion.div key={template.slug} layout {...operatorCardMotion} className="border border-white/5 bg-black/20 px-4 py-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${tone(template.mode)}`}>{modeLabel(template.mode)}</span>
                          {template.tags.slice(0, 3).map((tag) => (
                            <span key={tag} className="border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <p className="mt-3 font-semibold text-ink">{template.title}</p>
                        <p className="mt-2 text-sm leading-6 text-mutedInk">{template.description}</p>
                        <div className="mt-4 flex flex-wrap gap-3">
                          <button
                            type="button"
                            disabled={pending}
                            onClick={() => void handleCreate(template)}
                            className="border border-signal/30 bg-signal px-4 py-2.5 text-[10px] font-black uppercase tracking-[0.18em] text-black disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            Use template
                          </button>
                          <Link
                            href={`/chat/local-demo?template=${template.slug}`}
                            className="border border-white/10 bg-black/20 px-4 py-2.5 text-[10px] uppercase tracking-[0.18em] text-ink"
                          >
                            Open in chat
                          </Link>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <EmptyState copy="No built-in templates were returned for this workspace." />
                )}
              </PanelCard>
            ) : (
              <PanelCard
                eyebrow={view === "approval_queue" ? "Approval queue" : view === "active_runs" ? "Active runs" : view === "recent_failures" ? "Recent failures" : "All plans"}
                title={
                  view === "approval_queue"
                    ? "Pending approvals"
                    : view === "active_runs"
                      ? "Running plans"
                      : view === "recent_failures"
                        ? "Recently failed plans"
                        : "All operator plans"
                }
              >
                {view === "all_plans" ? (
                  <div className="mb-4 flex flex-wrap gap-2">
                    {FILTERS.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => setFilter(item)}
                        className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${
                          filter === item ? "border-signal/30 bg-signal/5 text-ink" : "border-white/10 bg-black/20 text-mutedInk"
                        }`}
                      >
                        {label(item)}
                      </button>
                    ))}
                  </div>
                ) : null}

                {currentViewItems.length ? (
                  <div className="space-y-3">
                    <AnimatePresence initial={false}>
                      {currentViewItems.map((plan) => (
                        <div key={plan.id} className="space-y-3">
                          <PlanListItem plan={plan} selected={selectedPlan?.id === plan.id} onOpen={openPlan} />
                          {view === "approval_queue" ? (
                            <div className="flex flex-wrap gap-3 border border-amber-300/20 bg-amber-500/5 px-4 py-3">
                              <button
                                type="button"
                                disabled={pending}
                                onClick={() => void handleApproval(plan.id, "approved")}
                                className="border border-emerald-400/30 bg-emerald-500/15 px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Approve
                              </button>
                              <button
                                type="button"
                                disabled={pending}
                                onClick={() => void handleApproval(plan.id, "denied")}
                                className="border border-red-400/30 bg-red-500/10 px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Deny
                              </button>
                              <Link href={plan.conversation_id ? `/chat/${plan.conversation_id}` : `/runtime?execution=${plan.parent_execution_id ?? ""}`} className="border border-white/10 bg-black/20 px-4 py-2.5 text-[10px] uppercase tracking-[0.18em] text-ink">
                                Inspect details
                              </Link>
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </AnimatePresence>
                  </div>
                ) : (
                  <EmptyState
                    copy={
                      view === "approval_queue"
                        ? "No approvals are waiting right now."
                        : view === "active_runs"
                          ? "No operator plans are currently running."
                          : view === "recent_failures"
                            ? "No recent failures were recorded."
                            : "No plans match the selected filter."
                    }
                  />
                )}
              </PanelCard>
            )}
          </div>
        </div>

        <AnimatePresence>
          {drawerOpen && selectedPlan ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            >
              <div className="absolute inset-y-0 right-0 w-full max-w-4xl overflow-y-auto border-l border-white/10 bg-[#111111] p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Plan detail</p>
                    <h2 className="mt-2 text-2xl font-black text-ink">{selectedPlan.title}</h2>
                    <p className="mt-2 text-sm leading-7 text-mutedInk">{selectedPlan.requested_prompt}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDrawerOpen(false)}
                    className="border border-white/10 bg-black/20 px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-ink"
                  >
                    Close
                  </button>
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-4">
                  <div className="border border-white/5 bg-black/20 px-4 py-3">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Status</p>
                    <p className="mt-2 text-sm font-semibold text-ink">{label(selectedPlan.status)}</p>
                  </div>
                  <div className="border border-white/5 bg-black/20 px-4 py-3">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Stage</p>
                    <p className="mt-2 text-sm font-semibold text-ink">{label(selectedPlan.operator_stage)}</p>
                  </div>
                  <div className="border border-white/5 bg-black/20 px-4 py-3">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Target</p>
                    <p className="mt-2 text-sm font-semibold text-ink">{selectedPlan.primary_target_value ?? "--"}</p>
                  </div>
                  <div className="border border-white/5 bg-black/20 px-4 py-3">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Updated</p>
                    <p className="mt-2 text-sm font-semibold text-ink">{new Date(selectedPlan.updated_at).toLocaleString()}</p>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  {selectedPlan.conversation_id ? (
                    <Link href={`/chat/${selectedPlan.conversation_id}`} className="border border-white/10 bg-black/20 px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-ink">
                      Open chat
                    </Link>
                  ) : null}
                  {selectedPlan.parent_execution_id ? (
                    <Link href={`/runtime?execution=${selectedPlan.parent_execution_id}`} className="border border-cyan-400/20 bg-cyan-500/10 px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-cyan-100">
                      Open runtime
                    </Link>
                  ) : null}
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => void handleResume(selectedPlan.id)}
                    className="border border-white/10 bg-black/20 px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-ink disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Resume plan
                  </button>
                </div>

                {selectedPlan.last_failure_summary ? (
                  <div className="mt-5 border border-red-400/20 bg-red-500/10 px-4 py-4 text-sm leading-7 text-red-100">
                    {selectedPlan.last_failure_summary}
                  </div>
                ) : null}

                <div className="mt-5">
                  {selectedTrace ? (
                    <ChatExecutionBundle
                      trace={selectedTrace}
                      runtimeIndex={runtimeIndex}
                      parentExecutionId={selectedPlan.parent_execution_id}
                      approvalPending={pending}
                      onReviewDesktopApproval={(decision) => handleApproval(selectedPlan.id, decision)}
                    />
                  ) : (
                    <EmptyState copy="This operator plan does not have a structured execution trace yet." />
                  )}
                </div>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </AppShell>
  );
}
