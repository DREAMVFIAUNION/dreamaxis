"use client";

import { useEffect, useMemo, useRef } from "react";
import type { SkillInvocationSummary } from "@dreamaxis/client";
import { motion } from "framer-motion";
import { operatorCardMotion } from "@/lib/operator-motion";

function statusTone(value?: string | null, active = false) {
  if (active) return "border-cyan-400/35 bg-cyan-500/10 shadow-[inset_3px_0_0_rgba(34,211,238,0.9)]";
  const v = (value ?? "").toLowerCase();
  if (v.includes("fail") || v.includes("error")) return "border-red-400/20 bg-red-500/5";
  if (v.includes("approval") || v.includes("running") || v.includes("queued") || v.includes("planned")) return "border-amber-300/20 bg-amber-500/5";
  return "border-white/5 bg-black/20";
}

function resolveStepId(step: SkillInvocationSummary, index: number) {
  return step.runtime_execution_id ?? `${step.title}-${index}`;
}

export function ActiveStepPin({
  steps,
  activeStepId,
}: {
  steps: SkillInvocationSummary[];
  activeStepId?: string | null;
}) {
  const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const currentId = useMemo(() => {
    if (activeStepId) return activeStepId;
    const active = steps.find((step) => {
      const status = String(step.status ?? "").toLowerCase();
      return status.includes("running") || status.includes("queued") || status.includes("planned") || status.includes("fail");
    });
    return active ? resolveStepId(active, steps.indexOf(active)) : null;
  }, [activeStepId, steps]);

  useEffect(() => {
    if (!currentId) return;
    itemRefs.current[currentId]?.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
  }, [currentId]);

  return (
    <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
      {steps.map((step, index) => {
        const id = resolveStepId(step, index);
        const isActive = id === currentId;
        return (
          <motion.div
            key={id}
            layout
            {...operatorCardMotion}
            ref={(node) => {
              itemRefs.current[id] = node;
            }}
            className={`border px-3 py-3 transition ${statusTone(step.status, isActive)}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] uppercase tracking-[0.18em] text-signal">{isActive ? "Active step" : `Step ${index + 1}`}</span>
              <span className="border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk">{String(step.status ?? "ready")}</span>
              <span className="text-[10px] uppercase tracking-[0.18em] text-mutedInk">{step.kind}</span>
            </div>
            <p className="mt-2 text-sm font-semibold text-ink">{step.title}</p>
            <p className="mt-2 text-xs leading-6 text-mutedInk">{step.summary || step.output_excerpt || "No step summary yet."}</p>
          </motion.div>
        );
      })}
    </div>
  );
}
