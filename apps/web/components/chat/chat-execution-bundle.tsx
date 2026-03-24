"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import type { ChatExecutionTrace, ChatEvidenceItem, RuntimeExecution } from "@dreamaxis/client";

const FAILURE_TYPE_LABELS: Record<string, string> = {
  dependency_or_install: "Dependency / install",
  missing_toolchain: "Missing toolchain",
  repo_not_ready: "Repo not ready",
  script_or_manifest_missing: "Script / manifest missing",
  code_or_config_failure: "Code / config failure",
  browser_or_runtime_failure: "Browser / runtime failure",
  unknown: "Unknown",
};

function tone(value?: string | null) {
  const v = (value ?? "").toLowerCase();
  if (v.includes("fail") || v.includes("error") || v.includes("missing")) return "border-red-400/30 bg-red-500/10 text-red-200";
  if (v.includes("degraded") || v.includes("warn") || v.includes("running")) return "border-amber-300/30 bg-amber-500/10 text-amber-100";
  if (!v || v === "pending") return "border-white/10 bg-white/5 text-mutedInk";
  return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
}

function modeLabel(mode?: string | null) {
  return mode ? mode.replaceAll("_", " ") : "Auto";
}

function readiness(trace: ChatExecutionTrace | null) {
  const status =
    trace?.workspace_readiness &&
    typeof trace.workspace_readiness === "object" &&
    "status" in trace.workspace_readiness
      ? String((trace.workspace_readiness as { status?: string }).status ?? "")
      : null;
  return status || "Pending";
}

function toArtifacts(value: unknown) {
  return Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];
}

function shorten(value: string | null | undefined, limit = 140) {
  if (!value) return "--";
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit - 3)}...`;
}

function StepMeta({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="border border-white/5 bg-black/20 px-2.5 py-2">
      <p className="text-[9px] uppercase tracking-[0.18em] text-mutedInk">{label}</p>
      <p className="mt-1 break-all text-[11px] leading-5 text-ink">{String(value)}</p>
    </div>
  );
}

function SectionCard({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="border border-white/5 bg-black/25 px-3 py-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[10px] uppercase tracking-[0.2em] text-signal">{title}</p>
        {aside}
      </div>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function renderArtifact(artifact: Record<string, unknown>, index: number) {
  const dataUrl = typeof artifact.data_url === "string" ? artifact.data_url : null;
  const kind = typeof artifact.kind === "string" ? artifact.kind : "artifact";
  const name = typeof artifact.name === "string" ? artifact.name : `${kind}-${index + 1}`;
  if (dataUrl) {
    return (
      <figure key={`${name}-${index}`} className="overflow-hidden border border-white/5 bg-black/30">
        <img src={dataUrl} alt={name} className="w-full object-cover" />
        <figcaption className="border-t border-white/5 px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-mutedInk">
          {name}
        </figcaption>
      </figure>
    );
  }

  return (
    <pre key={`${name}-${index}`} className="whitespace-pre-wrap border border-white/5 bg-black/30 px-3 py-3 font-sans text-[11px] leading-6 text-ink">
      {JSON.stringify(artifact, null, 2)}
    </pre>
  );
}

function renderEvidence(evidence: ChatEvidenceItem, runtimeIndex: Map<string, RuntimeExecution>) {
  const runtimeArtifacts = evidence.runtime_execution_id ? toArtifacts(runtimeIndex.get(evidence.runtime_execution_id)?.artifacts_json) : [];
  const inlineArtifacts = toArtifacts(evidence.artifact_summaries);
  const artifacts = inlineArtifacts.length ? inlineArtifacts : runtimeArtifacts;
  const preview = shorten(evidence.content, 120);
  const hasExpandableBody = Boolean(
    evidence.stderr_excerpt ||
      artifacts.length ||
      evidence.path ||
      evidence.current_url ||
      evidence.label ||
      typeof evidence.exit_code === "number",
  );

  return (
    <details key={`${evidence.title}-${evidence.runtime_execution_id ?? evidence.content}`} className="group border border-white/5 bg-black/30 px-3 py-3" open={!hasExpandableBody}>
      <summary className="cursor-pointer list-none">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold text-ink">{evidence.title}</p>
              <span className="border border-cyan-400/20 bg-cyan-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-cyan-100">{evidence.type}</span>
            </div>
            <p className="mt-2 text-xs leading-6 text-mutedInk">{preview}</p>
          </div>
          <div className="flex items-center gap-2">
            {evidence.runtime_execution_id ? (
              <Link
                href={`/runtime?execution=${evidence.runtime_execution_id}`}
                className="border border-cyan-400/20 bg-cyan-500/10 px-2.5 py-2 text-[10px] uppercase tracking-[0.18em] text-cyan-100"
              >
                Open runtime
              </Link>
            ) : null}
            {hasExpandableBody ? <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk transition group-open:text-ink">Details</span> : null}
          </div>
        </div>
      </summary>

      {hasExpandableBody ? (
        <div className="mt-3 border-t border-white/5 pt-3">
          <p className="text-xs leading-6 text-ink">{evidence.content}</p>
          <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            <StepMeta label="Path" value={evidence.path} />
            <StepMeta label="URL" value={evidence.current_url} />
            <StepMeta label="Exit" value={typeof evidence.exit_code === "number" ? evidence.exit_code : null} />
            <StepMeta label="Label" value={evidence.label} />
          </div>
          {evidence.stderr_excerpt ? (
            <details className="mt-3 border border-red-400/20 bg-red-500/5 px-3 py-2" open>
              <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-red-200">stderr excerpt</summary>
              <pre className="mt-3 whitespace-pre-wrap font-sans text-[11px] leading-6 text-red-200">{evidence.stderr_excerpt}</pre>
            </details>
          ) : null}
          {artifacts.length ? <div className="mt-3 grid gap-3 md:grid-cols-2">{artifacts.map((artifact, index) => renderArtifact(artifact, index))}</div> : null}
        </div>
      ) : null}
    </details>
  );
}

export function ChatExecutionBundle({
  trace,
  runtimeIndex,
  parentExecutionId,
}: {
  trace: ChatExecutionTrace;
  runtimeIndex: Map<string, RuntimeExecution>;
  parentExecutionId?: string | null;
}) {
  const currentMode = trace.mode_summary?.active_mode ?? trace.mode;
  const bundleId = trace.execution_bundle_id ?? parentExecutionId ?? "--";
  const evidenceItems = trace.evidence_items ?? trace.evidence ?? [];
  const groundingSummary = trace.grounding_summary;
  const groundedTargets = trace.grounded_targets ?? [];
  const primaryGroundedTarget = trace.primary_grounded_target;
  const reflectionSummary = trace.reflection_summary;
  const failureSummary = trace.failure_summary?.trim();
  const failureType = trace.failure_classification?.trim() ?? "";
  const primaryFailureTarget = trace.primary_failure_target?.trim() ?? primaryGroundedTarget?.value?.trim();
  const stderrHighlights = (trace.stderr_highlights ?? []).filter(Boolean);
  const groundedReasoning = (trace.grounded_next_step_reasoning ?? []).filter(Boolean);
  const failureLabel = FAILURE_TYPE_LABELS[failureType] ?? (failureType ? failureType.replaceAll("_", " ") : "Unknown");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(currentMode)}`}>Mode / {modeLabel(currentMode)}</span>
        <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(readiness(trace))}`}>Readiness / {readiness(trace)}</span>
        <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(trace.trace_summary?.status)}`}>Bundle / {bundleId}</span>
        {parentExecutionId ? (
          <Link
            href={`/runtime?execution=${parentExecutionId}`}
            className="border border-cyan-400/20 bg-cyan-500/10 px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-cyan-100"
          >
            Audit parent runtime
          </Link>
        ) : null}
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <SectionCard title="Intent / plan">
          <ul className="space-y-2 text-sm leading-7 text-ink">
            {trace.intent_plan.map((item) => (
              <li key={item}>- {item}</li>
            ))}
          </ul>
        </SectionCard>
        <SectionCard title="Grounded target">
          <div className="space-y-3">
            {groundingSummary?.summary ? <p className="text-sm leading-7 text-ink">{groundingSummary.summary}</p> : null}
            {primaryGroundedTarget ? (
              <div className="border border-cyan-400/20 bg-cyan-500/5 px-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="border border-cyan-400/20 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-cyan-100">
                    {primaryGroundedTarget.type.replaceAll("_", " ")}
                  </span>
                  {primaryGroundedTarget.status ? (
                    <span className="border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                      {primaryGroundedTarget.status}
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 break-all text-sm leading-7 text-ink">{primaryGroundedTarget.value}</p>
                {primaryGroundedTarget.reason ? <p className="mt-2 text-xs leading-6 text-mutedInk">{primaryGroundedTarget.reason}</p> : null}
              </div>
            ) : null}
            {groundedTargets.length > 1 ? (
              <ul className="space-y-2 text-xs leading-6 text-mutedInk">
                {groundedTargets.slice(0, 4).map((target, index) => (
                  <li key={`${target.type}-${target.value}-${index}`}>
                    - <span className="text-ink">{target.value}</span>
                    <span className="text-mutedInk"> ({target.type.replaceAll("_", " ")})</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="What ran" aside={<span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{(trace.steps ?? []).length} child executions</span>}>
        <div className="space-y-3">
          {(trace.steps ?? []).filter((step) => step.runtime_execution_id).map((step) => {
            const runtime = step.runtime_execution_id ? runtimeIndex.get(step.runtime_execution_id) : null;
            const artifacts = toArtifacts(step.artifact_summaries).length ? toArtifacts(step.artifact_summaries) : toArtifacts(runtime?.artifacts_json);
            const stepTarget =
              step.current_url ??
              (typeof step.command_preview === "string"
                ? step.command_preview
                : step.command_preview
                  ? JSON.stringify(step.command_preview)
                  : primaryGroundedTarget?.value ?? "--");
            const stepIsOpen = step.status !== "succeeded";

            return (
              <details key={step.runtime_execution_id} className="group border border-white/5 bg-black/30 px-3 py-3" open={stepIsOpen}>
                <summary className="cursor-pointer list-none">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-ink">{step.title}</p>
                        <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${tone(step.status)}`}>{step.status}</span>
                        <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{step.kind}</span>
                        {typeof step.exit_code === "number" ? (
                          <span className="border border-white/10 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk">exit {step.exit_code}</span>
                        ) : null}
                      </div>
                      <p className="mt-2 text-xs leading-6 text-mutedInk">{shorten(step.summary, 140)}</p>
                      <p className="mt-2 text-[11px] leading-5 text-ink/80">Target: {shorten(stepTarget, 150)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {step.runtime_execution_id ? (
                        <Link
                          href={`/runtime?execution=${step.runtime_execution_id}`}
                          className="border border-cyan-400/20 bg-cyan-500/10 px-2.5 py-2 text-[10px] uppercase tracking-[0.18em] text-cyan-100"
                        >
                          Open runtime
                        </Link>
                      ) : null}
                      <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk transition group-open:text-ink">{stepIsOpen ? "Expanded" : "Expand"}</span>
                    </div>
                  </div>
                </summary>

                <div className="mt-3 border-t border-white/5 pt-3">
                  <p className="text-xs leading-6 text-mutedInk">{step.summary}</p>
                  <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                    <StepMeta label="Target" value={stepTarget} />
                    <StepMeta label="Session" value={step.runtime_session_id ?? "--"} />
                    <StepMeta label="Artifacts" value={artifacts.length} />
                    <StepMeta label="Runtime" value={step.runtime_execution_id ?? "--"} />
                  </div>
                  {step.output_excerpt ? (
                    <details className="mt-3 border border-white/5 bg-black/20 px-3 py-2" open={step.status !== "succeeded"}>
                      <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-mutedInk">output excerpt</summary>
                      <pre className="mt-3 whitespace-pre-wrap font-sans text-[11px] leading-6 text-ink">{step.output_excerpt}</pre>
                    </details>
                  ) : null}
                  {artifacts.length ? <div className="mt-3 grid gap-3 md:grid-cols-2">{artifacts.map((artifact, index) => renderArtifact(artifact, index))}</div> : null}
                </div>
              </details>
            );
          })}
        </div>
      </SectionCard>

      <SectionCard title="What was found" aside={<span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{evidenceItems.length} evidence items</span>}>
        <div className="space-y-3">
          {failureSummary ? (
            <div className="border border-red-400/25 bg-red-500/10 px-4 py-4 shadow-[0_0_0_1px_rgba(248,113,113,0.08)]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-[10px] uppercase tracking-[0.18em] text-red-100">Failure summary</p>
                <div className="flex flex-wrap items-center gap-2">
                  {parentExecutionId ? (
                    <Link
                      href={`/runtime?execution=${parentExecutionId}`}
                      className="border border-red-300/20 bg-black/20 px-2.5 py-2 text-[10px] uppercase tracking-[0.18em] text-red-100"
                    >
                      Audit parent runtime
                    </Link>
                  ) : null}
                  <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${tone("failed")}`}>{failureLabel}</span>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="border border-red-300/20 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-red-100">Why it failed</span>
                {primaryFailureTarget ? <span className="border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-ink">Focus target ready</span> : null}
              </div>
              <p className="mt-3 text-sm leading-7 text-ink">{failureSummary}</p>
              <div className="mt-4 grid gap-3 xl:grid-cols-2">
                {primaryFailureTarget ? (
                  <div className="border border-white/10 bg-black/20 px-3 py-3">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-red-100">Fix this first</p>
                    <p className="mt-2 break-all text-xs leading-6 text-ink">{primaryFailureTarget}</p>
                  </div>
                ) : null}
                {groundedReasoning.length ? (
                  <div className="border border-white/10 bg-black/20 px-3 py-3">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-red-100">Why this likely failed</p>
                    <ul className="mt-2 space-y-2 text-xs leading-6 text-ink">
                      {groundedReasoning.map((item) => (
                        <li key={item}>- {item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
              {stderrHighlights.length ? (
                <details className="mt-4 border border-red-400/20 bg-black/20 px-3 py-2">
                  <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-red-100">stderr highlights</summary>
                  <ul className="mt-3 space-y-2 text-xs leading-6 text-red-100">
                    {stderrHighlights.map((item) => (
                      <li key={item}>- {item}</li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </div>
          ) : null}
          {evidenceItems.map((item) => renderEvidence(item, runtimeIndex))}
        </div>
      </SectionCard>

      <SectionCard
        title="Reflection"
        aside={
          <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(reflectionSummary?.triggered ? "degraded" : "ready")}`}>
            {reflectionSummary?.triggered ? "follow-up probe" : "no follow-up"}
          </span>
        }
      >
        <div className="space-y-3">
          {reflectionSummary?.summary ? <p className="text-sm leading-7 text-ink">{reflectionSummary.summary}</p> : <p className="text-sm leading-7 text-mutedInk">No reflection pass was needed for this turn.</p>}
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            <StepMeta label="Triggered" value={reflectionSummary ? (reflectionSummary.triggered ? "yes" : "no") : "no"} />
            <StepMeta label="Confidence" value={reflectionSummary?.confidence ?? null} />
            <StepMeta label="Reason" value={trace.reflection_reason ?? reflectionSummary?.reason ?? null} />
            <StepMeta label="Next probe" value={trace.reflection_next_probe ?? reflectionSummary?.next_probe ?? null} />
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Recommended next step">
        <ul className="space-y-2 text-sm leading-7 text-ink">
          {(trace.recommended_next_actions ?? []).map((item) => (
            <li key={item.label}>
              - {item.label}
              {item.reason ? <span className="text-mutedInk"> - {item.reason}</span> : null}
            </li>
          ))}
        </ul>
      </SectionCard>

      {trace.proposal ? (
        <SectionCard title="Proposal output" aside={<span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone("warn")}`}>not applied</span>}>
          <p className="text-sm leading-7 text-ink">{trace.proposal.summary}</p>
          {primaryFailureTarget || primaryGroundedTarget?.value ? (
            <div className="mt-3 border border-amber-300/20 bg-amber-500/5 px-3 py-3">
              <p className="text-[10px] uppercase tracking-[0.18em] text-amber-100">Focus target</p>
              <p className="mt-2 break-all text-xs leading-6 text-ink">{primaryFailureTarget ?? primaryGroundedTarget?.value}</p>
            </div>
          ) : null}
          {trace.proposal.patch_summary ? <p className="mt-4 text-xs leading-6 text-mutedInk">{trace.proposal.patch_summary}</p> : null}
          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <details className="border border-white/5 bg-black/20 px-3 py-3" open>
              <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-mutedInk">Affected files ({trace.proposal.targets.length})</summary>
              <ul className="mt-3 space-y-2 text-xs leading-6 text-ink">
                {trace.proposal.targets.map((target) => (
                  <li key={`${target.file_path}-${target.reason}`}>
                    - {target.file_path}
                    <span className="text-mutedInk"> - {target.reason}</span>
                  </li>
                ))}
              </ul>
            </details>
            <details className="border border-white/5 bg-black/20 px-3 py-3">
              <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-mutedInk">Suggested commands ({trace.proposal.suggested_commands.length})</summary>
              <ul className="mt-3 space-y-2 text-xs leading-6 text-ink">
                {trace.proposal.suggested_commands.map((command) => (
                  <li key={command}>- {command}</li>
                ))}
              </ul>
            </details>
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}
