"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type {
  Conversation,
  DiscoveredModel,
  KnowledgeChunkReference,
  Message,
  ProviderConnection,
  RuntimeExecution,
  SkillDefinition,
} from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { ChatComposer } from "@/components/chat/chat-composer";
import { StreamMessage } from "@/components/chat/stream-message";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

function formatDate(value?: string | null) {
  if (!value) return "--";
  return new Date(value).toLocaleString();
}

function formatDuration(value?: number | null) {
  if (!value) return "--";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

export function ChatScreen({ conversationId }: { conversationId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [skills, setSkills] = useState<SkillDefinition[]>([]);
  const [runtime, setRuntime] = useState<RuntimeExecution[]>([]);
  const [connections, setConnections] = useState<ProviderConnection[]>([]);
  const [connectionModels, setConnectionModels] = useState<DiscoveredModel[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState("");
  const [selectedModelName, setSelectedModelName] = useState("");
  const [configPending, setConfigPending] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSources, setLastSources] = useState<KnowledgeChunkReference[] | null>(null);
  const [lastRuntimeId, setLastRuntimeId] = useState<string | null>(null);
  const [composerPreset, setComposerPreset] = useState("");

  async function loadConnectionModels(token: string, connectionId: string) {
    if (!connectionId) {
      setConnectionModels([]);
      return;
    }
    try {
      const response = await apiClient.getProviderConnectionModels(token, connectionId);
      setConnectionModels(response.data);
    } catch {
      setConnectionModels([]);
    }
  }

  useEffect(() => {
    const token = getAuthToken();
    if (!token) return;

    (async () => {
      try {
        const [messageRes, conversationRes, runtimeRes, workspaceRes, connectionRes] = await Promise.all([
          apiClient.getMessages(token, conversationId),
          apiClient.getConversation(token, conversationId),
          apiClient.getRuntimeExecutions(token, { conversation_id: conversationId }),
          apiClient.getWorkspaces(token),
          apiClient.getProviderConnections(token),
        ]);
        const activeConversation = conversationRes.data;
        setMessages(messageRes.data);
        setConversation(activeConversation);
        setRuntime(runtimeRes.data);
        setConnections(connectionRes.data);
        setSelectedConnectionId(activeConversation.provider_connection_id ?? connectionRes.data[0]?.id ?? "");
        setSelectedModelName(activeConversation.model_name ?? connectionRes.data[0]?.default_model_name ?? "");

        if (activeConversation.provider_connection_id) {
          await loadConnectionModels(token, activeConversation.provider_connection_id);
        }

        if (activeConversation.workspace_id) {
          const skillsRes = await apiClient.getSkills(token, activeConversation.workspace_id);
          setSkills(skillsRes.data.filter((skill) => skill.enabled));
        } else if (workspaceRes.data.length > 0) {
          const skillsRes = await apiClient.getSkills(token, workspaceRes.data[0].id);
          setSkills(skillsRes.data.filter((skill) => skill.enabled));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load conversation");
      }
    })();
  }, [conversationId]);

  const ordered = useMemo(() => [...messages].sort((a, b) => a.created_at.localeCompare(b.created_at)), [messages]);
  const latestRuntime = runtime[0] ?? null;
  const selectedConnection = useMemo(
    () => connections.find((item) => item.id === selectedConnectionId) ?? null,
    [connections, selectedConnectionId],
  );

  return (
    <AppShell>
      <div className="mx-auto grid w-full max-w-7xl gap-6 xl:grid-cols-[1.45fr_0.85fr]">
        <section className="flex flex-col gap-4">
          <header className="panel px-6 py-6">
            <p className="text-[10px] uppercase tracking-[0.3em] text-signal">DreamAxis Command</p>
            <h1 className="mt-2 font-headline text-4xl font-black uppercase tracking-tight">Conversation Lane / {conversationId}</h1>
            <div className="mt-4 grid gap-3 text-xs uppercase tracking-[0.18em] text-mutedInk md:grid-cols-3">
              <div className="border border-white/5 bg-black/20 px-4 py-3">
                <p>Connection</p>
                <p className="mt-2 text-sm font-semibold text-ink">{conversation?.provider_connection_name ?? "Not configured"}</p>
              </div>
              <div className="border border-white/5 bg-black/20 px-4 py-3">
                <p>Model</p>
                <p className="mt-2 text-sm font-semibold text-ink">{conversation?.model_name ?? "Manual / Auto"}</p>
              </div>
              <div className="border border-white/5 bg-black/20 px-4 py-3">
                <p>Knowledge</p>
                <p className="mt-2 text-sm font-semibold text-ink">{conversation?.use_knowledge ? "Enabled" : "Optional"}</p>
              </div>
            </div>

            <div className="mt-5 grid gap-3 border border-white/5 bg-black/25 px-4 py-4 md:grid-cols-[1fr_1fr_auto]">
              <label className="flex flex-col gap-2 text-[10px] uppercase tracking-[0.2em] text-mutedInk">
                Provider connection
                <select
                  value={selectedConnectionId}
                  onChange={async (event) => {
                    const token = getAuthToken();
                    const nextConnectionId = event.target.value;
                    setSelectedConnectionId(nextConnectionId);
                    const nextConnection = connections.find((item) => item.id === nextConnectionId);
                    setSelectedModelName(nextConnection?.default_model_name ?? "");
                    if (token) await loadConnectionModels(token, nextConnectionId);
                  }}
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
                >
                  <option value="">Select connection</option>
                  {connections.map((connection) => (
                    <option key={connection.id} value={connection.id}>
                      {connection.name} / {connection.status}
                    </option>
                  ))}
                </select>
              </label>

              <div className="flex flex-col gap-2">
                <label className="text-[10px] uppercase tracking-[0.2em] text-mutedInk">Model name</label>
                <input
                  value={selectedModelName}
                  onChange={(event) => setSelectedModelName(event.target.value)}
                  placeholder="e.g. gpt-4.1-mini or free gateway model"
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
                />
                {connectionModels.length ? (
                  <select
                    value={selectedModelName}
                    onChange={(event) => setSelectedModelName(event.target.value)}
                    className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
                  >
                    <option value="">Pick discovered model</option>
                    {connectionModels
                      .filter((item) => item.kind === "chat")
                      .map((model) => (
                        <option key={`${model.kind}-${model.name}`} value={model.name}>
                          {model.name} / {model.source}
                        </option>
                      ))}
                  </select>
                ) : (
                  <p className="text-[11px] text-mutedInk">No discovered chat models. You can still enter a model name manually.</p>
                )}
              </div>

              <div className="flex flex-col justify-end gap-3">
                <button
                  type="button"
                  disabled={configPending || !selectedConnectionId || !selectedModelName || !conversation}
                  onClick={async () => {
                    const token = getAuthToken();
                    if (!token || !conversation) return;
                    setConfigPending(true);
                    setError(null);
                    try {
                      const response = await apiClient.updateConversation(token, conversation.id, {
                        provider_connection_id: selectedConnectionId,
                        model_name: selectedModelName,
                      });
                      setConversation(response.data);
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Failed to save model binding");
                    } finally {
                      setConfigPending(false);
                    }
                  }}
                  className="border border-signal/40 bg-signal px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-black disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {configPending ? "Saving..." : "Save Lane Config"}
                </button>
                <Link href="/settings/providers" className="text-center text-[10px] uppercase tracking-[0.2em] text-signal">
                  Manage connections
                </Link>
              </div>
            </div>
          </header>

          <div className="flex flex-col gap-4">
            {ordered.map((message) => (
              <StreamMessage key={message.id} role={message.role} content={message.content} sources={message.sources_json ?? null} />
            ))}
            {pending ? <StreamMessage role="assistant" content={streamBuffer || "Awaiting model deltas..."} pending sources={lastSources} /> : null}
          </div>

          {error ? <p className="text-sm text-red-300">{error}</p> : null}

          <ChatComposer
            disabled={pending || !conversation?.provider_connection_id || !conversation?.model_name}
            presetValue={composerPreset}
            defaultUseKnowledge={conversation?.use_knowledge ?? true}
            onSend={async ({ content, useKnowledge }) => {
              const token = getAuthToken();
              if (!token) return;
              const optimisticUser: Message = {
                id: `local-user-${Date.now()}`,
                conversation_id: conversationId,
                role: "user",
                content,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              };

              setMessages((current) => [...current, optimisticUser]);
              setStreamBuffer("");
              setPending(true);
              setError(null);
              setLastSources(null);
              setComposerPreset("");

              try {
                await apiClient.sendMessageStream(token, { conversation_id: conversationId, content, use_knowledge: useKnowledge }, (event) => {
                  if (event.event === "message_start") {
                    setLastRuntimeId(String(event.data.runtime_execution_id ?? ""));
                    const sources = Array.isArray(event.data.sources) ? (event.data.sources as KnowledgeChunkReference[]) : null;
                    setLastSources(sources);
                  }
                  if (event.event === "delta") {
                    const delta = String(event.data.delta ?? "");
                    setStreamBuffer((current) => current + delta);
                  }
                  if (event.event === "finish") {
                    const contentFromServer = String(event.data.content ?? streamBuffer);
                    const sources = Array.isArray(event.data.sources) ? (event.data.sources as KnowledgeChunkReference[]) : null;
                    const runtimeExecutionId = String(event.data.runtime_execution_id ?? "");
                    setMessages((current) => [
                      ...current,
                      {
                        id: String(event.data.message_id ?? `assistant-${Date.now()}`),
                        conversation_id: conversationId,
                        runtime_execution_id: runtimeExecutionId,
                        role: "assistant",
                        content: contentFromServer,
                        sources_json: sources,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString(),
                      },
                    ]);
                    setLastSources(sources);
                    setLastRuntimeId(runtimeExecutionId);
                    setStreamBuffer("");
                    setPending(false);
                    void apiClient.getRuntimeExecutions(token, { conversation_id: conversationId }).then((res) => setRuntime(res.data));
                  }
                  if (event.event === "error") {
                    setError(String(event.data.message ?? "Streaming error"));
                    setPending(false);
                  }
                  if (event.event === "done") {
                    setPending(false);
                  }
                });
              } catch (err) {
                setError(err instanceof Error ? err.message : "Streaming failed");
                setPending(false);
              }
            }}
          />
          {!conversation?.provider_connection_id || !conversation?.model_name ? (
            <p className="text-sm text-mutedInk">Bind a provider connection and model above before sending messages.</p>
          ) : null}
        </section>

        <aside className="flex flex-col gap-6">
          <PanelCard eyebrow="Runtime telemetry" title="Live context">
            <div className="space-y-4 text-sm text-mutedInk">
              <div className="border border-white/5 bg-black/25 px-4 py-4">
                <p className="text-[10px] uppercase tracking-[0.24em] text-signal">Execution status</p>
                <p className="mt-3 font-semibold text-ink">{latestRuntime?.status ?? "idle"}</p>
                <p className="mt-2 leading-7">Latest runtime: {latestRuntime?.id ?? lastRuntimeId ?? "--"}</p>
                <p>Connection: {latestRuntime?.provider_connection_name ?? conversation?.provider_connection_name ?? "--"}</p>
                <p>Model: {latestRuntime?.resolved_model_name ?? conversation?.model_name ?? "--"}</p>
                <p>Duration: {formatDuration(latestRuntime?.duration_ms)}</p>
                <p>Completed: {formatDate(latestRuntime?.completed_at)}</p>
              </div>
              <div className="border border-white/5 bg-black/25 px-4 py-4">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] uppercase tracking-[0.24em] text-signal">Quick skills</p>
                  <Link href="/skills" className="text-[10px] uppercase tracking-[0.2em] text-signal">Open registry</Link>
                </div>
                <div className="mt-3 flex flex-col gap-2">
                  {skills.slice(0, 4).map((skill) => (
                    <button
                      key={skill.id}
                      type="button"
                      onClick={() => setComposerPreset(skill.prompt_template)}
                      className="border border-white/5 bg-black/35 px-3 py-3 text-left transition hover:border-signal/25"
                    >
                      <p className="font-semibold text-ink">{skill.name}</p>
                      <p className="mt-1 text-xs leading-6 text-mutedInk">{skill.description}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div className="border border-white/5 bg-black/25 px-4 py-4">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] uppercase tracking-[0.24em] text-signal">Future execution hooks</p>
                  <Link href="/runtime" className="text-[10px] uppercase tracking-[0.2em] text-signal">Runtime</Link>
                </div>
                <div className="mt-3 grid gap-2">
                  <button
                    type="button"
                    onClick={() => setComposerPreset("Run this task with the Builder role. Inspect the repo, use the appropriate CLI or browser skills, and summarize what changed or what should happen next.")}
                    className="border border-white/5 bg-black/35 px-3 py-3 text-left transition hover:border-signal/25"
                  >
                    <p className="font-semibold text-ink">Run with Builder</p>
                    <p className="mt-1 text-xs leading-6 text-mutedInk">Repo + CLI + browser oriented execution handoff.</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => setComposerPreset("Run this task with the Operator role. Focus on controlled runtime actions, operational checks, and concise execution output.")}
                    className="border border-white/5 bg-black/35 px-3 py-3 text-left transition hover:border-signal/25"
                  >
                    <p className="font-semibold text-ink">Run with Operator</p>
                    <p className="mt-1 text-xs leading-6 text-mutedInk">Operational execution framing for CLI / browser workflows.</p>
                  </button>
                  <div className="grid gap-2 md:grid-cols-2">
                    <Link href="/skills" className="border border-white/5 bg-black/35 px-3 py-3 text-left transition hover:border-signal/25">
                      <p className="font-semibold text-ink">Use browser skill</p>
                      <p className="mt-1 text-xs leading-6 text-mutedInk">Jump into the Playwright-backed skill registry.</p>
                    </Link>
                    <Link href="/knowledge" className="border border-white/5 bg-black/35 px-3 py-3 text-left transition hover:border-signal/25">
                      <p className="font-semibold text-ink">Use knowledge pack</p>
                      <p className="mt-1 text-xs leading-6 text-mutedInk">Review builtin packs or upload workspace docs.</p>
                    </Link>
                  </div>
                </div>
              </div>
              <div className="border border-white/5 bg-black/25 px-4 py-4">
                <p className="text-[10px] uppercase tracking-[0.24em] text-signal">Knowledge references</p>
                {lastSources?.length ? (
                  <div className="mt-3 space-y-2">
                    {lastSources.map((source) => (
                      <div key={source.chunk_id} className="border border-white/5 bg-black/30 px-3 py-3">
                        <p className="font-semibold text-ink">{source.document_name}</p>
                        <p className="mt-1 text-xs leading-6">{source.excerpt}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-3">No knowledge snippets attached to the latest response.</p>
                )}
              </div>
              <div className="border border-white/5 bg-black/25 px-4 py-4">
                <p className="text-[10px] uppercase tracking-[0.24em] text-signal">Connection profile</p>
                <p className="mt-3">Base URL: {selectedConnection?.base_url ?? "--"}</p>
                <p className="mt-2">Default model: {selectedConnection?.default_model_name ?? "--"}</p>
                <p className="mt-2">Status: {selectedConnection?.status ?? "--"}</p>
              </div>
            </div>
          </PanelCard>
        </aside>
      </div>
    </AppShell>
  );
}
