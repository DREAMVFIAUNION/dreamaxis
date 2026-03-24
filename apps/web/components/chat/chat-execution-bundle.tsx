"use client";

import Link from "next/link";
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

  return (
    <div key={`${evidence.title}-${evidence.runtime_execution_id ?? evidence.content}`} className="border border-white/5 bg-black/30 px-3 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-ink">{evidence.title}</p>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-signal">{evidence.type}</p>
        </div>
        {evidence.runtime_execution_id ? (
          <Link href={`/runtime?execution=${evidence.runtime_execution_id}`} className="text-[10px] uppercase tracking-[0.18em] text-signal">
            Open runtime
          </Link>
        ) : null}
      </div>
      <p className="mt-2 text-xs leading-6 text-mutedInk">{evidence.content}</p>
      <div className="mt-3 grid gap-2 text-[11px] text-mutedInk md:grid-cols-2">
        {evidence.path ? <p>path: {evidence.path}</p> : null}
        {evidence.current_url ? <p>url: {evidence.current_url}</p> : null}
        {typeof evidence.exit_code === "number" ? <p>exit: {evidence.exit_code}</p> : null}
        {evidence.label ? <p>label: {evidence.label}</p> : null}
      </div>
      {evidence.stderr_excerpt ? (
        <details className="mt-3 border border-red-400/20 bg-red-500/5 px-3 py-2">
          <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-red-200">stderr excerpt</summary>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-[11px] leading-6 text-red-200">{evidence.stderr_excerpt}</pre>
        </details>
      ) : null}
      {artifacts.length ? <div className="mt-3 grid gap-3 md:grid-cols-2">{artifacts.map((artifact, index) => renderArtifact(artifact, index))}</div> : null}
    </div>
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
  const failureSummary = trace.failure_summary?.trim();
  const failureType = trace.failure_classification?.trim() ?? "";
  const primaryFailureTarget = trace.primary_failure_target?.trim();
  const stderrHighlights = (trace.stderr_highlights ?? []).filter(Boolean);
  const groundedReasoning = (trace.grounded_next_step_reasoning ?? []).filter(Boolean);
  const failureLabel = FAILURE_TYPE_LABELS[failureType] ?? (failureType ? failureType.replaceAll("_", " ") : "Unknown");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(currentMode)}`}>Mode / {modeLabel(currentMode)}</span>
        <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(trace.trace_summary?.status)}`}>Bundle / {bundleId}</span>
        <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(readiness(trace))}`}>Readiness / {readiness(trace)}</span>
        {parentExecutionId ? (
          <Link href={`/runtime?execution=${parentExecutionId}`} className="border border-white/10 px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-signal">
            Parent runtime
          </Link>
        ) : null}
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <div className="border border-white/5 bg-black/25 px-3 py-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-signal">Intent / plan</p>
          <ul className="mt-3 space-y-2 text-sm leading-7 text-ink">
            {trace.intent_plan.map((item) => (
              <li key={item}>- {item}</li>
            ))}
          </ul>
        </div>
        <div className="border border-white/5 bg-black/25 px-3 py-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-signal">Recommended next step</p>
          <ul className="mt-3 space-y-2 text-sm leading-7 text-ink">
            {(trace.recommended_next_actions ?? []).map((item) => (
              <li key={item.label}>
                - {item.label}
                {item.reason ? <span className="text-mutedInk"> - {item.reason}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border border-white/5 bg-black/25 px-3 py-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-signal">What ran</p>
          <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{(trace.steps ?? []).length} child executions</span>
        </div>
        <div className="mt-3 space-y-3">
          {(trace.steps ?? []).filter((step) => step.runtime_execution_id).map((step) => {
            const runtime = step.runtime_execution_id ? runtimeIndex.get(step.runtime_execution_id) : null;
            const artifacts = toArtifacts(step.artifact_summaries).length ? toArtifacts(step.artifact_summaries) : toArtifacts(runtime?.artifacts_json);
            return (
              <div key={step.runtime_execution_id} className="border border-white/5 bg-black/30 px-3 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-ink">{step.title}</p>
                      <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${tone(step.status)}`}>{step.status}</span>
                      <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{step.kind}</span>
                    </div>
                    <p className="mt-2 text-xs leading-6 text-mutedInk">{step.summary}</p>
                  </div>
                  <div className="text-right">
                    {step.runtime_execution_id ? (
                      <Link href={`/runtime?execution=${step.runtime_execution_id}`} className="text-[10px] uppercase tracking-[0.18em] text-signal">
                        Open runtime
                      </Link>
                    ) : null}
                  </div>
                </div>
                <div className="mt-3 grid gap-2 text-[11px] text-mutedInk md:grid-cols-2">
                  <p>target: {step.current_url ?? (typeof step.command_preview === "string" ? step.command_preview : step.command_preview ? JSON.stringify(step.command_preview) : "--")}</p>
                  <p>exit: {step.exit_code ?? "--"}</p>
                  <p>session: {step.runtime_session_id ?? "--"}</p>
                  <p>artifacts: {artifacts.length}</p>
                </div>
                {step.output_excerpt ? (
                  <pre className="mt-3 whitespace-pre-wrap font-sans text-[11px] leading-6 text-ink">{step.output_excerpt}</pre>
                ) : null}
                {artifacts.length ? <div className="mt-3 grid gap-3 md:grid-cols-2">{artifacts.map((artifact, index) => renderArtifact(artifact, index))}</div> : null}
              </div>
            );
          })}
        </div>
      </div>

      <div className="border border-white/5 bg-black/25 px-3 py-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-signal">What was found</p>
          <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{evidenceItems.length} evidence items</span>
        </div>
        <div className="mt-3 space-y-3">
          {failureSummary ? (
            <div className="border border-red-400/25 bg-red-500/10 px-3 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[10px] uppercase tracking-[0.18em] text-red-100">Failure summary</p>
                <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${tone("failed")}`}>{failureLabel}</span>
              </div>
              <p className="mt-3 text-sm leading-7 text-ink">{failureSummary}</p>
              {primaryFailureTarget ? (
                <div className="mt-4 border border-white/10 bg-black/20 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-[0.18em] text-red-100">Fix this first</p>
                  <p className="mt-2 break-all text-xs leading-6 text-ink">{primaryFailureTarget}</p>
                </div>
              ) : null}
              {groundedReasoning.length ? (
                <div className="mt-4">
                  <p className="text-[10px] uppercase tracking-[0.18em] text-red-100">Why this likely failed</p>
                  <ul className="mt-2 space-y-2 text-xs leading-6 text-ink">
                    {groundedReasoning.map((item) => (
                      <li key={item}>- {item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
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
      </div>

      {trace.proposal ? (
        <div className="border border-white/5 bg-black/25 px-3 py-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-signal">Proposal output</p>
            <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone("warn")}`}>not applied</span>
          </div>
          <p className="mt-3 text-sm leading-7 text-ink">{trace.proposal.summary}</p>
          {primaryFailureTarget ? (
            <p className="mt-3 text-xs leading-6 text-mutedInk">
              Focus target: <span className="text-ink">{primaryFailureTarget}</span>
            </p>
          ) : null}
          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <div>
              <p className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">Affected files</p>
              <ul className="mt-2 space-y-2 text-xs leading-6 text-ink">
                {trace.proposal.targets.map((target) => (
                  <li key={`${target.file_path}-${target.reason}`}>
                    - {target.file_path}
                    <span className="text-mutedInk"> - {target.reason}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">Suggested commands</p>
              <ul className="mt-2 space-y-2 text-xs leading-6 text-ink">
                {trace.proposal.suggested_commands.map((command) => (
                  <li key={command}>- {command}</li>
                ))}
              </ul>
            </div>
          </div>
          {trace.proposal.patch_summary ? <p className="mt-4 text-xs leading-6 text-mutedInk">{trace.proposal.patch_summary}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
