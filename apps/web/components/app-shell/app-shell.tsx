import { AuthGuard } from "@/components/app-shell/auth-guard";
import { SidebarNav } from "@/components/app-shell/sidebar-nav";
import { TopNav } from "@/components/app-shell/top-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="min-h-screen bg-graphite text-ink">
        <div className="flex min-h-screen">
          <SidebarNav />
          <div className="flex min-h-screen flex-1 flex-col">
            <TopNav />
            <main className="flex-1 px-4 py-4 md:px-6 md:py-6">{children}</main>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
