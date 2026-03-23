"use client";

import { useEffect, useMemo, useState } from "react";
import type { ProviderConnection } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

type StatusTone = {
  label: string;
  className: string;
};

const onboardingSteps = [
  {
    title: "Add a connection",
    body: "Enter a name, the gateway base URL, and the API key you want DreamAxis to use.",
  },
  {
    title: "Test it",
    body: "Use Test connection first. This confirms the key and URL are accepted before you depend on the connection elsewhere.",
  },
  {
    title: "Choose models",
    body: "If the gateway exposes /models, click Sync models. If it does not, provide model names manually when you create the connection.",
  },
  {
    title: "Use it in chat and skills",
    body: "After the connection is healthy, pick a default chat model, an embedding model if needed, and reuse the connection across the workspace.",
  },
] as const;

const compatibilityExamples = [
  "OpenAI official API",
  "OpenRouter and similar routing gateways",
  "Self-hosted or local gateways that mirror the OpenAI API shape",
] as const;

function splitManualModels(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((name) => ({ name, kind: "chat", source: "manual" }));
}

function getStatusTone(status: string, enabled: boolean): StatusTone {
  if (!enabled || status === "disabled") {
    return {
      label: "Disabled",
      className: "border-white/10 bg-white/5 text-mutedInk",
    };
  }

  if (status === "active") {
    return {
      label: "Ready",
      className: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
    };
  }

  if (status === "manual_entry_required") {
    return {
      label: "Manual model entry",
      className: "border-amber-400/30 bg-amber-400/10 text-amber-200",
    };
  }

  if (status === "pending") {
    return {
      label: "Not tested yet",
      className: "border-signal/30 bg-signal/10 text-signal",
    };
  }

  if (status === "error" || status === "requires_config") {
    return {
      label: "Needs attention",
      className: "border-red-400/30 bg-red-400/10 text-red-200",
    };
  }

  return {
    label: status.replaceAll("_", " "),
    className: "border-white/10 bg-white/5 text-mutedInk",
  };
}

function FieldHint({ children }: { children: React.ReactNode }) {
  return <p className="text-[11px] normal-case tracking-normal text-mutedInk/90">{children}</p>;
}

export function ProviderConnectionsScreen() {
  const [connections, setConnections] = useState<ProviderConnection[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
  const [apiKey, setApiKey] = useState("");
  const [defaultModelName, setDefaultModelName] = useState("");
  const [defaultEmbeddingModelName, setDefaultEmbeddingModelName] = useState("");
  const [manualModels, setManualModels] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selected = useMemo(() => connections.find((item) => item.id === selectedId) ?? null, [connections, selectedId]);
  const selectedStatusTone = selected ? getStatusTone(selected.status, selected.is_enabled) : null;

  async function refreshConnections() {
    const token = getAuthToken();
    if (!token) return;
    const response = await apiClient.getProviderConnections(token);
    setConnections(response.data);
    setSelectedId((current) => current || response.data[0]?.id || "");
  }

  useEffect(() => {
    void refreshConnections();
  }, []);

  return (
    <AppShell>
      <div className="mx-auto grid w-full max-w-7xl gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <PanelCard eyebrow="Provider Settings" title="OpenAI-compatible connections">
          <div className="space-y-4">
            <div className="border border-white/5 bg-black/20 px-4 py-4 text-sm text-mutedInk">
              <p className="text-[10px] uppercase tracking-[0.18em] text-signal">What this page is for</p>
              <p className="mt-2">
                Add your own API key and base URL so DreamAxis can call an OpenAI-style model gateway without a hosted DreamAxis account.
              </p>
              <p className="mt-3 text-xs text-mutedInk/90">
                “OpenAI-compatible” means the provider accepts the same general request shape DreamAxis expects for chat, embeddings, and often model discovery.
              </p>
            </div>

            {connections.map((connection) => {
              const statusTone = getStatusTone(connection.status, connection.is_enabled);

              return (
                <button
                  key={connection.id}
                  type="button"
                  onClick={() => setSelectedId(connection.id)}
                  className={`w-full border px-4 py-4 text-left transition ${selected?.id === connection.id ? "border-signal/35 bg-signal/5 shadow-[0_0_0_1px_rgba(103,232,249,0.08)]" : "border-white/5 bg-black/20 hover:border-white/10 hover:bg-black/25"}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold text-ink">{connection.name}</p>
                      <p className="mt-2 text-xs text-mutedInk">{connection.base_url}</p>
                    </div>
                    <span className={`inline-flex border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${statusTone.className}`}>
                      {statusTone.label}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 text-[11px] text-mutedInk md:grid-cols-2">
                    <p>Stored key: {connection.secret.masked_value ?? "Not configured"}</p>
                    <p>Known models: {connection.models.length}</p>
                  </div>
                  {connection.last_error ? <p className="mt-2 text-xs text-red-300">Last check: {connection.last_error}</p> : null}
                </button>
              );
            })}

            {!connections.length ? (
              <div className="border border-dashed border-white/10 bg-black/10 px-4 py-5 text-sm text-mutedInk">
                <p className="font-semibold text-ink">No provider connections yet.</p>
                <p className="mt-2">Start on the right with one connection name, one base URL, and one API key. Then test it before syncing models.</p>
                <ol className="mt-4 space-y-2 text-xs text-mutedInk/90">
                  <li>1. Create the connection.</li>
                  <li>2. Click Test connection.</li>
                  <li>3. Click Sync models, or rely on manual model names if /models is unavailable.</li>
                </ol>
              </div>
            ) : null}
          </div>
        </PanelCard>

        <div className="flex flex-col gap-6">
          <PanelCard eyebrow="Create connection" title="API key self-service">
            <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
              <div className="border border-white/5 bg-black/20 px-4 py-4 text-sm text-mutedInk">
                <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Before you start</p>
                <ol className="mt-3 space-y-3">
                  {onboardingSteps.map((step, index) => (
                    <li key={step.title} className="flex gap-3">
                      <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center border border-signal/30 bg-signal/10 text-[10px] font-bold text-signal">
                        {index + 1}
                      </span>
                      <div>
                        <p className="font-semibold text-ink">{step.title}</p>
                        <p className="mt-1 text-xs text-mutedInk/90">{step.body}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>

              <div className="border border-white/5 bg-black/20 px-4 py-4 text-sm text-mutedInk">
                <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Compatible gateways</p>
                <p className="mt-2 text-xs text-mutedInk/90">
                  If a provider exposes OpenAI-style endpoints, DreamAxis can usually use the same form for it.
                </p>
                <ul className="mt-3 space-y-2 text-xs text-mutedInk/90">
                  {compatibilityExamples.map((example) => (
                    <li key={example} className="border border-white/5 bg-black/20 px-3 py-2">
                      {example}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs text-mutedInk/80">
                  Name and Base URL are always required. API key is normally required for self-service use unless your deployment already provides a server-side fallback.
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Connection name <span className="text-signal">Required</span>
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="My OpenRouter workspace"
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none transition focus:border-signal/40"
                />
                <FieldHint>Use a human-friendly label you will recognize later in chat, skills, and runtime history.</FieldHint>
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Base URL <span className="text-signal">Required</span>
                <input
                  value={baseUrl}
                  onChange={(event) => setBaseUrl(event.target.value)}
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none transition focus:border-signal/40"
                />
                <FieldHint>Usually ends with <code className="text-[10px] text-ink">/v1</code>. Example: <code className="text-[10px] text-ink">https://api.openai.com/v1</code>.</FieldHint>
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk md:col-span-2">
                API key <span className="text-signal">Usually required</span>
                <input
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="sk-... or gateway token"
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none transition focus:border-signal/40"
                />
                <FieldHint>DreamAxis stores the secret server-side and only shows a masked value after save.</FieldHint>
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Default chat model <span className="text-white/50">Optional</span>
                <input
                  value={defaultModelName}
                  onChange={(event) => setDefaultModelName(event.target.value)}
                  placeholder="gpt-4.1-mini or your gateway model name"
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none transition focus:border-signal/40"
                />
                <FieldHint>Set this now if you already know the exact chat model name you want to use most often.</FieldHint>
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Default embedding model <span className="text-white/50">Optional</span>
                <input
                  value={defaultEmbeddingModelName}
                  onChange={(event) => setDefaultEmbeddingModelName(event.target.value)}
                  placeholder="text-embedding-3-small"
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none transition focus:border-signal/40"
                />
                <FieldHint>Only needed if you want this connection to power knowledge indexing and retrieval by default.</FieldHint>
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk md:col-span-2">
                Manual model names <span className="text-white/50">Optional fallback</span>
                <input
                  value={manualModels}
                  onChange={(event) => setManualModels(event.target.value)}
                  placeholder="Comma separated. Example: gpt-4.1-mini, deepseek-chat"
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none transition focus:border-signal/40"
                />
                <FieldHint>
                  Use this only when the gateway does not expose <code className="text-[10px] text-ink">/models</code> or when you want to pre-seed known model names before syncing.
                </FieldHint>
              </label>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={saving || !name || !baseUrl}
                onClick={async () => {
                  const token = getAuthToken();
                  if (!token) return;
                  setSaving(true);
                  setError(null);
                  setMessage(null);
                  try {
                    await apiClient.createProviderConnection(token, {
                      name,
                      base_url: baseUrl,
                      api_key: apiKey || undefined,
                      default_model_name: defaultModelName || undefined,
                      default_embedding_model_name: defaultEmbeddingModelName || undefined,
                      manual_models: splitManualModels(manualModels),
                    });
                    setName("");
                    setApiKey("");
                    setDefaultModelName("");
                    setDefaultEmbeddingModelName("");
                    setManualModels("");
                    setMessage("Connection created. Next step: test it, then sync models or rely on manual entries.");
                    await refreshConnections();
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Failed to create connection");
                  } finally {
                    setSaving(false);
                  }
                }}
                className="border border-signal/40 bg-signal px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-black disabled:cursor-not-allowed disabled:opacity-40"
              >
                {saving ? "Saving..." : "Create connection"}
              </button>
              <p className="text-xs text-mutedInk">Recommended flow: create → test → sync models → use in chat, skills, and knowledge.</p>
            </div>
            {message ? <p className="mt-4 text-sm text-emerald-300">{message}</p> : null}
            {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
          </PanelCard>

          <PanelCard eyebrow="Selected connection" title={selected?.name ?? "Select a connection"}>
            {selected ? (
              <div className="space-y-4 text-sm text-mutedInk">
                <div className="flex flex-wrap items-center gap-3">
                  {selectedStatusTone ? (
                    <span className={`inline-flex border px-3 py-1 text-[10px] uppercase tracking-[0.18em] ${selectedStatusTone.className}`}>
                      {selectedStatusTone.label}
                    </span>
                  ) : null}
                  <p className="text-xs text-mutedInk/90">
                    Test first to validate the key and base URL. Sync models second if the provider supports discovery.
                  </p>
                </div>

                <div className="border border-white/5 bg-black/25 px-4 py-4">
                  <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Profile</p>
                  <p className="mt-2 text-ink">Base URL: {selected.base_url}</p>
                  <p className="mt-2 text-ink">Stored key: {selected.secret.masked_value ?? "Not configured"}</p>
                  <p className="mt-2 text-ink">Default chat model: {selected.default_model_name ?? "Not set yet"}</p>
                  <p className="mt-2 text-ink">Default embedding model: {selected.default_embedding_model_name ?? "Not set yet"}</p>
                  <p className="mt-2 text-ink">Last checked: {selected.last_checked_at ? new Date(selected.last_checked_at).toLocaleString() : "Never tested"}</p>
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={async () => {
                      const token = getAuthToken();
                      if (!token) return;
                      setError(null);
                      setMessage(null);
                      try {
                        const response = await apiClient.testProviderConnection(token, selected.id);
                        setMessage(`${response.data.message} ${response.data.ok ? "You can sync models next if you want automatic discovery." : "Review the base URL and API key, then try again."}`.trim());
                        await refreshConnections();
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Connection test failed");
                      }
                    }}
                    className="border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-mutedInk"
                  >
                    Test connection
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      const token = getAuthToken();
                      if (!token) return;
                      setError(null);
                      setMessage(null);
                      try {
                        const response = await apiClient.syncProviderConnectionModels(token, selected.id);
                        setMessage(
                          response.data.warning
                            ? `${response.data.warning} You can still use manual model names for this connection.`
                            : `Synced ${response.data.count} models. Pick one of them in chat or use it as a default.`
                        );
                        await refreshConnections();
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Model sync failed");
                      }
                    }}
                    className="border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-mutedInk"
                  >
                    Sync models
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      const token = getAuthToken();
                      if (!token) return;
                      setError(null);
                      setMessage(null);
                      try {
                        await apiClient.updateProviderConnection(token, selected.id, { is_enabled: !selected.is_enabled });
                        setMessage(selected.is_enabled ? "Connection disabled. It will no longer be offered as an active option." : "Connection enabled and ready to use again.");
                        await refreshConnections();
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Failed to toggle connection");
                      }
                    }}
                    className="border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-mutedInk"
                  >
                    {selected.is_enabled ? "Disable" : "Enable"}
                  </button>
                </div>

                <div className="border border-white/5 bg-black/25 px-4 py-4">
                  <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Discovered + manual models</p>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    {selected.models.map((model) => (
                      <div key={`${model.kind}-${model.name}`} className="border border-white/5 bg-black/30 px-3 py-3">
                        <p className="font-semibold text-ink">{model.name}</p>
                        <p className="mt-1 text-xs text-mutedInk">{model.kind} / {model.source}</p>
                      </div>
                    ))}
                    {!selected.models.length ? (
                      <div className="border border-dashed border-white/10 bg-black/10 px-4 py-4 text-sm text-mutedInk md:col-span-2">
                        <p className="font-semibold text-ink">No models stored yet.</p>
                        <p className="mt-2">
                          If this gateway supports <code className="text-[10px] text-ink">/models</code>, click <span className="text-ink">Sync models</span>. If it does not,
                          recreate or update the connection with manual model names and use those names directly in chat or skills.
                        </p>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : (
              <div className="border border-dashed border-white/10 bg-black/10 px-4 py-5 text-sm text-mutedInk">
                <p className="font-semibold text-ink">Pick a connection to inspect it.</p>
                <p className="mt-2">From this panel you can validate the key, sync any discoverable models, and confirm exactly what DreamAxis will expose elsewhere.</p>
              </div>
            )}
            {message ? <p className="mt-4 text-sm text-emerald-300">{message}</p> : null}
            {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
          </PanelCard>
        </div>
      </div>
    </AppShell>
  );
}
