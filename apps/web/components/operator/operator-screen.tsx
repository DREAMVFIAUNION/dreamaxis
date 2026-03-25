"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { ChatExecutionTrace, ChatMode, OperatorPlan, OperatorPlanTemplate, RuntimeExecution, Workspace } from "@dreamaxis/client";
import { AnimatePresence, motion } from "framer-motion";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { ChatExecutionBundle } from "@/components/chat/chat-execution-bundle";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";
import { operatorCardMotion, operatorStageMotion } from "@/lib/operator-motion";

const DESKTOP_MODES: ChatMode[] = ["inspect_desktop", "verify_desktop", "operate_desktop"];

function toTrace(value: unknown): ChatExecutionTrace | null {
  if (!value || typeof value !== "object") return null;
  if (!("scenario_tag" in value) || !("steps" in value)) return null;
  return value as ChatExecutionTrace;
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

export function OperatorScreen() {
  const searchParams = useSearchParams();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [plans, setPlans] = useState<OperatorPlan[]>([]);
  const [templates, setTemplates] = useState<OperatorPlanTemplate[]>([]);
  const [runtime, setRuntime] = useState<RuntimeExecution[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<ChatMode>("inspect_desktop");
  const [title, setTitle] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPlan = useMemo(
    () => plans.find((item) => item.id === selectedPlanId) ?? plans[0] ?? null,
    [plans, selectedPlanId],
  );
  const selectedTrace = useMemo(() => toTrace(selectedPlan?.trace_json), [selectedPlan?.trace_json]);
  const runtimeIndex = useMemo(() => new Map(runtime.map((item) => [item.id, item])), [runtime]);
  const pendingApprovals = useMemo(() => plans.filter((item) => item.status === "awaiting_approval"), [plans]);
  const activeRuns = useMemo(() => plans.filter((item) => ["running", "awaiting_approval"].includes(item.status)), [plans]);

  async function refresh(nextWorkspaceId?: string) {
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
      return planRes.data.items.some((item) => item.id === current) ? current : planRes.data.items[0]?.id ?? "";
    });
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
        if (nextWorkspaceId) await refresh(nextWorkspaceId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load operator workspace state");
      }
    })();
  }, []);

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
      setPrompt("");
      setTitle("");
      await refresh(workspaceId);
      setSelectedPlanId(response.data.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create operator plan");
    } finally {
      setPending(false);
    }
  }

  async function handleApproval(decision: "approved" | "denied") {
    const token = getAuthToken();
    if (!token || !selectedPlan) return;
    setPending(true);
    setError(null);
    try {
      if (decision === "approved") {
        await apiClient.approveOperatorPlan(token, selectedPlan.id);
      } else {
        await apiClient.denyOperatorPlan(token, selectedPlan.id);
      }
      await refresh(workspaceId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to review operator plan");
    } finally {
      setPending(false);
    }
  }

  async function handleResume() {
    const token = getAuthToken();
    if (!token || !selectedPlan) return;
    setPending(true);
    setError(null);
    try {
      const response = await apiClient.resumeOperatorPlan(token, selectedPlan.id);
      await refresh(workspaceId);
      setSelectedPlanId(response.data.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resume operator plan");
    } finally {
      setPending(false);
    }
  }

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

        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
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

            <PanelCard eyebrow="Templates" title="Built-in operator templates">
              <div className="grid gap-3">
                {templates.map((template) => (
                  <motion.button
                    key={template.slug}
                    type="button"
                    layout
                    {...operatorCardMotion}
                    onClick={() => void handleCreate(template)}
                    disabled={pending}
                    className="border border-white/5 bg-black/25 px-4 py-4 text-left transition hover:border-signal/30 disabled:cursor-not-allowed disabled:opacity-50"
                  >
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
                  </motion.button>
                ))}
              </div>
            </PanelCard>

            <PanelCard eyebrow="Plan queue" title="Active runs + pending approvals">
              <div className="space-y-3">
                <AnimatePresence initial={false}>
                  {plans.map((plan) => (
                    <motion.button
                      key={plan.id}
                      layout
                      {...operatorCardMotion}
                      type="button"
                      onClick={() => setSelectedPlanId(plan.id)}
                      className={`w-full border px-4 py-4 text-left ${selectedPlan?.id === plan.id ? "border-signal/30 bg-signal/5" : "border-white/5 bg-black/20"}`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-ink">{plan.title}</p>
                          <p className="mt-2 text-xs leading-6 text-mutedInk">{plan.primary_target_value ?? plan.requested_prompt}</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${tone(plan.status)}`}>{plan.status.replaceAll("_", " ")}</span>
                          <span className="border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk">{modeLabel(plan.mode)}</span>
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-mutedInk">
                        <span>Stage: {plan.operator_stage.replaceAll("_", " ")}</span>
                        <span>Approvals: {plan.pending_approval_count}</span>
                        <span>Updated: {new Date(plan.updated_at).toLocaleString()}</span>
                      </div>
                    </motion.button>
                  ))}
                </AnimatePresence>
              </div>
            </PanelCard>
          </div>

          <div className="flex flex-col gap-6">
            <PanelCard eyebrow="Selected plan" title={selectedPlan?.title ?? "No plan selected"}>
              {selectedPlan ? (
                <div className="space-y-4">
                  <div className="operator-live-rail grid gap-3 border border-white/5 bg-black/25 px-4 py-4 md:grid-cols-4">
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Status</p>
                      <p className="mt-2 text-sm font-semibold text-ink">{selectedPlan.status.replaceAll("_", " ")}</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Stage</p>
                      <p className="mt-2 text-sm font-semibold text-ink">{selectedPlan.operator_stage.replaceAll("_", " ")}</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Target</p>
                      <p className="mt-2 text-sm font-semibold text-ink">{selectedPlan.primary_target_value ?? "--"}</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Runtime</p>
                      <p className="mt-2 text-sm font-semibold text-ink">{selectedPlan.parent_execution_id ?? "--"}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    {selectedPlan.parent_execution_id ? (
                      <Link href={`/runtime?execution=${selectedPlan.parent_execution_id}`} className="border border-cyan-400/20 bg-cyan-500/10 px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-cyan-100">
                        Open parent runtime
                      </Link>
                    ) : null}
                    {selectedPlan.conversation_id ? (
                      <Link href={`/chat/${selectedPlan.conversation_id}`} className="border border-white/10 bg-black/20 px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-ink">
                        Open conversation
                      </Link>
                    ) : null}
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => void handleResume()}
                      className="border border-white/10 bg-black/20 px-4 py-3 text-[10px] uppercase tracking-[0.18em] text-ink disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      Resume plan
                    </button>
                  </div>

                  <div className="border border-white/5 bg-black/20 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Requested prompt</p>
                    <p className="mt-2 text-sm leading-7 text-ink">{selectedPlan.requested_prompt}</p>
                    {selectedPlan.last_failure_summary ? <p className="mt-3 text-sm leading-7 text-red-200">{selectedPlan.last_failure_summary}</p> : null}
                  </div>

                  {selectedTrace ? (
                    <ChatExecutionBundle
                      trace={selectedTrace}
                      runtimeIndex={runtimeIndex}
                      parentExecutionId={selectedPlan.parent_execution_id}
                      approvalPending={pending}
                      onReviewDesktopApproval={(decision) => handleApproval(decision)}
                    />
                  ) : (
                    <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">
                      This operator plan does not have a structured execution trace yet.
                    </div>
                  )}
                </div>
              ) : (
                <div className="border border-dashed border-white/10 bg-black/20 px-4 py-5 text-sm text-mutedInk">
                  Create or select an operator plan to inspect approval state, evidence, and runtime lineage.
                </div>
              )}
            </PanelCard>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
