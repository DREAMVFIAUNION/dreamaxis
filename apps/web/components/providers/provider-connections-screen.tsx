"use client";

import { useEffect, useMemo, useState } from "react";
import type { ProviderConnection } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

function splitManualModels(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((name) => ({ name, kind: "chat", source: "manual" }));
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
          <div className="space-y-3">
            {connections.map((connection) => (
              <button
                key={connection.id}
                type="button"
                onClick={() => setSelectedId(connection.id)}
                className={`w-full border px-4 py-4 text-left ${selected?.id === connection.id ? "border-signal/35 bg-signal/5" : "border-white/5 bg-black/20"}`}
              >
                <div className="flex items-center justify-between gap-4">
                  <p className="font-semibold text-ink">{connection.name}</p>
                  <span className="text-[10px] uppercase tracking-[0.18em] text-signal">{connection.status}</span>
                </div>
                <p className="mt-2 text-xs text-mutedInk">{connection.base_url}</p>
                <div className="mt-3 grid gap-2 text-[11px] text-mutedInk md:grid-cols-2">
                  <p>Key: {connection.secret.masked_value ?? "Not configured"}</p>
                  <p>Models: {connection.models.length}</p>
                </div>
                {connection.last_error ? <p className="mt-2 text-xs text-red-300">{connection.last_error}</p> : null}
              </button>
            ))}
            {!connections.length ? <p className="text-sm text-mutedInk">No provider connections yet. Create one on the right.</p> : null}
          </div>
        </PanelCard>

        <div className="flex flex-col gap-6">
          <PanelCard eyebrow="Create connection" title="API key self-service">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Connection name
                <input value={name} onChange={(event) => setName(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Base URL
                <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk md:col-span-2">
                API key
                <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="sk-... or gateway token" className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Default chat model
                <input value={defaultModelName} onChange={(event) => setDefaultModelName(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Default embedding model
                <input value={defaultEmbeddingModelName} onChange={(event) => setDefaultEmbeddingModelName(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
              </label>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk md:col-span-2">
                Manual model names
                <input
                  value={manualModels}
                  onChange={(event) => setManualModels(event.target.value)}
                  placeholder="Comma separated, used when /models is unavailable"
                  className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
                />
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
                    setMessage("Connection created.");
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
              <p className="text-xs text-mutedInk">OpenAI, OpenRouter, SiliconFlow, DeepSeek-compatible gateways all use the same form.</p>
            </div>
            {message ? <p className="mt-4 text-sm text-emerald-300">{message}</p> : null}
            {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
          </PanelCard>

          <PanelCard eyebrow="Selected connection" title={selected?.name ?? "Select a connection"}>
            {selected ? (
              <div className="space-y-4 text-sm text-mutedInk">
                <div className="border border-white/5 bg-black/25 px-4 py-4">
                  <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Profile</p>
                  <p className="mt-2 text-ink">Base URL: {selected.base_url}</p>
                  <p className="mt-2 text-ink">Key: {selected.secret.masked_value ?? "Not configured"}</p>
                  <p className="mt-2 text-ink">Default chat model: {selected.default_model_name ?? "--"}</p>
                  <p className="mt-2 text-ink">Default embedding model: {selected.default_embedding_model_name ?? "--"}</p>
                  <p className="mt-2 text-ink">Last checked: {selected.last_checked_at ? new Date(selected.last_checked_at).toLocaleString() : "--"}</p>
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
                        setMessage(response.data.message);
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
                        setMessage(response.data.warning ?? `Synced ${response.data.count} models.`);
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
                        setMessage(selected.is_enabled ? "Connection disabled." : "Connection enabled.");
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
                    {!selected.models.length ? <p className="text-sm text-mutedInk">No models stored yet.</p> : null}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-mutedInk">Pick a connection to test, sync, and inspect its model catalog.</p>
            )}
            {message ? <p className="mt-4 text-sm text-emerald-300">{message}</p> : null}
            {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
          </PanelCard>
        </div>
      </div>
    </AppShell>
  );
}
