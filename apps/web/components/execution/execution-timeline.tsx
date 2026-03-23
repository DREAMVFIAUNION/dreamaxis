"use client";

import Link from "next/link";
import type { ExecutionAnnotation } from "@dreamaxis/client";

function statusTone(status: string) {
  if (status === "failed") return "text-red-300 border-red-400/20 bg-red-500/10";
  if (status === "running") return "text-amber-200 border-amber-300/20 bg-amber-500/10";
  if (status === "queued" || status === "ready") return "text-signal border-signal/20 bg-signal/10";
  return "text-emerald-300 border-emerald-400/20 bg-emerald-500/10";
}

function kindLabel(kind: string) {
  return kind.replaceAll("_", " ");
}

function formatDuration(durationMs?: number | null) {
  if (!durationMs) return null;
  return durationMs < 1000 ? `${durationMs} ms` : `${(durationMs / 1000).toFixed(2)} s`;
}

function renderPreview(value: Record<string, unknown> | string | null | undefined) {
  if (!value) return null;
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function renderArtifact(artifact: Record<string, unknown>, index: number) {
  const dataUrl = typeof artifact.data_url === "string" ? artifact.data_url : null;
  if (dataUrl) {
    return <img key={index} src={dataUrl} alt="execution artifact" className="mt-3 w-full border border-white/5" />;
  }
  return (
    <pre key={index} className="mt-3 whitespace-pre-wrap font-sans text-[11px] leading-6 text-ink">
      {JSON.stringify(artifact, null, 2)}
    </pre>
  );
}

export function ExecutionTimeline({
  items,
  emptyCopy,
  resolveArtifacts,
}: {
  items: ExecutionAnnotation[];
  emptyCopy?: string;
  resolveArtifacts?: (item: ExecutionAnnotation) => Array<Record<string, unknown>>;
}) {
  if (!items.length) {
    return <p className="text-sm text-mutedInk">{emptyCopy ?? "No execution activity recorded yet."}</p>;
  }

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const artifacts = resolveArtifacts ? resolveArtifacts(item) : [];
        return (
          <div key={item.id} className="border border-white/5 bg-black/25 px-4 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-ink">{item.title}</p>
                  <span className={`border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${statusTone(item.status)}`}>
                    {item.status}
                  </span>
                  <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{kindLabel(item.kind)}</span>
                </div>
                <p className="mt-2 text-xs leading-6 text-mutedInk">{item.summary || "No summary available."}</p>
                {item.target_label ? <p className="mt-2 text-[11px] uppercase tracking-[0.15em] text-signal">{item.target_label}</p> : null}
              </div>
              <div className="text-right text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                {item.duration_ms ? <p>{formatDuration(item.duration_ms)}</p> : null}
                {item.runtime_execution_id ? (
                  <Link href={`/runtime?execution=${item.runtime_execution_id}`} className="mt-2 inline-block text-signal">
                    Open runtime
                  </Link>
                ) : null}
              </div>
            </div>
            {item.payload_preview ? (
              <pre className="mt-3 whitespace-pre-wrap font-sans text-[11px] leading-6 text-ink">{renderPreview(item.payload_preview)}</pre>
            ) : null}
            {artifacts.length ? <div className="mt-1">{artifacts.map((artifact, index) => renderArtifact(artifact, index))}</div> : null}
            {item.raw_payload ? (
              <details className="mt-3 border-t border-white/5 pt-3">
                <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-mutedInk">Raw payload</summary>
                <pre className="mt-3 whitespace-pre-wrap font-sans text-[11px] leading-6 text-mutedInk">
                  {JSON.stringify(item.raw_payload, null, 2)}
                </pre>
              </details>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
