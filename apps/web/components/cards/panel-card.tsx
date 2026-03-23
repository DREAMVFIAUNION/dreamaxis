import { cn } from "@/lib/utils";

export function PanelCard({
  title,
  eyebrow,
  children,
  className,
}: {
  title?: string;
  eyebrow?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("panel signal-line relative overflow-hidden px-5 py-5", className)}>
      {(eyebrow || title) && (
        <header className="mb-4 pl-4">
          {eyebrow ? <p className="text-[10px] uppercase tracking-[0.3em] text-signal">{eyebrow}</p> : null}
          {title ? <h2 className="mt-2 font-headline text-xl font-black uppercase tracking-[0.08em]">{title}</h2> : null}
        </header>
      )}
      <div className="pl-4">{children}</div>
    </section>
  );
}
