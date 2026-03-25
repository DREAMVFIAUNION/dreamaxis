import type { KnowledgeChunkReference } from "@dreamaxis/client";
import { RichContentRenderer } from "@/components/rich-content/rich-content-renderer";
import { cn } from "@/lib/utils";

type MessageRole = "system" | "user" | "assistant";

export function StreamMessage({
  role,
  content,
  pending = false,
  sources,
  details,
}: {
  role: MessageRole;
  content: string;
  pending?: boolean;
  sources?: KnowledgeChunkReference[] | null;
  details?: React.ReactNode;
}) {
  const hasStructuredBundle = role === "assistant" && Boolean(details);
  const renderContent = (
    <RichContentRenderer content={content} streaming={pending} />
  );

  return (
    <article
      className={cn(
        "panel flex flex-col gap-3 px-5 py-4",
        role === "user" ? "border-signal/20 bg-signal/5" : "border-white/5 bg-white/[0.02]",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-[0.3em] text-signal">{role}</span>
        {pending ? <span className="text-[10px] uppercase tracking-[0.3em] text-mutedInk">streaming</span> : null}
      </div>

      {hasStructuredBundle ? <div className="border-t border-white/5 pt-3">{details}</div> : null}

      {hasStructuredBundle ? (
        <details className="border border-white/5 bg-black/20 px-4 py-3">
          <summary className="cursor-pointer text-[10px] uppercase tracking-[0.22em] text-mutedInk">
            Model synthesis / raw assistant response
          </summary>
          <div className="mt-3">{renderContent}</div>
        </details>
      ) : (
        <div>{renderContent}</div>
      )}

      {sources?.length ? (
        <div className="border-t border-white/5 pt-3">
          <p className="text-[10px] uppercase tracking-[0.24em] text-mutedInk">Knowledge sources</p>
          <div className="mt-3 flex flex-col gap-2">
            {sources.map((source) => (
              <div key={source.chunk_id} className="border border-white/5 bg-black/25 px-3 py-3 text-xs text-mutedInk">
                <div className="flex items-center justify-between gap-4">
                  <span className="font-semibold text-ink">{source.document_name}</span>
                  <span className="uppercase tracking-[0.18em] text-signal">{Math.round(source.score * 100)}%</span>
                </div>
                <p className="mt-2 leading-6">{source.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}
