"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect, useId, useState } from "react";

let mermaidPromise: Promise<typeof import("mermaid")> | null = null;
let initialized = false;

async function getMermaid() {
  mermaidPromise ??= import("mermaid");
  const module = await mermaidPromise;
  const mermaid = module.default;
  if (!initialized) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "dark",
      themeVariables: {
        darkMode: true,
        background: "#111111",
        primaryColor: "#171717",
        primaryTextColor: "#f5f5f5",
        primaryBorderColor: "#303030",
        lineColor: "#9ca3af",
        secondaryColor: "#202020",
        tertiaryColor: "#262626",
        edgeLabelBackground: "#171717",
        fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
      },
    });
    initialized = true;
  }
  return mermaid;
}

export function MermaidBlock({ chart }: { chart: string }) {
  const id = useId();
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      try {
        const mermaid = await getMermaid();
        const result = await mermaid.render(`dreamaxis-mermaid-${id.replace(/[:]/g, "-")}`, chart);
        if (!cancelled) {
          setSvg(result.svg);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setSvg(null);
          setError(err instanceof Error ? err.message : "Mermaid render failed");
        }
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  if (error) {
    return (
      <div className="space-y-3 rounded-xl border border-amber-400/25 bg-amber-500/10 p-4">
        <div className="flex items-start gap-3 text-amber-100">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold">Mermaid render failed</p>
            <p className="mt-1 text-xs leading-6 text-amber-100/80">{error}</p>
          </div>
        </div>
        <details open className="rounded-lg border border-white/10 bg-black/30 p-3">
          <summary className="cursor-pointer text-[10px] uppercase tracking-[0.18em] text-amber-100">Source</summary>
          <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-ink">{chart}</pre>
        </details>
      </div>
    );
  }

  if (!svg) {
    return <div className="rounded-xl border border-white/10 bg-black/30 p-4 text-xs uppercase tracking-[0.18em] text-mutedInk">Rendering diagram...</div>;
  }

  return <div className="dx-rich-mermaid overflow-x-auto rounded-xl border border-white/10 bg-black/30 p-4" dangerouslySetInnerHTML={{ __html: svg }} />;
}
