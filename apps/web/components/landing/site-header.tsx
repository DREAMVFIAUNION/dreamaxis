import Link from "next/link";
import { BrandLogo } from "@/components/brand/brand-logo";

const items = ["Features", "Models", "Runtimes", "Docs", "GitHub"];

export function SiteHeader() {
  return (
    <header className="mx-auto flex w-full max-w-7xl items-center justify-between border-b border-white/5 px-6 py-5">
      <BrandLogo />
      <nav className="hidden items-center gap-8 text-[11px] uppercase tracking-[0.24em] text-mutedInk md:flex">
        {items.map((item) => (
          <a key={item} href="#" className="transition hover:text-ink">
            {item}
          </a>
        ))}
      </nav>
      <Link href="/login" className="text-[11px] font-semibold uppercase tracking-[0.24em] text-signal">
        Sign In
      </Link>
    </header>
  );
}
