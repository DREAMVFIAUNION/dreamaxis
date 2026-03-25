"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, MessageSquareText, MonitorSmartphone, Database, Sparkles, Cpu, Wrench, ScrollText, Shield } from "lucide-react";
import { moduleNavigation } from "@dreamaxis/ui";
import { BrandLogo } from "@/components/brand/brand-logo";
import { cn } from "@/lib/utils";

const icons = [LayoutDashboard, MessageSquareText, MonitorSmartphone, Database, Sparkles, Cpu, Wrench, ScrollText, Shield];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-[92px] flex-col border-r border-white/5 bg-black/35 lg:flex">
      <div className="flex h-20 items-center justify-center border-b border-white/5">
        <BrandLogo compact />
      </div>
      <nav className="flex flex-1 flex-col gap-2 px-3 py-6">
        {moduleNavigation.map((item, index) => {
          const Icon = icons[index] ?? LayoutDashboard;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex min-h-16 flex-col items-center justify-center gap-2 border border-transparent bg-transparent text-[10px] uppercase tracking-[0.2em] text-mutedInk transition",
                active && "border-signal/25 bg-white/[0.03] text-ink",
              )}
            >
              <Icon className={cn("h-4 w-4", active ? "text-signal" : "text-mutedInk group-hover:text-signal")} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
