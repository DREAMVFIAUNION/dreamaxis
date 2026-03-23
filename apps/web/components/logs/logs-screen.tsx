"use client";

import { useEffect, useState } from "react";
import type { ExecutionAnnotation, Workspace } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { ExecutionTimeline } from "@/components/execution/execution-timeline";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

export function LogsScreen() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [runtimeType, setRuntimeType] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [items, setItems] = useState<ExecutionAnnotation[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadEvents(activeWorkspaceId: string, nextRuntimeType?: string, nextKind?: string) {
    const token = getAuthToken();
    if (!token || !activeWorkspaceId) return;
    setError(null);
    try {
      const response = await apiClient.getLogEvents(token, {
        workspace_id: activeWorkspaceId,
        runtime_type: (nextRuntimeType ?? runtimeType) || undefined,
        kind: (nextKind ?? kindFilter) || undefined,
      });
      setItems(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load log events");
    }
  }

  useEffect(() => {
    const token = getAuthToken();
    if (!token) return;
    (async () => {
      try {
        const workspaceRes = await apiClient.getWorkspaces(token);
        setWorkspaces(workspaceRes.data);
        const primaryWorkspaceId = workspaceRes.data[0]?.id ?? "";
        setWorkspaceId(primaryWorkspaceId);
        if (primaryWorkspaceId) await loadEvents(primaryWorkspaceId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load log workspace");
      }
    })();
  }, []);

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <PanelCard eyebrow="Execution logs" title="Workspace event stream">
          <div className="grid gap-4 md:grid-cols-3">
            <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Workspace
              <select
                value={workspaceId}
                onChange={async (event) => {
                  const nextWorkspaceId = event.target.value;
                  setWorkspaceId(nextWorkspaceId);
                  await loadEvents(nextWorkspaceId);
                }}
                className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
              >
                {workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Runtime type
              <select
                value={runtimeType}
                onChange={async (event) => {
                  setRuntimeType(event.target.value);
                  await loadEvents(workspaceId, event.target.value);
                }}
                className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
              >
                <option value="">All runtimes</option>
                <option value="cli">CLI</option>
                <option value="browser">Browser</option>
              </select>
            </label>
            <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Event kind
              <input
                value={kindFilter}
                onChange={(event) => setKindFilter(event.target.value)}
                onBlur={async () => {
                  await loadEvents(workspaceId, runtimeType, kindFilter);
                }}
                placeholder="command_finished, browser_action..."
                className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
              />
            </label>
          </div>
          {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
        </PanelCard>

        <PanelCard eyebrow="Timeline" title="Cross-execution annotations">
          <ExecutionTimeline
            items={items}
            emptyCopy="No events matched this filter. Trigger a chat, CLI skill, or browser skill to populate the workspace event stream."
          />
        </PanelCard>
      </div>
    </AppShell>
  );
}
