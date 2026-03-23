import { cn } from "@/lib/utils";

export function MetricCard({ label, value, hint, className }: { label: string; value: string; hint?: string; className?: string }) {
  return (
    <div className={cn("panel min-h-36 border-white/5 bg-white/[0.02] p-5", className)}>
      <p className="text-[10px] uppercase tracking-[0.28em] text-mutedInk">{label}</p>
      <p className="mt-6 font-headline text-4xl font-black tracking-tight text-ink">{value}</p>
      {hint ? <p className="mt-4 text-xs uppercase tracking-[0.2em] text-mutedInk">{hint}</p> : null}
    </div>
  );
}
