"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { ChatExecutionTrace, ChatMode, Conversation, DiscoveredModel, KnowledgeChunkReference, Message, ProviderConnection, RuntimeExecution, SkillDefinition } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { ChatComposer, type ChatModeSelection } from "@/components/chat/chat-composer";
import { ChatExecutionBundle } from "@/components/chat/chat-execution-bundle";
import { StreamMessage } from "@/components/chat/stream-message";
import { ExecutionTimeline } from "@/components/execution/execution-timeline";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

function toTrace(value: unknown): ChatExecutionTrace | null {
  if (!value || typeof value !== "object") return null;
  if (!("scenario_tag" in value) || !("steps" in value)) return null;
  return value as ChatExecutionTrace;
}

function readiness(trace: ChatExecutionTrace | null) {
  const status = trace?.workspace_readiness && typeof trace.workspace_readiness === "object" && "status" in trace.workspace_readiness
    ? String((trace.workspace_readiness as { status?: string }).status ?? "")
    : null;
  return status || "Pending";
}

function tone(value?: string | null) {
  const v = (value ?? "").toLowerCase();
  if (v.includes("fail") || v.includes("error") || v.includes("missing")) return "border-red-400/30 bg-red-500/10 text-red-200";
  if (v.includes("degraded") || v.includes("warn") || v.includes("running")) return "border-amber-300/30 bg-amber-500/10 text-amber-100";
  if (!v || v === "pending") return "border-white/10 bg-white/5 text-mutedInk";
  return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
}

function modeLabel(mode?: ChatMode | null) {
  return mode ? mode.replaceAll("_", " ") : "Auto";
}

function traceFromRuntimeExecution(execution?: RuntimeExecution | null) {
  if (!execution?.details_json || typeof execution.details_json !== "object") return null;
  return toTrace((execution.details_json as Record<string, unknown>).execution_trace);
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
  const [chatMode, setChatMode] = useState<ChatModeSelection>("auto");
  const [configPending, setConfigPending] = useState(false);
  const [pending, setPending] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [lastSources, setLastSources] = useState<KnowledgeChunkReference[] | null>(null);
  const [lastTrace, setLastTrace] = useState<ChatExecutionTrace | null>(null);
  const [composerPreset, setComposerPreset] = useState("");

  async function loadConnectionModels(token: string, connectionId: string) {
    if (!connectionId) return setConnectionModels([]);
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
        const latestChat = runtimeRes.data.find((item) => item.execution_kind === "chat");
        setLastTrace(toTrace(latestChat?.details_json && (latestChat.details_json as Record<string, unknown>).execution_trace));
        if (activeConversation.provider_connection_id) await loadConnectionModels(token, activeConversation.provider_connection_id);
        const workspaceId = activeConversation.workspace_id || workspaceRes.data[0]?.id;
        if (workspaceId) {
          const skillsRes = await apiClient.getSkills(token, workspaceId);
          setSkills(skillsRes.data.filter((skill) => skill.enabled && skill.chat_callable));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load conversation");
      }
    })();
  }, [conversationId]);

  const ordered = useMemo(() => [...messages].sort((a, b) => a.created_at.localeCompare(b.created_at)), [messages]);
  const latestRuntime = runtime[0] ?? null;
  const latestChatRuntime = useMemo(() => runtime.find((item) => item.execution_kind === "chat") ?? null, [runtime]);
  const selectedTrace = useMemo(() => lastTrace ?? traceFromRuntimeExecution(latestChatRuntime), [lastTrace, latestChatRuntime]);
  const runtimeIndex = useMemo(() => new Map(runtime.map((item) => [item.id, item])), [runtime]);
  const currentMode = selectedTrace?.mode_summary?.active_mode ?? (chatMode === "auto" ? undefined : chatMode);
  const selectedConnection = connections.find((item) => item.id === selectedConnectionId) ?? null;

  return (
    <AppShell>
      <div className="mx-auto grid w-full max-w-7xl gap-6 xl:grid-cols-[1.45fr_0.85fr]">
        <section className="flex flex-col gap-4">
          <header className="panel px-6 py-6">
            <p className="text-[10px] uppercase tracking-[0.3em] text-signal">DreamAxis Repo Copilot</p>
            <h1 className="mt-2 font-headline text-4xl font-black uppercase tracking-tight">Chat-first verification lane</h1>
            <div className="mt-4 grid gap-3 text-xs uppercase tracking-[0.18em] text-mutedInk md:grid-cols-5">
              {[
                ["Workspace", conversation?.workspace_id ?? "--"],
                ["Connection", conversation?.provider_connection_name ?? "Not configured"],
                ["Model", conversation?.model_name ?? "Manual / Auto"],
                ["Readiness", readiness(selectedTrace)],
                ["Active mode", modeLabel(currentMode)],
              ].map(([label, value]) => (
                <div key={String(label)} className="border border-white/5 bg-black/20 px-4 py-3">
                  <p>{label}</p>
                  <p className="mt-2 text-sm font-semibold text-ink">{value}</p>
                </div>
              ))}
            </div>
            <div className="mt-5 grid gap-3 border border-white/5 bg-black/25 px-4 py-4 md:grid-cols-[1fr_1fr_auto]">
              <label className="flex flex-col gap-2 text-[10px] uppercase tracking-[0.2em] text-mutedInk">
                Provider connection
                <select value={selectedConnectionId} onChange={async (event) => {
                  const token = getAuthToken();
                  const nextConnectionId = event.target.value;
                  setSelectedConnectionId(nextConnectionId);
                  const nextConnection = connections.find((item) => item.id === nextConnectionId);
                  setSelectedModelName(nextConnection?.default_model_name ?? "");
                  if (token) await loadConnectionModels(token, nextConnectionId);
                }} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none">
                  <option value="">Select connection</option>
                  {connections.map((connection) => <option key={connection.id} value={connection.id}>{connection.name} / {connection.status}</option>)}
                </select>
              </label>
              <div className="flex flex-col gap-2">
                <label className="text-[10px] uppercase tracking-[0.2em] text-mutedInk">Model name</label>
                <input value={selectedModelName} onChange={(event) => setSelectedModelName(event.target.value)} placeholder="e.g. qwen/qwen3-coder-480b-a35b-instruct" className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
                {connectionModels.length ? <select value={selectedModelName} onChange={(event) => setSelectedModelName(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none">
                  <option value="">Pick discovered model</option>
                  {connectionModels.filter((item) => item.kind === "chat").map((model) => <option key={model.name} value={model.name}>{model.name} / {model.source}</option>)}
                </select> : <p className="text-[11px] text-mutedInk">No discovered chat models. Manual model entry still works.</p>}
              </div>
              <div className="flex flex-col justify-end gap-3">
                <button type="button" disabled={configPending || !selectedConnectionId || !selectedModelName || !conversation} onClick={async () => {
                  const token = getAuthToken();
                  if (!token || !conversation) return;
                  setConfigPending(true);
                  setError(null);
                  try {
                    const response = await apiClient.updateConversation(token, conversation.id, { provider_connection_id: selectedConnectionId, model_name: selectedModelName });
                    setConversation(response.data);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Failed to save model binding");
                  } finally {
                    setConfigPending(false);
                  }
                }} className="border border-signal/40 bg-signal px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-black disabled:cursor-not-allowed disabled:opacity-40">{configPending ? "Saving..." : "Save lane config"}</button>
                <Link href="/settings/providers" className="text-center text-[10px] uppercase tracking-[0.2em] text-signal">Manage connections</Link>
              </div>
            </div>
          </header>

          <div className="flex flex-col gap-4">
            {ordered.map((message) => {
              const runtimeExecution = message.runtime_execution_id ? runtimeIndex.get(message.runtime_execution_id) ?? null : null;
              const trace = traceFromRuntimeExecution(runtimeExecution);
              return (
                <StreamMessage
                  key={message.id}
                  role={message.role}
                  content={message.content}
                  sources={message.sources_json ?? null}
                  details={message.role === "assistant" && trace ? <ChatExecutionBundle trace={trace} runtimeIndex={runtimeIndex} parentExecutionId={message.runtime_execution_id} /> : null}
                />
              );
            })}
            {pending ? (
              <StreamMessage
                role="assistant"
                content={streamBuffer || "Awaiting model deltas..."}
                pending
                sources={lastSources}
                details={lastTrace ? <ChatExecutionBundle trace={lastTrace} runtimeIndex={runtimeIndex} parentExecutionId={latestChatRuntime?.id ?? null} /> : null}
              />
            ) : null}
          </div>

          {selectedTrace ? <PanelCard eyebrow="Current turn" title={selectedTrace.trace_summary?.headline ?? "Execution bundle"}>
            <div className="space-y-5 text-sm text-mutedInk">
              <div className="flex flex-wrap gap-2">
                <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(currentMode)}`}>Mode / {modeLabel(currentMode)}</span>
                <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(selectedTrace.trace_summary?.status)}`}>Bundle / {selectedTrace.execution_bundle_id ?? latestChatRuntime?.id ?? "--"}</span>
                <span className={`border px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${tone(readiness(selectedTrace))}`}>Readiness / {readiness(selectedTrace)}</span>
              </div>
              <div className="border border-white/5 bg-black/25 px-4 py-4">
                <p className="text-[10px] uppercase tracking-[0.2em] text-signal">Timeline</p>
                <div className="mt-3">
                  <ExecutionTimeline
                    items={selectedTrace.actual_events ?? selectedTrace.timeline ?? []}
                    emptyCopy="Send a repo-focused prompt to generate a visible execution lane."
                    resolveArtifacts={(item) => {
                      const r = item.runtime_execution_id ? runtimeIndex.get(item.runtime_execution_id) : null;
                      return Array.isArray(r?.artifacts_json) ? (r.artifacts_json as Array<Record<string, unknown>>) : [];
                    }}
                  />
                </div>
              </div>
            </div>
          </PanelCard> : null}

          {error ? <p className="text-sm text-red-300">{error}</p> : null}

          <ChatComposer disabled={pending} presetValue={composerPreset} defaultUseKnowledge={conversation?.use_knowledge ?? true} mode={chatMode} onModeChange={setChatMode} onSend={async ({ content, useKnowledge, mode }) => {
            const token = getAuthToken();
            if (!token) return;
            setMessages((current) => [...current, { id: `local-user-${Date.now()}`, conversation_id: conversationId, role: "user", content, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }]);
            setStreamBuffer(""); setPending(true); setError(null); setLastSources(null); setComposerPreset(""); setLastTrace(null);
            try {
              await apiClient.sendMessageStream(token, { conversation_id: conversationId, content, use_knowledge: useKnowledge, mode }, (event) => {
                if (event.event === "message_start") { const sources = Array.isArray(event.data.sources) ? (event.data.sources as KnowledgeChunkReference[]) : null; setLastSources(sources); setLastTrace(toTrace(event.data.execution_trace)); }
                if (event.event === "delta") setStreamBuffer((current) => current + String(event.data.delta ?? ""));
                if (event.event === "finish") {
                  const sources = Array.isArray(event.data.sources) ? (event.data.sources as KnowledgeChunkReference[]) : null;
                  const runtimeExecutionId = String(event.data.runtime_execution_id ?? "");
                  setMessages((current) => [...current, { id: String(event.data.message_id ?? `assistant-${Date.now()}`), conversation_id: conversationId, runtime_execution_id: runtimeExecutionId, role: "assistant", content: String(event.data.content ?? ""), sources_json: sources, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }]);
                  setLastSources(sources); setLastTrace(toTrace(event.data.execution_trace)); setStreamBuffer(""); setPending(false);
                  void apiClient.getRuntimeExecutions(token, { conversation_id: conversationId }).then((res) => setRuntime(res.data));
                }
                if (event.event === "error") { setError(String(event.data.message ?? "Streaming error")); setPending(false); }
                if (event.event === "done") setPending(false);
              });
            } catch (err) { setError(err instanceof Error ? err.message : "Streaming failed"); setPending(false); }
          }} />
          {!conversation?.provider_connection_id || !conversation?.model_name ? <p className="text-sm text-mutedInk">No provider lane is bound yet. DreamAxis can still run local repo-copilot probes and fall back to trace-grounded answers until you save a provider connection and model above.</p> : null}
        </section>

        <aside className="flex flex-col gap-6">
          <PanelCard eyebrow="Operator sidebar" title="Context + shortcuts">
            <div className="space-y-4 text-sm text-mutedInk">
              <div className="border border-white/5 bg-black/25 px-4 py-4"><p className="text-[10px] uppercase tracking-[0.24em] text-signal">Latest runtime</p><p className="mt-3 font-semibold text-ink">{latestRuntime?.status ?? "idle"}</p><p className="mt-2 leading-7">Runtime: {latestRuntime?.id ?? "--"}</p></div>
              <div className="border border-white/5 bg-black/25 px-4 py-4"><div className="flex items-center justify-between"><p className="text-[10px] uppercase tracking-[0.24em] text-signal">Quick skills</p><Link href="/skills" className="text-[10px] uppercase tracking-[0.2em] text-signal">Open registry</Link></div><div className="mt-3 flex flex-col gap-2">{skills.slice(0, 5).map((skill) => <button key={skill.id} type="button" onClick={() => setComposerPreset(skill.prompt_template)} className="border border-white/5 bg-black/35 px-3 py-3 text-left transition hover:border-signal/25"><p className="font-semibold text-ink">{skill.name}</p><p className="mt-1 text-xs leading-6 text-mutedInk">{skill.description}</p><p className="mt-2 text-[10px] uppercase tracking-[0.18em] text-signal">{skill.skill_mode} / {skill.chat_modes?.join(", ") || "chat"} / {skill.safety_level}</p></button>)}</div></div>
              <div className="border border-white/5 bg-black/25 px-4 py-4"><p className="text-[10px] uppercase tracking-[0.24em] text-signal">Knowledge references</p>{lastSources?.length ? <div className="mt-3 space-y-2">{lastSources.map((source) => <div key={source.chunk_id} className="border border-white/5 bg-black/30 px-3 py-3"><p className="font-semibold text-ink">{source.document_name}</p><p className="mt-1 text-xs leading-6">{source.excerpt}</p></div>)}</div> : <p className="mt-3 text-xs leading-6 text-mutedInk">No knowledge snippets attached to the latest response.</p>}</div>
              <div className="border border-white/5 bg-black/25 px-4 py-4"><p className="text-[10px] uppercase tracking-[0.24em] text-signal">Connection profile</p><p className="mt-3">Base URL: {selectedConnection?.base_url ?? "--"}</p><p className="mt-2">Default model: {selectedConnection?.default_model_name ?? "--"}</p><p className="mt-2">Status: {selectedConnection?.status ?? "--"}</p></div>
            </div>
          </PanelCard>
        </aside>
      </div>
    </AppShell>
  );
}
