"use client";

import { PanelCard } from "@/components/cards/panel-card";
import { StreamMessage } from "@/components/chat/stream-message";
import { RichContentRenderer } from "@/components/rich-content/rich-content-renderer";
import { cn } from "@/lib/utils";

type RichTextAcceptanceFixtures = {
  chatStreaming: string;
  chatMarkdown: string;
  chatCode: string;
  chatMath: string;
  chatMermaidOk: string;
  chatMermaidBad: string;
  chatHtmlEscape: string;
  operatorPlanSummary: string;
  operatorFailureSummary: string;
  runtimeExecutionSummary: string;
  runtimeApprovalSummary: string;
  runtimeRawLog: string;
};

const shotFrameClassName = "rounded-2xl border border-white/10 bg-[#111111] p-4 shadow-[0_24px_60px_rgba(0,0,0,0.35)]";

function Shot({
  shot,
  title,
  children,
  captureTarget = false,
  targetClassName,
}: {
  shot: string;
  title: string;
  children: React.ReactNode;
  captureTarget?: boolean;
  targetClassName?: string;
}) {
  const body = (
    <>
      <div className="mb-4 border-b border-white/10 pb-3">
        <p className="text-[10px] uppercase tracking-[0.24em] text-signal">{shot}.png</p>
        <h2 className="mt-2 text-lg font-black uppercase tracking-[0.08em] text-ink">{title}</h2>
      </div>
      {children}
    </>
  );

  if (captureTarget) {
    return (
      <section id={shot} className="flex justify-center">
        <div
          data-shot-target={shot}
          className={cn(shotFrameClassName, "w-[628px] max-w-[628px]", targetClassName)}
        >
          {body}
        </div>
      </section>
    );
  }

  return (
    <section
      id={shot}
      data-shot={shot}
      className={cn(shotFrameClassName, targetClassName)}
    >
      {body}
    </section>
  );
}

export function RichTextV1AcceptanceScreen({ fixtures }: { fixtures: RichTextAcceptanceFixtures }) {
  const narrowViewportContent = [
    fixtures.chatMarkdown,
    fixtures.chatMath,
    fixtures.chatCode.split("```python")[0].trim(),
  ].join("\n\n");

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(0,212,255,0.08),transparent_28%),linear-gradient(180deg,#151515_0%,#101010_100%)] px-6 py-8 text-ink">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-white/10 bg-black/30 px-6 py-6">
          <p className="text-[10px] uppercase tracking-[0.3em] text-signal">DreamAxis acceptance</p>
          <h1 className="mt-2 text-3xl font-black uppercase tracking-[0.08em] text-ink">Rich Text v1 screenshot harness</h1>
          <p className="mt-3 max-w-4xl text-sm leading-7 text-mutedInk">
            This page is driven only by fixed fixtures from docs/acceptance/rich-text-v1/fixtures so the pre-main screenshot pass stays deterministic.
          </p>
        </header>

        <div className="grid gap-6 xl:grid-cols-2">
          <Shot shot="chat-01-streaming-rich" title="Streaming rich message" captureTarget>
            <StreamMessage role="assistant" content={fixtures.chatStreaming} pending />
          </Shot>

          <Shot shot="chat-02-markdown-basics" title="Markdown basics" captureTarget>
            <StreamMessage role="assistant" content={fixtures.chatMarkdown} />
          </Shot>

          <Shot shot="chat-03-code-highlight" title="Code highlight coverage" captureTarget>
            <StreamMessage role="assistant" content={fixtures.chatCode} />
          </Shot>

          <Shot shot="chat-04-math-katex-all-syntax" title="Math / KaTeX coverage" captureTarget>
            <StreamMessage role="assistant" content={fixtures.chatMath} />
          </Shot>

          <Shot shot="chat-05-mermaid-success" title="Mermaid success" captureTarget>
            <StreamMessage role="assistant" content={fixtures.chatMermaidOk} />
          </Shot>

          <Shot shot="chat-06-mermaid-fallback-with-src" title="Mermaid fallback with source" captureTarget>
            <StreamMessage role="assistant" content={fixtures.chatMermaidBad} />
          </Shot>

          <Shot shot="chat-07-html-escaped" title="Unsafe HTML stays escaped" captureTarget>
            <StreamMessage role="assistant" content={fixtures.chatHtmlEscape} />
          </Shot>

          <Shot shot="chat-08-narrow-viewport" title="Narrow viewport (375px)" captureTarget>
            <div className="mx-auto w-[375px] max-w-full">
              <StreamMessage role="assistant" content={narrowViewportContent} />
            </div>
          </Shot>

          <Shot shot="operator-01-plan-summary-rich" title="Operator plan summary rich text">
            <PanelCard eyebrow="Operator acceptance" title="Plan summary surface">
              <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-4 text-sm text-ink">
                <RichContentRenderer content={fixtures.operatorPlanSummary} compact />
              </div>
            </PanelCard>
          </Shot>

          <Shot shot="operator-02-failure-summary-rich" title="Operator failure summary rich text">
            <PanelCard eyebrow="Operator acceptance" title="Failure summary surface">
              <div className="rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-4 text-sm text-red-100">
                <RichContentRenderer content={fixtures.operatorFailureSummary} compact />
              </div>
            </PanelCard>
          </Shot>

          <Shot shot="runtime-01-execution-summary-rich" title="Runtime execution summary rich text">
            <PanelCard eyebrow="Runtime acceptance" title="Execution summary surface">
              <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-4 text-sm text-ink">
                <RichContentRenderer content={fixtures.runtimeExecutionSummary} compact />
              </div>
            </PanelCard>
          </Shot>

          <Shot shot="runtime-02-approval-summary-rich" title="Runtime approval summary rich text">
            <PanelCard eyebrow="Runtime acceptance" title="Approval summary surface">
              <div className="rounded-xl border border-amber-300/20 bg-amber-500/10 px-4 py-4 text-sm text-amber-100">
                <RichContentRenderer content={fixtures.runtimeApprovalSummary} compact />
              </div>
            </PanelCard>
          </Shot>

          <div className="xl:col-span-2">
            <Shot shot="runtime-03-raw-logs-monospace" title="Runtime raw logs stay monospace">
              <PanelCard eyebrow="Runtime acceptance" title="Raw payload / logs surface">
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-black/30 p-4 font-mono text-xs leading-6 text-ink">
                  {fixtures.runtimeRawLog}
                </pre>
              </PanelCard>
            </Shot>
          </div>
        </div>
      </div>
    </div>
  );
}
