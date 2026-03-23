"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { AgentRole, DiscoveredModel, ProviderConnection, SkillDefinition, SkillPack, SkillRunResult, Workspace } from "@dreamaxis/client";
import { AppShell } from "@/components/app-shell/app-shell";
import { PanelCard } from "@/components/cards/panel-card";
import { apiClient } from "@/lib/api";
import { getAuthToken } from "@/lib/auth";

function valueToText(value: unknown) {
  if (value == null) return "--";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function compatibilityTone(status?: string | null) {
  if (status === "ready") return "text-emerald-300";
  if (status === "warn") return "text-amber-300";
  if (status === "blocked") return "text-red-300";
  return "text-mutedInk";
}

export function SkillsScreen() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [skillPacks, setSkillPacks] = useState<SkillPack[]>([]);
  const [skills, setSkills] = useState<SkillDefinition[]>([]);
  const [connections, setConnections] = useState<ProviderConnection[]>([]);
  const [connectionModels, setConnectionModels] = useState<DiscoveredModel[]>([]);
  const [agentRoles, setAgentRoles] = useState<AgentRole[]>([]);
  const [selectedSkillId, setSelectedSkillId] = useState<string>("");
  const [selectedConnectionId, setSelectedConnectionId] = useState("");
  const [selectedModelName, setSelectedModelName] = useState("");
  const [skillMode, setSkillMode] = useState<"prompt" | "cli" | "browser" | string>("prompt");
  const [requiredRuntimeType, setRequiredRuntimeType] = useState("");
  const [sessionMode, setSessionMode] = useState("reuse");
  const [commandTemplate, setCommandTemplate] = useState("");
  const [workingDirectory, setWorkingDirectory] = useState(".");
  const [agentRoleSlug, setAgentRoleSlug] = useState("");
  const [importPath, setImportPath] = useState("");
  const [variables, setVariables] = useState<Record<string, string>>({ input: "Provide an operational summary." });
  const [pending, setPending] = useState(false);
  const [savingSkill, setSavingSkill] = useState(false);
  const [syncingPacks, setSyncingPacks] = useState(false);
  const [importingPack, setImportingPack] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<SkillRunResult | null>(null);

  const selectedSkill = useMemo(() => skills.find((skill) => skill.id === selectedSkillId) ?? skills[0] ?? null, [selectedSkillId, skills]);

  function syncFormState(skill: SkillDefinition | null, nextConnections: ProviderConnection[]) {
    setSelectedConnectionId(skill?.provider_connection_id ?? nextConnections[0]?.id ?? "");
    setSelectedModelName(skill?.model_name ?? nextConnections[0]?.default_model_name ?? "");
    setSkillMode(skill?.skill_mode ?? "prompt");
    setRequiredRuntimeType(skill?.required_runtime_type ?? "");
    setSessionMode(skill?.session_mode ?? "reuse");
    setCommandTemplate(skill?.command_template ?? "");
    setWorkingDirectory(skill?.working_directory ?? ".");
    setAgentRoleSlug(skill?.agent_role_slug ?? "");

    const schema = skill?.input_schema && typeof skill.input_schema === "object" ? Object.keys(skill.input_schema) : ["input"];
    const defaults = Object.fromEntries(schema.map((key) => [key, key === "input" ? "Provide an operational summary." : ""]));
    setVariables(defaults);
  }

  async function loadConnectionModels(activeConnectionId: string) {
    const token = getAuthToken();
    if (!token || !activeConnectionId) {
      setConnectionModels([]);
      return;
    }
    const response = await apiClient.getProviderConnectionModels(token, activeConnectionId);
    setConnectionModels(response.data);
  }

  async function loadWorkspaceState(activeWorkspaceId: string) {
    const token = getAuthToken();
    if (!token || !activeWorkspaceId) return;
    const [packsRes, skillsRes, connectionRes, roleRes] = await Promise.all([
      apiClient.getSkillPacks(token, activeWorkspaceId),
      apiClient.getSkills(token, activeWorkspaceId),
      apiClient.getProviderConnections(token),
      apiClient.getAgentRoles(token),
    ]);
    setSkillPacks(packsRes.data);
    setSkills(skillsRes.data);
    setConnections(connectionRes.data);
    setAgentRoles(roleRes.data);
    const nextSelectedSkill = skillsRes.data.find((skill) => skill.id === selectedSkillId) ?? skillsRes.data[0] ?? null;
    setSelectedSkillId(nextSelectedSkill?.id ?? "");
    syncFormState(nextSelectedSkill, connectionRes.data);
    if (nextSelectedSkill?.provider_connection_id) {
      await loadConnectionModels(nextSelectedSkill.provider_connection_id);
    } else {
      setConnectionModels([]);
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
        if (primaryWorkspaceId) await loadWorkspaceState(primaryWorkspaceId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load skills workspace state");
      }
    })();
  }, []);

  const packCounts = useMemo(() => {
    return skills.reduce<Record<string, number>>((acc, skill) => {
      const key = skill.pack_slug ?? "workspace";
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
  }, [skills]);

  const variableKeys = useMemo(() => {
    if (!selectedSkill?.input_schema || typeof selectedSkill.input_schema !== "object") return Object.keys(variables);
    const keys = Object.keys(selectedSkill.input_schema);
    return keys.length ? keys : ["input"];
  }, [selectedSkill, variables]);

  return (
    <AppShell>
      <div className="mx-auto grid w-full max-w-7xl gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="flex flex-col gap-6">
          <PanelCard eyebrow="Skill Packs" title="Installed pack library">
            <div className="mb-4 flex items-end justify-between gap-4">
              <label className="flex min-w-64 flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                Workspace
                <select
                  value={workspaceId}
                  onChange={async (event) => {
                    setWorkspaceId(event.target.value);
                    await loadWorkspaceState(event.target.value);
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
              <div className="flex gap-3">
                <button
                  type="button"
                  disabled={syncingPacks || !workspaceId}
                  onClick={async () => {
                    const token = getAuthToken();
                    if (!token || !workspaceId) return;
                    setSyncingPacks(true);
                    setError(null);
                    try {
                      const response = await apiClient.syncSkillPacks(token, workspaceId);
                      setNotice(`Synced ${response.data.synced_pack_count} packs / ${response.data.synced_skill_count} skills`);
                      await loadWorkspaceState(workspaceId);
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Failed to sync builtin packs");
                    } finally {
                      setSyncingPacks(false);
                    }
                  }}
                  className="border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-mutedInk"
                >
                  {syncingPacks ? "Syncing..." : "Sync builtin packs"}
                </button>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-[1fr_auto]">
              <input
                value={importPath}
                onChange={(event) => setImportPath(event.target.value)}
                placeholder="Local skill pack manifest path or checked-out git repo directory"
                className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none"
              />
              <button
                type="button"
                disabled={importingPack || !workspaceId || !importPath}
                onClick={async () => {
                  const token = getAuthToken();
                  if (!token || !workspaceId || !importPath) return;
                  setImportingPack(true);
                  setError(null);
                  try {
                    const response = await apiClient.importSkillPack(token, { workspace_id: workspaceId, source_path: importPath });
                    setNotice(`Imported ${response.data.pack.name} (${response.data.imported_skill_count} skills)`);
                    setImportPath("");
                    await loadWorkspaceState(workspaceId);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Failed to import skill pack");
                  } finally {
                    setImportingPack(false);
                  }
                }}
                className="border border-signal/40 bg-signal px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-black disabled:opacity-40"
              >
                {importingPack ? "Importing..." : "Import pack"}
              </button>
            </div>
            <div className="mt-4 grid gap-3">
              {skillPacks.map((pack) => (
                <div key={pack.id} className="border border-white/5 bg-black/20 px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-ink">{pack.name}</p>
                    <span className="text-[10px] uppercase tracking-[0.18em] text-signal">{pack.source_type}</span>
                  </div>
                  <p className="mt-2 text-xs leading-6 text-mutedInk">{pack.description}</p>
                  <p className="mt-2 text-[11px] text-mutedInk">{pack.slug} / v{pack.version} / {packCounts[pack.slug] ?? 0} skills</p>
                </div>
              ))}
              {!skillPacks.length ? <p className="text-sm text-mutedInk">No skill packs synced yet.</p> : null}
            </div>
          </PanelCard>

          <PanelCard eyebrow="Registry" title="Skill definitions">
            <div className="flex flex-col gap-3">
              {skills.map((skill) => (
                <button
                  key={skill.id}
                  type="button"
                  onClick={async () => {
                    setSelectedSkillId(skill.id);
                    syncFormState(skill, connections);
                    if (skill.provider_connection_id) await loadConnectionModels(skill.provider_connection_id);
                  }}
                  className={`border px-4 py-4 text-left ${selectedSkill?.id === skill.id ? "border-signal/40 bg-signal/5" : "border-white/5 bg-black/20"}`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-semibold text-ink">{skill.name}</p>
                    <span className={`text-[10px] uppercase tracking-[0.18em] ${compatibilityTone(skill.compatibility?.status)}`}>
                      {skill.skill_mode} / {skill.compatibility?.status ?? (skill.enabled ? "ready" : "disabled")}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-6 text-mutedInk">{skill.description}</p>
                  <p className="mt-2 text-[11px] text-mutedInk">Pack: {skill.pack_slug ?? "workspace"} / Role: {skill.agent_role_slug ?? "unassigned"}</p>
                </button>
              ))}
            </div>
          </PanelCard>
        </div>

        <div className="flex flex-col gap-6">
          <PanelCard eyebrow="Execution" title={selectedSkill?.name ?? "Select a skill"}>
            {selectedSkill ? (
              <>
                <p className="text-sm leading-7 text-mutedInk">{selectedSkill.description}</p>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Pack / capabilities</p>
                    <p className="mt-3 text-sm text-ink">{selectedSkill.pack_slug ?? "workspace"} / v{selectedSkill.pack_version ?? "--"}</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-mutedInk">{valueToText(selectedSkill.tool_capabilities)}</pre>
                  </div>
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Knowledge scope</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-mutedInk">{valueToText(selectedSkill.knowledge_scope)}</pre>
                  </div>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Required</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-mutedInk">{valueToText(selectedSkill.required_capabilities)}</pre>
                  </div>
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Recommended</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-mutedInk">{valueToText(selectedSkill.recommended_capabilities)}</pre>
                  </div>
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Workspace reqs</p>
                    <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-mutedInk">{valueToText(selectedSkill.workspace_requirements)}</pre>
                  </div>
                  <div className="border border-white/5 bg-black/25 px-4 py-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Compatibility</p>
                    <p className={`mt-3 text-sm font-semibold uppercase tracking-[0.18em] ${compatibilityTone(selectedSkill.compatibility?.status)}`}>
                      {selectedSkill.compatibility?.status ?? "--"}
                    </p>
                    <p className="mt-2 text-xs leading-6 text-mutedInk">{selectedSkill.compatibility?.message ?? "No compatibility snapshot."}</p>
                  </div>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                    Skill mode
                    <select value={skillMode} onChange={(event) => setSkillMode(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none">
                      <option value="prompt">prompt</option>
                      <option value="cli">cli</option>
                      <option value="browser">browser</option>
                    </select>
                  </label>
                  <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                    Agent role
                    <select value={agentRoleSlug} onChange={(event) => setAgentRoleSlug(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none">
                      <option value="">Unassigned</option>
                      {agentRoles.map((role) => (
                        <option key={role.slug} value={role.slug}>
                          {role.slug}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {skillMode === "prompt" ? (
                  <>
                    <div className="mt-4 border border-white/5 bg-black/25 px-4 py-4 text-xs text-mutedInk">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Prompt template</p>
                      <pre className="mt-3 whitespace-pre-wrap font-sans leading-7 text-ink">{selectedSkill.prompt_template}</pre>
                    </div>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                        Provider connection
                        <select
                          value={selectedConnectionId}
                          onChange={async (event) => {
                            const nextId = event.target.value;
                            setSelectedConnectionId(nextId);
                            const nextConnection = connections.find((item) => item.id === nextId);
                            setSelectedModelName(nextConnection?.default_model_name ?? "");
                            await loadConnectionModels(nextId);
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
                      <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                        Model name
                        <input value={selectedModelName} onChange={(event) => setSelectedModelName(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
                      </label>
                    </div>
                    {connectionModels.length ? (
                      <select value={selectedModelName} onChange={(event) => setSelectedModelName(event.target.value)} className="mt-3 border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none">
                        <option value="">Pick discovered model</option>
                        {connectionModels.filter((model) => model.kind === "chat").map((model) => (
                          <option key={`${model.kind}-${model.name}`} value={model.name}>
                            {model.name} / {model.source}
                          </option>
                        ))}
                      </select>
                    ) : null}
                  </>
                ) : (
                  <>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                        Required runtime type
                        <input value={requiredRuntimeType} onChange={(event) => setRequiredRuntimeType(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
                      </label>
                      <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                        Session mode
                        <select value={sessionMode} onChange={(event) => setSessionMode(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none">
                          <option value="reuse">reuse</option>
                          <option value="new">new</option>
                        </select>
                      </label>
                    </div>
                    {skillMode === "cli" ? (
                      <label className="mt-4 flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                        Working directory
                        <input value={workingDirectory} onChange={(event) => setWorkingDirectory(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-3 text-sm text-ink outline-none" />
                      </label>
                    ) : null}
                    <label className="mt-4 flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                      {skillMode === "browser" ? "Browser action template (JSON)" : "Command template"}
                      <textarea rows={8} value={commandTemplate} onChange={(event) => setCommandTemplate(event.target.value)} className="border border-white/10 bg-black/20 px-4 py-4 text-sm text-ink outline-none" />
                    </label>
                  </>
                )}

                <div className="mt-4 flex items-center gap-3">
                  <button
                    type="button"
                    disabled={savingSkill || !selectedSkill}
                    onClick={async () => {
                      const token = getAuthToken();
                      if (!token || !selectedSkill) return;
                      setSavingSkill(true);
                      setError(null);
                      try {
                        await apiClient.updateSkill(token, selectedSkill.id, {
                          skill_mode: skillMode,
                          required_runtime_type: skillMode === "prompt" ? undefined : requiredRuntimeType || (skillMode === "browser" ? "browser" : "cli"),
                          session_mode: skillMode === "prompt" ? undefined : sessionMode,
                          command_template: skillMode === "prompt" ? undefined : commandTemplate,
                          working_directory: skillMode === "cli" ? workingDirectory : undefined,
                          agent_role_slug: agentRoleSlug || undefined,
                          provider_connection_id: skillMode === "prompt" ? selectedConnectionId || undefined : undefined,
                          model_name: skillMode === "prompt" ? selectedModelName || undefined : undefined,
                        });
                        setNotice(`Saved ${selectedSkill.name}`);
                        await loadWorkspaceState(workspaceId);
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Failed to save skill definition");
                      } finally {
                        setSavingSkill(false);
                      }
                    }}
                    className="border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-mutedInk"
                  >
                    {savingSkill ? "Saving..." : "Save skill"}
                  </button>
                  <Link href="/settings/providers" className="text-[10px] uppercase tracking-[0.18em] text-signal">
                    Manage connections
                  </Link>
                </div>

                <div className="mt-4 grid gap-4">
                  {variableKeys.map((key) => (
                    <label key={key} className="flex flex-col gap-2 text-xs uppercase tracking-[0.18em] text-mutedInk">
                      {key}
                      <textarea
                        rows={key === "input" ? 6 : 3}
                        value={variables[key] ?? ""}
                        onChange={(event) => setVariables((current) => ({ ...current, [key]: event.target.value }))}
                        className="border border-white/10 bg-black/20 px-4 py-4 text-sm text-ink outline-none"
                      />
                    </label>
                  ))}
                </div>

                <div className="mt-4 flex items-center gap-3">
                  <button
                    type="button"
                    disabled={pending || !selectedSkill.enabled}
                    onClick={async () => {
                      const token = getAuthToken();
                      if (!token || !workspaceId || !selectedSkill) return;
                      setPending(true);
                      setError(null);
                      try {
                        const response = await apiClient.runSkill(token, selectedSkill.id, {
                          workspace_id: workspaceId,
                          variables,
                          use_knowledge: selectedSkill.use_knowledge,
                        });
                        setRunResult(response.data);
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Skill execution failed");
                      } finally {
                        setPending(false);
                      }
                    }}
                    className="border border-signal/40 bg-signal px-4 py-3 text-xs font-black uppercase tracking-[0.2em] text-black disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {pending ? "Running..." : skillMode === "browser" ? "Run Browser Skill" : skillMode === "cli" ? "Run CLI Skill" : "Run Prompt Skill"}
                  </button>
                  {runResult ? (
                    <Link href={`/chat/${runResult.conversation.id}`} className="border border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-mutedInk">
                      Open Conversation
                    </Link>
                  ) : null}
                </div>
                {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
                {notice ? <p className="mt-4 text-sm text-emerald-300">{notice}</p> : null}
              </>
            ) : (
              <p className="text-sm text-mutedInk">No skills are registered for this workspace yet.</p>
            )}
          </PanelCard>

          <PanelCard eyebrow="Last result" title="Skill run output">
            {runResult ? (
              <div className="space-y-4">
                <div className="border border-white/5 bg-black/25 px-4 py-4">
                  <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Runtime</p>
                  <p className="mt-2 text-sm font-semibold text-ink">{runResult.execution.status}</p>
                  <p className="mt-1 text-xs text-mutedInk">{runResult.execution.execution_kind} / {runResult.execution.runtime_name ?? runResult.execution.runtime_id ?? "--"}</p>
                  <p className="mt-1 text-xs text-mutedInk">Session: {runResult.execution.runtime_session_id ?? "--"}</p>
                </div>
                <div className="border border-white/5 bg-black/25 px-4 py-4">
                  <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Assistant output</p>
                  <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-7 text-ink">{runResult.assistant_message.content}</pre>
                </div>
                {Array.isArray(runResult.execution.artifacts_json) ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {runResult.execution.artifacts_json.map((artifact, index) => (
                      <div key={index} className="border border-white/5 bg-black/25 px-4 py-4">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-signal">Artifact / {String((artifact as { kind?: string }).kind ?? index)}</p>
                        {(artifact as { data_url?: string }).data_url ? (
                          <img src={String((artifact as { data_url?: string }).data_url)} alt="runtime artifact" className="mt-3 w-full border border-white/5" />
                        ) : (
                          <pre className="mt-3 whitespace-pre-wrap font-sans text-xs leading-6 text-ink">{valueToText(artifact)}</pre>
                        )}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-mutedInk">Run a skill to populate the latest execution output.</p>
            )}
          </PanelCard>
        </div>
      </div>
    </AppShell>
  );
}
