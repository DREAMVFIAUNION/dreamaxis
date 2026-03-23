import { readSSEStream } from "./sse";
import type {
  AgentRole,
  AppConfig,
  ApiResponse,
  DoctorCheckResult,
  BrowserExecutionResult,
  CliExecutionResult,
  Conversation,
  DiscoveredModel,
  EnvironmentOverview,
  KnowledgeDocument,
  KnowledgePack,
  LoginResponse,
  Message,
  MessageCreateInput,
  Model,
  PaginatedResponse,
  Provider,
  ProviderConnection,
  ProviderConnectionTestResult,
  RuntimeExecution,
  RuntimeHost,
  RuntimeSession,
  SkillDefinition,
  SkillPack,
  SkillRunInput,
  SkillRunResult,
  StreamEvent,
  Workspace,
  WorkspaceEnvironmentStatus,
} from "./types";

function resolveBaseUrl(baseUrl?: string) {
  if (baseUrl) return baseUrl;
  if (typeof window !== "undefined") {
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL;
    }

    const protocol = window.location.protocol || "http:";
    const hostname = window.location.hostname || "localhost";

    if (hostname === "web") {
      return "http://api:8000";
    }

    if (hostname === "127.0.0.1" || hostname === "localhost" || hostname === "host.docker.internal") {
      return `${protocol}//${hostname}:8000`;
    }

    return `${protocol}//${hostname}:8000`;
  }
  return process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createApiClient(baseUrl?: string) {
  const apiBase = resolveBaseUrl(baseUrl);

  const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
    const isFormData = init?.body instanceof FormData;
    const response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
    return parseJson<T>(response);
  };

  return {
    getAppConfig: () => request<ApiResponse<AppConfig>>("/api/v1/app-config"),
    getEnvironmentOverview: (token: string) =>
      request<ApiResponse<EnvironmentOverview>>("/api/v1/environment", {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getEnvironmentDoctor: (token: string, workspaceId?: string) =>
      request<ApiResponse<DoctorCheckResult>>(`/api/v1/environment/doctor${workspaceId ? `?workspace_id=${workspaceId}` : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getWorkspaceEnvironment: (token: string, workspaceId: string) =>
      request<ApiResponse<WorkspaceEnvironmentStatus>>(`/api/v1/environment/workspaces/${workspaceId}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    login: (email: string, password: string) =>
      request<ApiResponse<LoginResponse>>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    bootstrapAuth: () =>
      request<ApiResponse<LoginResponse>>("/api/v1/auth/bootstrap", {
        method: "POST",
      }),
    getProviders: () => request<PaginatedResponse<Provider>>("/api/v1/providers"),
    getModels: (kind?: string) => request<PaginatedResponse<Model>>(`/api/v1/models${kind ? `?kind=${kind}` : ""}`),
    getProviderConnections: (token: string) =>
      request<PaginatedResponse<ProviderConnection>>("/api/v1/provider-connections", {
        headers: { Authorization: `Bearer ${token}` },
      }),
    createProviderConnection: (
      token: string,
      payload: {
        provider_type?: string;
        name: string;
        base_url: string;
        api_key?: string;
        model_discovery_mode?: string;
        default_model_name?: string;
        default_embedding_model_name?: string;
        manual_models?: Array<{ name: string; kind?: string; source?: string }>;
      },
    ) =>
      request<ApiResponse<ProviderConnection>>("/api/v1/provider-connections", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    updateProviderConnection: (
      token: string,
      connectionId: string,
      payload: {
        name?: string;
        base_url?: string;
        api_key?: string;
        model_discovery_mode?: string;
        status?: string;
        is_enabled?: boolean;
        default_model_name?: string;
        default_embedding_model_name?: string;
        manual_models?: Array<{ name: string; kind?: string; source?: string }>;
      },
    ) =>
      request<ApiResponse<ProviderConnection>>(`/api/v1/provider-connections/${connectionId}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    testProviderConnection: (token: string, connectionId: string) =>
      request<ApiResponse<ProviderConnectionTestResult>>(`/api/v1/provider-connections/${connectionId}/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }),
    syncProviderConnectionModels: (token: string, connectionId: string) =>
      request<ApiResponse<{ connection: ProviderConnection; count: number; warning?: string }>>(
        `/api/v1/provider-connections/${connectionId}/sync-models`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      ),
    getProviderConnectionModels: (token: string, connectionId: string) =>
      request<PaginatedResponse<DiscoveredModel>>(`/api/v1/provider-connections/${connectionId}/models`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getWorkspaces: (token: string) =>
      request<PaginatedResponse<Workspace>>("/api/v1/workspaces", {
        headers: { Authorization: `Bearer ${token}` },
      }),
    createWorkspace: (
      token: string,
      payload: {
        name: string;
        slug: string;
        description?: string;
        default_provider_id?: string;
        default_model_id?: string;
        default_provider_connection_id?: string;
        default_model_name?: string;
        default_embedding_model_name?: string;
      },
    ) =>
      request<ApiResponse<Workspace>>("/api/v1/workspaces", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    getConversations: (token: string, workspaceId?: string) =>
      request<PaginatedResponse<Conversation>>(`/api/v1/conversations${workspaceId ? `?workspace_id=${workspaceId}` : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getConversation: (token: string, conversationId: string) =>
      request<ApiResponse<Conversation>>(`/api/v1/conversations/${conversationId}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    createConversation: (
      token: string,
      payload: {
        workspace_id: string;
        title: string;
        id?: string;
        provider_id?: string;
        model_id?: string;
        provider_connection_id?: string;
        model_name?: string;
        use_knowledge?: boolean;
      },
    ) =>
      request<ApiResponse<Conversation>>("/api/v1/conversations", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    updateConversation: (
      token: string,
      conversationId: string,
      payload: {
        title?: string;
        provider_connection_id?: string;
        model_name?: string;
        use_knowledge?: boolean;
      },
    ) =>
      request<ApiResponse<Conversation>>(`/api/v1/conversations/${conversationId}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    getMessages: (token: string, conversationId: string) =>
      request<PaginatedResponse<Message>>(`/api/v1/messages?conversation_id=${conversationId}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    sendMessage: (token: string, payload: MessageCreateInput) =>
      request<ApiResponse<{ user_message: Message; assistant_message: Message; runtime_execution_id: string }>>("/api/v1/messages", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    sendMessageStream: async (token: string, payload: MessageCreateInput, onEvent: (event: StreamEvent) => void) => {
      const response = await fetch(`${apiBase}/api/v1/messages/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      await readSSEStream(response, onEvent);
    },
    getKnowledgeDocuments: (token: string, workspaceId?: string) =>
      request<PaginatedResponse<KnowledgeDocument>>(`/api/v1/knowledge${workspaceId ? `?workspace_id=${workspaceId}` : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getKnowledgeDocumentsFiltered: (
      token: string,
      params?: { workspace_id?: string; source_type?: string; pack_slug?: string },
    ) => {
      const search = new URLSearchParams();
      if (params?.workspace_id) search.set("workspace_id", params.workspace_id);
      if (params?.source_type) search.set("source_type", params.source_type);
      if (params?.pack_slug) search.set("pack_slug", params.pack_slug);
      const suffix = search.toString() ? `?${search.toString()}` : "";
      return request<PaginatedResponse<KnowledgeDocument>>(`/api/v1/knowledge${suffix}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    },
    getKnowledgePacks: (token: string, workspaceId?: string) =>
      request<PaginatedResponse<KnowledgePack>>(`/api/v1/knowledge-packs${workspaceId ? `?workspace_id=${workspaceId}` : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    syncKnowledgePacks: (token: string, workspaceId: string) =>
      request<ApiResponse<{ synced_pack_count: number; synced_document_count: number }>>(`/api/v1/knowledge-packs/sync?workspace_id=${workspaceId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }),
    uploadKnowledgeDocument: (token: string, workspaceId: string, file: File) => {
      const formData = new FormData();
      formData.append("workspace_id", workspaceId);
      formData.append("file", file);
      return request<ApiResponse<KnowledgeDocument>>("/api/v1/knowledge/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
    },
    getSkills: (token: string, workspaceId?: string) =>
      request<PaginatedResponse<SkillDefinition>>(`/api/v1/skills${workspaceId ? `?workspace_id=${workspaceId}` : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getSkillPacks: (token: string, workspaceId?: string) =>
      request<PaginatedResponse<SkillPack>>(`/api/v1/skill-packs${workspaceId ? `?workspace_id=${workspaceId}` : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    syncSkillPacks: (token: string, workspaceId: string) =>
      request<ApiResponse<{ synced_pack_count: number; synced_skill_count: number }>>(`/api/v1/skill-packs/sync?workspace_id=${workspaceId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }),
    importSkillPack: (token: string, payload: { workspace_id: string; source_path: string }) =>
      request<ApiResponse<{ pack: SkillPack; imported_skill_count: number }>>("/api/v1/skill-packs/import", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    updateSkill: (
      token: string,
        skillId: string,
        payload: {
          enabled?: boolean;
          skill_mode?: string;
          required_runtime_type?: string;
          session_mode?: string;
          command_template?: string;
          working_directory?: string;
          agent_role_slug?: string;
          tool_capabilities?: string[] | Record<string, unknown>;
          knowledge_scope?: string[] | Record<string, unknown>;
          provider_connection_id?: string;
          model_name?: string;
          allow_model_override?: boolean;
          use_knowledge?: boolean;
        },
    ) =>
      request<ApiResponse<SkillDefinition>>(`/api/v1/skills/${skillId}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    runSkill: (token: string, skillId: string, payload: SkillRunInput) =>
      request<ApiResponse<SkillRunResult>>(`/api/v1/skills/${skillId}/run`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    getAgentRoles: (token: string) =>
      request<PaginatedResponse<AgentRole>>("/api/v1/agent-roles", {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getRuntimes: (token: string, workspaceId?: string) =>
      request<PaginatedResponse<RuntimeHost>>(`/api/v1/runtimes${workspaceId ? `?workspace_id=${workspaceId}` : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getRuntimesFiltered: (token: string, params?: { workspace_id?: string; runtime_type?: string }) => {
      const search = new URLSearchParams();
      if (params?.workspace_id) search.set("workspace_id", params.workspace_id);
      if (params?.runtime_type) search.set("runtime_type", params.runtime_type);
      const suffix = search.toString() ? `?${search.toString()}` : "";
      return request<PaginatedResponse<RuntimeHost>>(`/api/v1/runtimes${suffix}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    },
    getRuntimeSessions: (token: string, workspaceId?: string) =>
      request<PaginatedResponse<RuntimeSession>>(`/api/v1/runtime-sessions${workspaceId ? `?workspace_id=${workspaceId}` : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    getRuntimeSessionsFiltered: (token: string, params?: { workspace_id?: string; session_type?: string }) => {
      const search = new URLSearchParams();
      if (params?.workspace_id) search.set("workspace_id", params.workspace_id);
      if (params?.session_type) search.set("session_type", params.session_type);
      const suffix = search.toString() ? `?${search.toString()}` : "";
      return request<PaginatedResponse<RuntimeSession>>(`/api/v1/runtime-sessions${suffix}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    },
    createRuntimeSession: (
      token: string,
      payload: {
        workspace_id: string;
        working_directory?: string;
        reusable?: boolean;
      },
    ) =>
      request<ApiResponse<RuntimeSession>>("/api/v1/runtime-sessions", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      }),
    closeRuntimeSession: (token: string, runtimeSessionId: string) =>
      request<ApiResponse<RuntimeSession>>(`/api/v1/runtime-sessions/${runtimeSessionId}/close`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }),
    getRuntimeExecutions: (token: string, params?: { workspace_id?: string; conversation_id?: string }) => {
      const search = new URLSearchParams();
      if (params?.workspace_id) search.set("workspace_id", params.workspace_id);
      if (params?.conversation_id) search.set("conversation_id", params.conversation_id);
      const suffix = search.toString() ? `?${search.toString()}` : "";
      return request<PaginatedResponse<RuntimeExecution>>(`/api/v1/runtime-executions${suffix}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    },
    getRuntimeExecution: (token: string, executionId: string) =>
      request<ApiResponse<RuntimeExecution>>(`/api/v1/runtime-executions/${executionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    dispatchCliExecution: (token: string, executionId: string) =>
      request<ApiResponse<CliExecutionResult>>(`/api/v1/runtime-executions/${executionId}/dispatch-cli`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }),
    dispatchBrowserExecution: (token: string, executionId: string) =>
      request<ApiResponse<BrowserExecutionResult>>(`/api/v1/runtime-executions/${executionId}/dispatch-browser`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }),
  };
}
