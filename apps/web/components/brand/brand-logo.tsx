import Image from "next/image";
import { cn } from "@/lib/utils";

export function BrandLogo({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative h-8 w-8 overflow-hidden">
        <Image src="/brand/icon.png" alt="DreamAxis" fill className="object-contain" priority />
      </div>
      {!compact ? (
        <div className="flex flex-col leading-none">
          <span className="font-headline text-sm font-black uppercase tracking-[0.2em] text-signal">DreamAxis</span>
          <span className="text-[10px] uppercase tracking-[0.3em] text-mutedInk">Execution Platform</span>
        </div>
      ) : null}
    </div>
  );
}
