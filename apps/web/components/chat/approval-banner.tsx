"use client";

import Link from "next/link";
import type { DesktopActionApproval, DesktopActionRequest } from "@dreamaxis/client";
import { motion } from "framer-motion";
import { operatorStripMotion } from "@/lib/operator-motion";

export function ApprovalBanner({
  approval,
  actions,
  operatorPlanId,
  pending = false,
  onReview,
}: {
  approval?: DesktopActionApproval | null;
  actions?: DesktopActionRequest[] | null;
  operatorPlanId?: string | null;
  pending?: boolean;
  onReview?: ((decision: "approved" | "denied") => void | Promise<void>) | null;
}) {
  if (!approval || approval.status !== "approval_required") return null;
  const primaryAction = actions?.[0];
  return (
    <motion.div
      layout
      {...operatorStripMotion}
      className="panel sticky top-[10.5rem] z-20 border border-amber-300/30 bg-amber-500/12 px-4 py-4"
    >
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="border border-amber-300/30 bg-black/20 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-amber-100">
              Approval required
            </span>
            {primaryAction?.action ? (
              <span className="border border-white/10 bg-black/20 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-mutedInk">
                {primaryAction.action.replaceAll("_", " ")}
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-sm font-semibold text-ink">{approval.summary}</p>
          <p className="mt-1 text-xs leading-6 text-amber-50/90">
            {primaryAction?.target_window || primaryAction?.target_app || primaryAction?.target_label || "Desktop surface"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {operatorPlanId ? (
            <Link href={`/operator?plan=${operatorPlanId}`} className="border border-white/10 bg-black/20 px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-ink">
              Open plan
            </Link>
          ) : null}
          {onReview ? (
            <>
              <button
                type="button"
                disabled={pending}
                onClick={() => void onReview("approved")}
                className="border border-emerald-400/30 bg-emerald-500/15 px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {pending ? "Running..." : "Approve + run"}
              </button>
              <button
                type="button"
                disabled={pending}
                onClick={() => void onReview("denied")}
                className="border border-red-400/30 bg-red-500/10 px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-red-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Deny
              </button>
            </>
          ) : null}
        </div>
      </div>
    </motion.div>
  );
}
