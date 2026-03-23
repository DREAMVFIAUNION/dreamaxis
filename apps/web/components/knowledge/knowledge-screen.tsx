"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { KnowledgeDocument, KnowledgePack, Workspace } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

function fmtDate(value?: string | null) {
  if (!value) return "--";
  return new Date(value).toLocaleString();
}

function getDocumentStatusLabel(document: KnowledgeDocument) {
  if (document.status === "ready" && document.error_message) {
    return "metadata only";
  }
  return document.status;
}

export function KnowledgeScreen() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [packs, setPacks] = useState<KnowledgePack[]>([]);
  const [sourceType, setSourceType] = useState<string>("");
  const [pending, setPending] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const readyCount = useMemo(() => documents.filter((item) => item.status === "ready").length, [documents]);

  async function refreshKnowledge(activeWorkspaceId: string, nextSourceType?: string) {
    const token = getAuthToken();
    if (!token || !activeWorkspaceId) return;
    const [docsRes, packsRes] = await Promise.all([
      apiClient.getKnowledgeDocumentsFiltered(token, { workspace_id: activeWorkspaceId, source_type: nextSourceType || sourceType || undefined }),
      apiClient.getKnowledgePacks(token, activeWorkspaceId),
    ]);
    setDocuments(docsRes.data);
    setPacks(packsRes.data);
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
        if (primaryWorkspaceId) await refreshKnowledge(primaryWorkspaceId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load knowledge module");
      }
    })();
  }, []);

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <PanelCard eyebrow="Knowledge Plane" title="Workspace document registry">
          <div className="grid gap-4 xl:grid-cols-[1fr_0.6fr_auto_auto] xl:items-end">
            <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Workspace
              <select
                value={workspaceId}
                onChange={async (event) => {
                  setWorkspaceId(event.target.value);
                  await refreshKnowledge(event.target.value);
                }}
                className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
              >
                {workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
              Source filter
              <select
                value={sourceType}
                onChange={async (event) => {
                  setSourceType(event.target.value);
                  await refreshKnowledge(workspaceId, event.target.value);
                }}
                className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
              >
                <option value="">All sources</option>
                <option value="user_upload">User uploads</option>
                <option value="builtin_pack">Builtin packs</option>
              </select>
            </label>
            <button
              type="button"
              disabled={syncing || !workspaceId}
              onClick={async () => {
                const token = getAuthToken();
                if (!token || !workspaceId) return;
                setSyncing(true);
                setError(null);
                try {
                  const response = await apiClient.syncKnowledgePacks(token, workspaceId);
                  setSuccess(`Synced ${response.data.synced_pack_count} packs / ${response.data.synced_document_count} documents`);
                  await refreshKnowledge(workspaceId);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Failed to sync builtin knowledge packs");
                } finally {
                  setSyncing(false);
                }
              }}
              className="border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-mutedInk"
            >
              {syncing ? "Syncing..." : "Sync builtin packs"}
            </button>
            <div className="border border-white/5 bg-black/25 px-4 py-4 text-xs uppercase tracking-[0.18em] text-mutedInk">
              <p>Ready docs</p>
              <p className="mt-2 text-2xl font-black text-ink">{readyCount}</p>
            </div>
          </div>
          <p className="mt-4 text-xs text-mutedInk">
            Upload your own txt / md / pdf files below, then combine them with builtin packs such as Playwright, Git, Docker, Python, Next.js, and DreamAxis architecture. Provider defaults live in <Link href="/settings/providers" className="text-signal">Provider Settings</Link>. Builtin pack metadata can sync without embeddings, but retrieval requires a valid embedding-capable provider connection.
          </p>
          <label className="mt-4 flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
            Upload txt / md / pdf
            <input
              type="file"
              accept=".txt,.md,.pdf"
              className="border border-white/10 bg-black/20 px-4 py-[11px] text-sm text-ink file:mr-4 file:border-0 file:bg-signal file:px-3 file:py-2 file:text-xs file:font-black file:uppercase file:tracking-[0.16em] file:text-black"
              onChange={async (event) => {
                const token = getAuthToken();
                const file = event.target.files?.[0];
                if (!token || !file || !workspaceId) return;
                setPending(true);
                setError(null);
                setSuccess(null);
                try {
                  const response = await apiClient.uploadKnowledgeDocument(token, workspaceId, file);
                  setSuccess(`Uploaded ${response.data.file_name}`);
                  await refreshKnowledge(workspaceId);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Upload failed");
                } finally {
                  setPending(false);
                  event.currentTarget.value = "";
                }
              }}
            />
          </label>
          {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
          {success ? <p className="mt-4 text-sm text-emerald-300">{success}</p> : null}
          {pending ? <p className="mt-4 text-sm text-signal">Processing upload and embeddings...</p> : null}
        </PanelCard>

        <div className="grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
          <PanelCard eyebrow="Builtin knowledge packs" title="Pack catalog">
            <div className="space-y-3">
              {packs.map((pack) => (
                <div key={pack.id} className="border border-white/5 bg-black/20 px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-ink">{pack.name}</p>
                    <span className="text-[10px] uppercase tracking-[0.18em] text-signal">{pack.version}</span>
                  </div>
                  <p className="mt-2 text-xs leading-6 text-mutedInk">{pack.description}</p>
                  <p className="mt-2 text-[11px] text-mutedInk">{pack.slug} / {pack.source_type}</p>
                </div>
              ))}
              {!packs.length ? <p className="text-sm text-mutedInk">No builtin knowledge packs synced yet.</p> : null}
            </div>
          </PanelCard>

          <PanelCard eyebrow="Document state" title="Indexed files and sources">
            <div className="overflow-hidden border border-white/5 bg-black/20">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="border-b border-white/5 text-[10px] uppercase tracking-[0.3em] text-mutedInk">
                  <tr>
                    <th className="px-4 py-4">Name</th>
                    <th className="px-4 py-4">Source</th>
                    <th className="px-4 py-4">Status</th>
                    <th className="px-4 py-4">Chunks</th>
                    <th className="px-4 py-4">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((document) => (
                    <tr key={document.id} className="border-b border-white/5 last:border-b-0 align-top">
                      <td className="px-4 py-4 font-semibold text-ink">
                        <p>{document.title ?? document.file_name}</p>
                        <p className="mt-1 text-xs font-normal text-mutedInk">{document.file_name}</p>
                        {document.error_message ? (
                          <p className={`mt-2 text-xs font-normal ${document.status === "failed" ? "text-red-300" : "text-amber-300"}`}>
                            {document.error_message}
                          </p>
                        ) : null}
                      </td>
                      <td className="px-4 py-4 text-mutedInk">
                        {document.source_type}
                        {document.knowledge_pack_slug ? <p className="mt-1 text-xs">{document.knowledge_pack_slug}</p> : null}
                      </td>
                      <td className="px-4 py-4 text-mutedInk">{getDocumentStatusLabel(document)}</td>
                      <td className="px-4 py-4 text-mutedInk">{document.chunk_count}</td>
                      <td className="px-4 py-4 text-mutedInk">{fmtDate(document.updated_at)}</td>
                    </tr>
                  ))}
                  {!documents.length ? (
                    <tr>
                      <td className="px-4 py-6 text-mutedInk" colSpan={5}>No knowledge documents available yet.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </PanelCard>
        </div>
      </div>
    </AppShell>
  );
}
