"use client";

import { Check, ChevronDown, ChevronUp, Copy } from "lucide-react";
import { useMemo, useState } from "react";
import { hljs } from "@/lib/highlight";
import { cn } from "@/lib/utils";

function escapeHtml(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

export function CodeBlock({ code, language }: { code: string; language?: string | null }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const lines = useMemo(() => code.split(/\r?\n/), [code]);
  const collapsible = lines.length > 18;

  const highlighted = useMemo(() => {
    const normalized = (language ?? "").trim().toLowerCase();
    try {
      if (normalized && hljs.getLanguage(normalized)) {
        return hljs.highlight(code, { language: normalized }).value;
      }
      return escapeHtml(code);
    } catch {
      return escapeHtml(code);
    }
  }, [code, language]);

  async function handleCopy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-black/40">
      <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.03] px-3 py-2">
        <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{language || "code"}</span>
        <div className="flex items-center gap-1">
          {collapsible ? (
            <button
              type="button"
              onClick={() => setExpanded((current) => !current)}
              className="rounded border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk transition hover:border-white/20 hover:text-ink"
            >
              <span className="inline-flex items-center gap-1">{expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}{expanded ? "Collapse" : "Expand"}</span>
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => void handleCopy()}
            className="rounded border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk transition hover:border-white/20 hover:text-ink"
          >
            <span className="inline-flex items-center gap-1">{copied ? <Check size={12} /> : <Copy size={12} />}{copied ? "Copied" : "Copy"}</span>
          </button>
        </div>
      </div>
      <div className="relative">
        <pre className={cn("dx-rich-code m-0 overflow-x-auto p-4 text-[13px] leading-6 text-ink", collapsible && !expanded && "max-h-72 overflow-hidden")}>
          <code dangerouslySetInnerHTML={{ __html: highlighted }} />
        </pre>
        {collapsible && !expanded ? <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[#111111] to-transparent" /> : null}
      </div>
    </div>
  );
}
